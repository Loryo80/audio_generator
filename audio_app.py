import streamlit as st
import fal_client
import os
import tempfile
import docx2txt
import PyPDF2
from dotenv import load_dotenv
import base64
from io import BytesIO
import logging
import requests
import time
import uuid
import subprocess
import shutil
import wave

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check if FAL_KEY is set
if not os.getenv("FAL_KEY"):
    st.error("FAL_KEY environment variable is not set. Please set it in a .env file or directly in your environment.")
    st.stop()

def extract_text_from_docx(file):
    """Extract text from a .docx file"""
    try:
        text = docx2txt.process(file)
        return text
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {e}")
        st.error(f"Error extracting text from document: {e}")
        return None

def extract_text_from_pdf(file):
    """Extract text from a PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        st.error(f"Error extracting text from PDF: {e}")
        return None

def generate_audio(text: str, voice: str = "af_heart") -> dict:
    """Generate audio from text using fal.ai API"""
    try:
        # Progress callback
        def on_queue_update(update):
            if isinstance(update, fal_client.InProgress):
                for log in update.logs:
                    st.write(log["message"])

        result = fal_client.subscribe(
            "fal-ai/kokoro/american-english",
            arguments={
                "prompt": text,
                "voice": voice
            },
            with_logs=True,
            on_queue_update=on_queue_update,
        )
        return result
    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        st.error(f"Error generating audio: {e}")
        return None

def chunk_text(text: str, max_chunk_size: int = 1000) -> list[str]:
    """Split text into chunks of specified size, trying to break at sentences."""
    chunks = []
    
    # Try to split at sentence boundaries (periods, question marks, exclamation points)
    sentences = []
    for sentence_end in ['. ', '? ', '! ']:
        text = text.replace(sentence_end, sentence_end + '[SPLIT]')
    
    sentences = text.split('[SPLIT]')
    
    current_chunk = ""
    for sentence in sentences:
        # If adding this sentence would exceed the max chunk size and we already have content,
        # save the current chunk and start a new one
        if len(current_chunk) + len(sentence) > max_chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += sentence
    
    # Add the last chunk if it has content
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # If any chunk is still too large, force split it
    final_chunks = []
    for chunk in chunks:
        if len(chunk) > max_chunk_size:
            # Split the chunk into smaller pieces
            for i in range(0, len(chunk), max_chunk_size):
                final_chunks.append(chunk[i:i+max_chunk_size])
        else:
            final_chunks.append(chunk)
    
    return final_chunks

def download_audio_file(url: str, save_path: str) -> bool:
    """Download audio file from URL and save to path"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            f.write(response.content)
        
        return True
    except Exception as e:
        logger.error(f"Error downloading audio file: {e}")
        return False

def combine_audio_files(file_list_path: str, output_file: str) -> bool:
    """Combine WAV files into a single MP3 file using ffmpeg"""
    try:
        # Check if ffmpeg is available
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=False)
        except FileNotFoundError:
            logger.error("ffmpeg is not installed or not in PATH")
            return False
        
        # Run ffmpeg command to concatenate files
        cmd = [
            "ffmpeg", 
            "-f", "concat", 
            "-safe", "0", 
            "-i", file_list_path, 
            "-c:a", "libmp3lame", 
            "-q:a", "2", 
            output_file
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return os.path.exists(output_file)
    except Exception as e:
        logger.error(f"Error combining audio files with ffmpeg: {e}")
        return False

def combine_wav_files(input_files: list[str], output_file: str) -> bool:
    """Combine WAV files into a single WAV file using Python's wave module"""
    try:
        # Check if we have any files
        if not input_files:
            return False
            
        # Get info from first file
        with wave.open(input_files[0], 'rb') as w:
            params = w.getparams()
        
        # Open output file
        with wave.open(output_file, 'wb') as output:
            output.setparams(params)
            
            # Write each file's data (skipping header)
            for wav_file in input_files:
                with wave.open(wav_file, 'rb') as w:
                    output.writeframes(w.readframes(w.getnframes()))
        
        return os.path.exists(output_file)
    except Exception as e:
        logger.error(f"Error combining WAV files: {e}")
        return False

def main():
    st.title("Audiobook Generator")
    
    # File uploader
    uploaded_file = st.file_uploader("Upload a document (DOCX or PDF)", type=["docx", "pdf"])
    
    if uploaded_file is not None:
        # Display file info
        st.write(f"Filename: {uploaded_file.name}")
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        # Extract text based on file type
        if file_extension == "docx":
            text = extract_text_from_docx(uploaded_file)
        elif file_extension == "pdf":
            text = extract_text_from_pdf(uploaded_file)
        else:
            st.error("Unsupported file format. Please upload a DOCX or PDF file.")
            st.stop()
        
        if text:
            # Display document content in a scrollable container
            st.subheader("Document Preview")
            st.text_area("Document Content", text, height=400)
            
            # Voice selection
            voice_options = {
                "Female Voices": ["af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica", 
                                 "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky"],
                "Male Voices": ["am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", 
                               "am_michael", "am_onyx", "am_puck", "am_santa"]
            }
            
            voice_category = st.selectbox("Voice Category", list(voice_options.keys()))
            selected_voice = st.selectbox("Select Voice", voice_options[voice_category])
            
            # Chunk size selection
            chunk_size = st.slider("Max chunk size (characters)", 
                                  min_value=500, max_value=2000, value=1000, step=100,
                                  help="Larger chunks mean fewer API calls but may hit API limits")
            
            # Display text length info
            st.info(f"Document length: {len(text)} characters. This will be processed in multiple chunks.")
            
            # Book title for the output file
            book_title = st.text_input("Audiobook Title (for the output file name)", 
                                     value=os.path.splitext(uploaded_file.name)[0])
            
            # Audio format selection
            output_format = st.radio("Output Format", ["MP3", "WAV"], index=0)
            
            # Generate audio button
            if st.button("Generate Complete Audiobook"):
                # Split text into chunks
                text_chunks = chunk_text(text, chunk_size)
                
                # Create containers for progress and audio chunks
                progress_container = st.container()
                audio_chunks_container = st.expander("Individual Audio Chunks (click to expand)")
                
                with progress_container:
                    st.write(f"Processing {len(text_chunks)} text chunks...")
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                
                # Create a temporary directory for audio files
                temp_dir = tempfile.mkdtemp()
                audio_files = []
                audio_urls = []
                success_count = 0
                
                try:
                    for i, chunk in enumerate(text_chunks):
                        status_text.text(f"Generating audio for chunk {i+1}/{len(text_chunks)}...")
                        
                        try:
                            # Call FAL.ai API to generate audio
                            result = generate_audio(chunk, selected_voice)
                            
                            if result and 'audio' in result and 'url' in result['audio']:
                                audio_url = result['audio']['url']
                                audio_urls.append(audio_url)
                                
                                # Create filename for this chunk
                                chunk_file = os.path.join(temp_dir, f"chunk_{i+1:03d}.wav")
                                
                                # Download the audio file
                                status_text.text(f"Downloading audio for chunk {i+1}...")
                                if download_audio_file(audio_url, chunk_file):
                                    audio_files.append(chunk_file)
                                    success_count += 1
                                    
                                    # Display audio player for this chunk in the expander
                                    with audio_chunks_container:
                                        st.subheader(f"Audio Chunk {i+1}")
                                        st.audio(audio_url)
                                else:
                                    st.error(f"Failed to download audio for chunk {i+1}.")
                            else:
                                st.error(f"Failed to generate audio for chunk {i+1}. Skipping this chunk.")
                        except Exception as e:
                            logger.error(f"Error in audio generation for chunk {i+1}: {e}")
                            st.error(f"Error processing chunk {i+1}: {e}")
                        
                        # Update progress bar
                        progress_bar.progress((i + 1) / len(text_chunks))
                    
                    # Check if we have any successful chunks
                    if success_count > 0:
                        status_text.text("Combining audio chunks into a single audiobook...")
                        
                        # Create a safe title for the output file
                        safe_title = ''.join(c if c.isalnum() else '_' for c in book_title)
                        
                        # Output file paths
                        combined_wav = os.path.join(temp_dir, f"{safe_title}_combined.wav")
                        final_output = os.path.join(temp_dir, f"{safe_title}_audiobook.{output_format.lower()}")
                        
                        # First try to combine using Python's wave module
                        if combine_wav_files(audio_files, combined_wav):
                            st.success("Successfully combined audio chunks!")
                            
                            # If MP3 was selected, convert the WAV to MP3
                            if output_format.upper() == "MP3":
                                try:
                                    # Create a file list for ffmpeg
                                    file_list_path = os.path.join(temp_dir, "file_list.txt")
                                    with open(file_list_path, 'w') as f:
                                        for audio_file in audio_files:
                                            f.write(f"file '{audio_file}'\n")
                                    
                                    # Try ffmpeg conversion
                                    if combine_audio_files(file_list_path, final_output):
                                        combined_file = final_output
                                    else:
                                        combined_file = combined_wav
                                        st.warning("Could not convert to MP3. Providing WAV file instead.")
                                except Exception as e:
                                    logger.error(f"Error converting to MP3: {e}")
                                    combined_file = combined_wav
                                    st.warning("Error converting to MP3. Providing WAV file instead.")
                            else:
                                combined_file = combined_wav
                            
                            # Provide the combined file for download
                            with open(combined_file, 'rb') as f:
                                final_data = f.read()
                            
                            # Determine the final extension
                            final_ext = os.path.splitext(combined_file)[1][1:]  # Remove the dot
                            
                            # Create the download button
                            st.markdown("### 📥 Download Your Audiobook")
                            col1, col2 = st.columns([1, 2])
                            
                            with col1:
                                st.download_button(
                                    label=f"DOWNLOAD COMPLETE AUDIOBOOK ({final_ext.upper()})",
                                    data=final_data,
                                    file_name=f"{safe_title}_audiobook.{final_ext}",
                                    mime=f"audio/{final_ext}",
                                    use_container_width=True
                                )
                            
                            # Add some instructions
                            with col2:
                                st.info(f"Click the button to download your complete audiobook in {final_ext.upper()} format")
                            
                            # Play the combined audio
                            st.subheader("Complete Audiobook")
                            st.audio(final_data)
                        else:
                            st.error("Failed to combine audio chunks. Providing individual chunks instead.")
                            
                            # Create a ZIP file with the individual chunks as fallback
                            zip_path = os.path.join(temp_dir, f"{safe_title}_audio_chunks.zip")
                            shutil.make_archive(os.path.splitext(zip_path)[0], 'zip', temp_dir)
                            
                            # Offer the ZIP file for download
                            with open(zip_path, 'rb') as f:
                                zip_data = f.read()
                            
                            # Create a prominent download button
                            st.markdown("### 📥 Download Your Audio Chunks")
                            col1, col2 = st.columns([1, 2])
                            
                            with col1:
                                st.download_button(
                                    label="DOWNLOAD AUDIO CHUNKS (ZIP)",
                                    data=zip_data,
                                    file_name=f"{safe_title}_audio_chunks.zip",
                                    mime="application/zip",
                                    use_container_width=True
                                )
                            
                            # Add instructions
                            with col2:
                                st.info("Download this ZIP file containing all audio chunks. You can use software like Audacity to combine them into a complete audiobook.")
                        
                        # Also provide links to individual chunks for backup
                        with st.expander("Individual Audio URLs (for backup)"):
                            for i, url in enumerate(audio_urls):
                                st.markdown(f"[Chunk {i+1}]({url})")
                            
                            # Option to download all URLs as a text file
                            urls_text = "\n".join(audio_urls)
                            b64 = base64.b64encode(urls_text.encode()).decode()
                            href = f'<a href="data:file/txt;base64,{b64}" download="audio_urls.txt">Download all audio URLs as text file</a>'
                            st.markdown(href, unsafe_allow_html=True)
                    
                    else:
                        st.error("No audio chunks were successfully generated. Please try again.")
                
                finally:
                    # Clean up temporary directory
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception as e:
                        logger.error(f"Error cleaning up temporary files: {e}")

if __name__ == "__main__":
    main() 
