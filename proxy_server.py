
import os
import uuid
import json
import requests
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configurations
TEMP_FOLDER = "/tmp/temp_sessions"
os.makedirs(TEMP_FOLDER, exist_ok=True)

GPT2_ENDPOINT = os.getenv("GPT2_ENDPOINT", "https://it-assessment-api.onrender.com/start_assessment")
GPT3_ENDPOINT = os.getenv("GPT3_ENDPOINT", "https://dummy-next-gpt3.webhook.com")  # placeholder

@app.route('/')
def index():
    return 'GPT1 Proxy Server is live'

@app.route('/start_analysis', methods=['POST'])
def start_analysis():
    print("📥 /start_analysis called")
    data = request.get_json(force=True)
    email = data.get("email")
    goal = data.get("goal")

    if not email or not goal:
        return jsonify({"error": "Missing email or goal"}), 400

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    clean_email = email.replace("@", "_").replace(".", "_")
    session_id = f"Temp_{timestamp}_{clean_email}"
    session_folder = os.path.join(TEMP_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    print(f"📁 Created session folder: {session_folder}")

    return jsonify({
        "session_id": session_id,
        "folder_url": f"https://drive.google.com/folderview?id={session_id}"
    })

@app.route('/list_files', methods=['POST'])
def list_files():
    data = request.get_json(force=True)
    print("📄 /list_files called")
    return jsonify({"status": "Files received", "files": data})

@app.route('/user_message', methods=['POST'])
def user_message():
    print("📩 /user_message called")
    try:
        data = request.get_json(force=True)
        session_id = data.get("session_id")
        email = data.get("email")
        goal = data.get("goal")
        files = data.get("files", [])

        print(f"🧾 session_id: {session_id}")
        print(f"📧 email: {email}")
        print(f"🎯 goal: {goal}")
        print(f"📎 files: {json.dumps(files, indent=2)}")

        print(f"🔁 Triggering GPT2 at: {GPT2_ENDPOINT}")
        response = requests.post(
            GPT2_ENDPOINT,
            json={
                "session_id": session_id,
                "email": email,
                "goal": goal,
                "files": files,
                "next_action_webhook": GPT3_ENDPOINT
            }
        )
        print(f"✅ GPT2 responded: {response.status_code} - {response.text}")
        return jsonify({"status": "Assessment started", "response": response.json()})
    except Exception as e:
        print(f"❌ Error in /user_message: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
