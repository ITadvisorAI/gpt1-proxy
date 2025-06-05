
import os
import uuid
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TEMP_FOLDER = "temp_sessions"

@app.route("/")
def index():
    return "GPT1 Proxy Server is live"

@app.route("/start_analysis", methods=["POST"])
def start_analysis():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON payload received"}), 400

        email = data.get("email")
        goal = data.get("goal")
        files = data.get("files", [])
        next_action_webhook = data.get("next_action_webhook")

        if not email or not goal:
            return jsonify({"error": "Missing required fields"}), 400

        # Create session ID and folder
        session_id = f"Temp_{uuid.uuid4().hex[:8]}_{email.replace('@', '_').replace('.', '_')}"
        session_folder = os.path.join(TEMP_FOLDER, session_id)
        os.makedirs(session_folder, exist_ok=True)

        print(f"📁 Session folder created at: {session_folder}")
        print(f"📧 Email: {email} | 📂 Files: {len(files)}")

        downloaded_files = []
        for f in files:
            file_name = f.get("file_name")
            file_url = f.get("file_url")
            if not file_name or not file_url:
                continue

            response = requests.get(file_url)
            if response.status_code == 200:
                file_path = os.path.join(session_folder, file_name)
                with open(file_path, "wb") as out_file:
                    out_file.write(response.content)
                downloaded_files.append({"file_name": file_name, "type": f.get("type", "general")})
                print(f"✅ Downloaded: {file_name}")
            else:
                print(f"❌ Failed to download: {file_name}")

        if next_action_webhook:
            payload = {
                "session_id": session_id,
                "email": email,
                "goal": goal,
                "files": downloaded_files,
                "next_action_webhook": next_action_webhook
            }
            response = requests.post(next_action_webhook, json=payload)
            response.raise_for_status()
            print("🚀 Triggered GPT2 (IT Assessment Module)")

        return jsonify({
            "message": "Files received and session initiated.",
            "session_id": session_id
        }), 200

    except Exception as e:
        print(f"🔥 Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/list_files", methods=["POST"])
def list_files():
    try:
        data = request.get_json()
        session_id = data.get("session_id")
        email = data.get("email")

        if not session_id or not email:
            return jsonify({"error": "Missing session_id or email"}), 400

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
