import os
import requests
import time
import pandas as pd
import json
from datetime import datetime
from googletrans import Translator
import streamlit as st
from configure import auth_key

# AssemblyAI API Endpoints
UPLOAD_URL = "https://api.assemblyai.com/v2/upload"
TRANSCRIBE_URL = "https://api.assemblyai.com/v2/transcript"

# Define Folders
AUDIO_FOLDER = "audio_files"
BASE_OUTPUT_FOLDER = "transcriptions"
os.makedirs(AUDIO_FOLDER, exist_ok=True)
os.makedirs(BASE_OUTPUT_FOLDER, exist_ok=True)

# Initialize Google Translator
translator = Translator()

# Function to Upload Audio Files
def upload_audio_file(file_path):
    headers = {'authorization': auth_key}
    with open(file_path, 'rb') as f:
        response = requests.post(UPLOAD_URL, headers=headers, files={'file': f})
    if response.status_code == 200:
        return response.json()['upload_url']
    else:
        st.error(f"Upload Error {response.status_code}: {response.text}")
        return None

# Function to Transcribe Audio Files
def transcribe_audio(upload_url):
    headers = {
        "authorization": auth_key,
        "content-type": "application/json"
    }
    json_payload = {
        "audio_url": upload_url,
        "language_detection": True
    }
    response = requests.post(TRANSCRIBE_URL, json=json_payload, headers=headers)
    if response.status_code == 200:
        return response.json()["id"]
    else:
        st.error(f"Transcription Error {response.status_code}: {response.text}")
        return None

# Function to Poll Transcription Status
def poll_transcription_status(transcript_id):
    headers = {"authorization": auth_key}
    poll_url = f"{TRANSCRIBE_URL}/{transcript_id}"

    while True:
        response = requests.get(poll_url, headers=headers)
        result = response.json()

        status = result.get("status")
        if status == "completed":
            detected_language = result.get("language_code", "unknown")
            transcription_text = result["text"]
            return transcription_text, detected_language
        elif status == "failed":
            st.error("Transcription Failed!")
            return None, None
        else:
            time.sleep(5)

# Function to Save Transcriptions
def save_transcription_to_file(file_name, text, lang_code):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    lang_folder = os.path.join(BASE_OUTPUT_FOLDER, lang_code)
    os.makedirs(lang_folder, exist_ok=True)
    output_file = os.path.join(lang_folder, f"{file_name}_{lang_code}_{timestamp}.txt")

    with open(output_file, "w") as f:
        f.write(text)
    return output_file

# Function to Export Transcription to CSV
def export_to_csv(data, file_name="transcriptions.csv"):
    df = pd.DataFrame(data)
    return df.to_csv(index=False).encode("utf-8")

# Function to Export Transcription to JSON
def export_to_json(data):
    return json.dumps(data, indent=4).encode("utf-8")

# Function to Export Transcription to TXT
def export_to_txt(data):
    txt_output = ""
    for item in data:
        txt_output += f"File Name: {item['File Name']}\n"
        txt_output += f"Language: {item['Language']}\n"
        txt_output += f"Transcription Text:\n{item['Transcription Text']}\n\n"
        txt_output += f"Translated Text (English):\n{item['Translated Text (English)']}\n\n{'-'*80}\n\n"
    return txt_output.encode("utf-8")

# Streamlit App Layout
st.title("🎙️ Audio Transcription Web App - Multiple File Uploads ")

uploaded_files = st.file_uploader("Upload Multiple Audio Files (MP3/WAV/FLAC)", type=["mp3", "wav", "flac"], accept_multiple_files=True)

if uploaded_files:
    transcription_results = []

    progress_bar = st.progress(0)
    status_text = st.empty()
    total_files = len(uploaded_files)

    for idx, uploaded_file in enumerate(uploaded_files):
        file_name = uploaded_file.name
        file_path = os.path.join(AUDIO_FOLDER, file_name)

        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())

        status_text.text(f"🔄 Processing {file_name}...")
        upload_url = upload_audio_file(file_path)
        if upload_url:
            transcript_id = transcribe_audio(upload_url)
            if transcript_id:
                transcription_text, detected_language = poll_transcription_status(transcript_id)

                if transcription_text:
                    st.success(f"✅ Completed: {file_name} - Language: {detected_language}")
                    st.text_area(f"Transcription for {file_name}", transcription_text, height=200)

                    translated_text = translator.translate(transcription_text, src=detected_language, dest="en").text
                    st.text_area(f"Translated (English) - {file_name}", translated_text, height=200)

                    saved_file = save_transcription_to_file(file_name, transcription_text, detected_language)

                    # Save result in list for export
                    transcription_results.append({
                        "File Name": file_name,
                        "Language": detected_language,
                        "Transcription Text": transcription_text,
                        "Translated Text (English)": translated_text
                    })

        # Update Progress Bar
        progress_percentage = (idx + 1) / total_files
        progress_bar.progress(progress_percentage)

    # Export Section
    if transcription_results:
        st.download_button(
            label="📥 Download CSV",
            data=export_to_csv(transcription_results),
            file_name="transcriptions.csv",
            mime="text/csv"
        )

        st.download_button(
            label="📥 Download JSON",
            data=export_to_json(transcription_results),
            file_name="transcriptions.json",
            mime="application/json"
        )

        st.download_button(
            label="📥 Download TXT",
            data=export_to_txt(transcription_results),
            file_name="transcriptions.txt",
            mime="text/plain"
        )

        # Detailed Table
        st.subheader("📄 Detailed Transcriptions Table")
        df = pd.DataFrame(transcription_results)
        st.dataframe(df[['File Name', 'Language', 'Transcription Text', 'Translated Text (English)']])

