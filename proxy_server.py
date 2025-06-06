import os
import time
import threading
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

TEMP_FOLDER = "temp_sessions"
IT_ASSESSMENT_WEBHOOK = "https://it-assessment-api.onrender.com/start_assessment"

@app.route("/")
def index():
    return "GPT1 Proxy Server is live"

@app.route("/start_analysis", methods=["POST"])
def start_analysis():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON payload"}), 400

        email = data.get("email")
        goal = data.get("goal")
        files = data.get("files", [])
        session_id = data.get("session_id")
        next_action_webhook = data.get("next_action_webhook")

        if not email or not goal or not session_id:
            return jsonify({"error": "Missing required fields"}), 400

        # Create session folder using session_id as folder name
        session_folder = os.path.join(TEMP_FOLDER, session_id)
        os.makedirs(session_folder, exist_ok=True)
        print(f"📁 Session folder created: {session_folder}")

        print(f"📧 Email: {email} | 📂 Files: {len(files)}")
        print("🚀 Starting background thread for assessment")

        def trigger_assessment():
            payload = {
                "session_id": session_id,
                "email": email,
                "files": files,
                "next_action_webhook": next_action_webhook
            }
            try:
                r = requests.post(IT_ASSESSMENT_WEBHOOK, json=payload)
                r.raise_for_status()
                print("✅ Assessment trigger sent successfully")
            except Exception as e:
                print(f"❌ Failed to trigger assessment: {e}")

        threading.Thread(target=trigger_assessment).start()

        return jsonify({"message": "Assessment started"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/list_files", methods=["POST"])
def list_files():
    try:
        data = request.get_json()
        session_id = data.get("session_id")

        if not session_id:
            return jsonify({"error": "Missing session_id"}), 400

        session_folder = os.path.join(TEMP_FOLDER, session_id)
        if not os.path.exists(session_folder):
            return jsonify({"files": []})

        files = os.listdir(session_folder)
        return jsonify({"files": files}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
