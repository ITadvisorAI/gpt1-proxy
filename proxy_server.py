import os
import json
import shutil
import threading
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_FOLDER = os.path.join(BASE_DIR, "temp_sessions")

GPT2_ENDPOINT = os.getenv("GPT2_ENDPOINT", "https://it-assessment-api.onrender.com/start_assessment")

@app.route('/')
def index():
    return "GPT1 Proxy Server is running"

@app.route('/upload_to_drive', methods=['POST'])
def upload_to_drive():
    data = request.get_json()
    session_id = data.get('session_id')
    folder_path = os.path.join(TEMP_FOLDER, session_id)
    os.makedirs(folder_path, exist_ok=True)

    for file in data.get("files", []):
        file_name = file["file_name"]
        file_url = file["file_url"]
        local_path = os.path.join(folder_path, file_name)
        try:
            r = requests.get(file_url)
            r.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(r.content)
            print(f"✅ Downloaded {file_name}")
        except Exception as e:
            print(f"❌ Failed to download {file_name}: {e}")
    
    return jsonify({"status": "files downloaded"})

@app.route('/list_files', methods=['POST'])
def list_files():
    data = request.get_json()
    session_id = data.get("session_id")
    folder_path = os.path.join(TEMP_FOLDER, session_id)
    files = os.listdir(folder_path)
    classified = []

    for f in files:
        file_type = "asset_inventory" if "inventory" in f.lower() else "general"
        classified.append({
            "file_name": f,
            "type": file_type,
            "file_url": f"https://your-storage-domain.com/{session_id}/{f}"  # Placeholder URL
        })

    print(f"📦 Classified {len(classified)} files in session {session_id}")

    # Automatically trigger assessment after classification
    try:
        trigger_payload = {
            "session_id": session_id,
            "email": data.get("email"),
            "goal": data.get("goal"),
            "files": classified,
            "next_action_webhook": data.get("next_action_webhook")
        }
        headers = {"Content-Type": "application/json"}
        r = requests.post(GPT2_ENDPOINT, json=trigger_payload, headers=headers)
        r.raise_for_status()
        print(f"🚀 Triggered assessment for session {session_id}")
    except Exception as e:
        print(f"❌ Failed to trigger assessment for session {session_id}: {e}")

    return jsonify({"status": "files classified", "files": classified})

@app.route('/start_analysis', methods=['POST'])
def start_analysis():
    data = request.get_json()
    print("📩 /start_analysis received:", data)  # Debugging line

    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400

    session_folder = os.path.join(TEMP_FOLDER, session_id)
    if not os.path.exists(session_folder):
        return jsonify({"error": "Session folder does not exist"}), 404

    print(f"📁 Session folder validated: {session_id}")
    return jsonify({"status": "ready"})

@app.route('/delete_session', methods=['POST'])
def delete_session():
    data = request.get_json()
    session_id = data.get("session_id")
    session_folder = os.path.join(TEMP_FOLDER, session_id)
    try:
        shutil.rmtree(session_folder)
        print(f"🗑️ Deleted session folder: {session_id}")
        return jsonify({"status": "session deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
