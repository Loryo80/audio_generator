# Audiobook Generator

A Streamlit application that converts PDF and DOCX documents into audiobooks using the fal.ai API for text-to-speech synthesis.

## Features

- Upload PDF or DOCX documents and extract text
- Preview document content before processing
- Select from multiple male and female voice options
- Customize text chunk size for processing
- Generate audio in MP3 or WAV format
- Download complete audiobook or individual audio chunks
- Fallback mechanisms for handling processing errors

## Requirements

- Python 3.7+
- ffmpeg (optional, for MP3 conversion)
- fal.ai API key

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/audio_generator.git
   cd audio_generator
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root and add your fal.ai API key:
   ```
   FAL_KEY=your_fal_ai_api_key_here
   ```

## Usage

1. Run the Streamlit app:
   ```
   streamlit run audio_app.py
   ```

2. Open your browser and navigate to the URL shown in the terminal (typically `http://localhost:8501`)

3. Upload a PDF or DOCX document

4. Preview the extracted text

5. Choose your preferred voice and audio format settings

6. Click "Generate Complete Audiobook" to start the conversion process

7. Download your audiobook when processing is complete

## How It Works

The application:
1. Extracts text from uploaded PDF or DOCX documents
2. Splits text into manageable chunks to avoid API limitations
3. Processes each chunk through the fal.ai text-to-speech API
4. Combines audio chunks into a complete audiobook file
5. Provides download options for the final audiobook

## Dependencies

- streamlit: Web interface
- fal_client: API client for fal.ai
- docx2txt: Extract text from DOCX files
- PyPDF2: Extract text from PDF files
- python-dotenv: Load environment variables
- requests: HTTP requests to download audio files
- wave: Audio file manipulation

## Troubleshooting

- **ffmpeg errors**: The application uses ffmpeg for MP3 conversion. If not available, it will fallback to WAV format.
- **API errors**: Check your fal.ai API key and ensure it has sufficient quota.
- **Chunk processing errors**: If some chunks fail to process, the app will skip them and continue with the remaining chunks.

## License

MIT

## Acknowledgements

- [fal.ai](https://fal.ai/) for providing the text-to-speech API
- [Streamlit](https://streamlit.io/) for the web application framework 
