from flask import Flask, request, jsonify, render_template
from pydub import AudioSegment
from pydub.utils import which
import openai
import os
import requests
import shutil

app = Flask(__name__, static_folder="static", template_folder="templates")
UPLOAD_FOLDER = 'uploads/'
CHUNK_LENGTH_MS = 600000  # 10 minutes
openai.api_key = os.getenv("OPENAI_API_KEY")

# Ensure FFMPEG is correctly configured
AudioSegment.converter = which("ffmpeg")
AudioSegment.ffprobe = which("ffprobe")

# Function to delete only the files inside the 'uploads' folder
def clear_upload_folder():
    """Delete all files inside the 'uploads' folder without deleting the folder."""
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)  # Delete the file or link
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)  # Delete sub-directory (if any)
        except Exception as e:
            app.logger.error(f"Failed to delete {file_path}. Reason: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'file' not in request.files:
        return "No file part", 400

    audio_file = request.files['file']
    audio_path = os.path.join(UPLOAD_FOLDER, audio_file.filename)
    audio_file.save(audio_path)

    try:
        # Split the audio file into 5-minute chunks
        audio_chunks = split_audio(audio_path)

        # Transcribe each chunk sequentially
        full_transcription = " ".join(
            [transcribe_audio_with_whisper(chunk) for chunk in audio_chunks]
        )

        # Clean up uploaded files
        clear_upload_folder()

        return jsonify({"transcription": full_transcription})
    except Exception as e:
        return str(e), 500

def split_audio(file_path):
    """Split the audio file into 5-minute chunks and save them."""
    audio = AudioSegment.from_file(file_path)
    chunk_paths = []

    for i in range(0, len(audio), CHUNK_LENGTH_MS):
        chunk = audio[i:i + CHUNK_LENGTH_MS]
        chunk_path = f"{UPLOAD_FOLDER}/chunk_{i // CHUNK_LENGTH_MS}.m4a"
        chunk.export(chunk_path, format="mp4", codec="aac")
        chunk_paths.append(chunk_path)

    return chunk_paths

def transcribe_audio_with_whisper(audio_file_path):
    """Transcribe a single audio chunk using OpenAI's Whisper API."""
    if os.path.getsize(audio_file_path) > 25 * 1024 * 1024:
        raise ValueError("Audio file exceeds 25 MB size limit.")

    with open(audio_file_path, "rb") as audio_file:
        response = openai.Audio.transcribe(
            model="whisper-1", file=audio_file, response_format="text"
        )

    if isinstance(response, dict) and 'text' in response:
        return response['text']
    elif isinstance(response, str):
        return response
    else:
        raise ValueError(f"Unexpected response format: {response}")

@app.route('/generate-notes', methods=['POST'])
def generate_notes():
    """Generate comprehensive notes from the transcription."""
    data = request.json
    transcription = data.get('transcription', '')

    if not transcription:
        return "Transcription required", 400

    notes = send_to_4o_api(transcription)
    return jsonify({"notes": notes})

def send_to_4o_api(transcription):
    """Send the transcription to GPT-4 for note generation."""
    api_url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are an expert-level note-taker."},
            {"role": "user", "content": f"Create a note guide:\n\n{transcription}"}
        ],
        "temperature": 0.5
    }

    try:
        response = requests.post(api_url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None

if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
