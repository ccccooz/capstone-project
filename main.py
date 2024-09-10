import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import tempfile
import subprocess
from gtts import gTTS

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI()

# Streamlit app
st.title("Video Transcription and Translation")

# File uploader
video_file = st.file_uploader("Upload a video file", type=["mp4", "avi", "mov"])

# Language selection with added Turkish option
languages = st.multiselect("Select languages for translation:", ["English", "Spanish", "French", "German", "Chinese", "Turkish"])

# Function to save uploaded file temporarily
def save_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            return tmp_file.name
    return None

# Function to convert video to audio using ffmpeg
def convert_video_to_audio(video_path):
    audio_path = video_path.rsplit('.', 1)[0] + ".wav"
    subprocess.run(["ffmpeg", "-i", video_path, "-q:a", "0", "-map", "a", audio_path], check=True)
    return audio_path

# Function to generate audio from text using gTTS
def text_to_speech(text, language_code):
    tts = gTTS(text=text, lang=language_code)
    temp_audio_path = tempfile.mktemp(suffix=".mp3")
    tts.save(temp_audio_path)
    return temp_audio_path

# Function to remove time codes from SRT
def remove_time_codes(srt_text):
    lines = srt_text.splitlines()
    text_lines = []
    for line in lines:
        # Check if the line is a time code or index line
        if '-->' in line or (line.isdigit() and not line.startswith('0')):
            continue
        text_lines.append(line)
    return "\n".join(text_lines)

# Initialize session state for translations and audio files
if "translations" not in st.session_state:
    st.session_state.translations = {}
if "audio_files" not in st.session_state:
    st.session_state.audio_files = {}

# Process button
if st.button("Transcribe and Translate") and video_file is not None and languages:
    with st.spinner("Processing video..."):
        try:
            # Save uploaded file
            temp_video_path = save_uploaded_file(video_file)

            # Convert video to audio
            temp_audio_path = convert_video_to_audio(temp_video_path)

            # Transcribe audio to SRT format
            with open(temp_audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="srt"  # Getting transcription in SRT format
                )

            st.success("Audio transcribed successfully!")

            # Translate transcription for each selected language
            for language in languages:
                if language not in st.session_state.translations:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a very helpful and talented translator who can translate SRT files."},
                            {"role": "user", "content": f"Could you please translate the SRT text below to {language}? Do not add any comments, just translate. Keep the same SRT format and timestamps.\n\n{transcription}"}
                        ]
                    )
                    translated_srt = response.choices[0].message.content
                    st.session_state.translations[language] = translated_srt

                    # Remove timestamps from translated SRT for TTS
                    text_only = remove_time_codes(translated_srt)
                    audio_file_path = text_to_speech(text_only, language_code={'English': 'en', 'Spanish': 'es', 'French': 'fr', 'German': 'de', 'Chinese': 'zh', 'Turkish': 'tr'}[language])
                    st.session_state.audio_files[language] = audio_file_path

            st.success("Translation and TTS completed!")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

# Display and provide download links for translated SRT files
if st.session_state.translations:
    for language, translated_srt in st.session_state.translations.items():
        st.subheader(f"Translated SRT in {language}")
        st.text_area(f"{language} SRT Translation", translated_srt, height=300)

        st.download_button(
            label=f"Download Translated SRT ({language})",
            data=translated_srt,
            file_name=f"translated_subtitles_{language}.srt",
            mime="text/plain"
        )

        # Provide download link for the TTS audio file
        st.download_button(
            label=f"Download Audio in {language}",
            data=open(st.session_state.audio_files[language], "rb").read(),
            file_name=f"translated_audio_{language}.mp3",
            mime="audio/mpeg"
        )

# Instructions
st.sidebar.header("Instructions")
st.sidebar.markdown("""
1. Upload a video file (mp4, avi, or mov format).
2. Select the desired languages for translation.
3. Click 'Transcribe and Translate' to process the video.
4. View the translated SRT files and download them.
5. Download the translated audio in the selected languages.
""")
