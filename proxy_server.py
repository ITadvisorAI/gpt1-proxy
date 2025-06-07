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
    data = request.get_json(force=True)
    email = data.get("email")
    goal = data.get("goal")
    if not email or not goal:
        return jsonify({"error": "Missing email or goal"}), 400

    session_id = f"Temp_{uuid.uuid4().hex[:8]}_{email}"
    folder_path = os.path.join(TEMP_FOLDER, session_id)
    os.makedirs(folder_path, exist_ok=True)

    return jsonify({
        "session_id": session_id,
        "folder_url": f"https://drive.google.com/folderview?id={session_id}"
    })

@app.route("/list_files", methods=["POST"])
def list_files():
    data = request.get_json(force=True)
    session_id = data.get("session_id")
    email = data.get("email")

    folder_path = os.path.join(TEMP_FOLDER, session_id)
    files = os.listdir(folder_path)
    file_list = []
    for fname in files:
        ftype = "hardware" if "hw" in fname.lower() else "software" if "sw" in fname.lower() else "general"
        file_list.append({
            "file_name": fname,
            "file_url": os.path.join(folder_path, fname),
            "type": ftype
        })

    return jsonify({"session_id": session_id, "files": file_list})

@app.route("/user_message", methods=["POST"])
def user_message():
    data = request.get_json(force=True)
    session_id = data.get("session_id")
    message = data.get("message", "").lower()

    if "upload" in message and ("done" in message or "uploaded" in message):
        folder_path = os.path.join(TEMP_FOLDER, session_id)
        files = os.listdir(folder_path)
        file_list = []
        for fname in files:
            ftype = "hardware" if "hw" in fname.lower() else "software" if "sw" in fname.lower() else "general"
            file_list.append({
                "file_name": fname,
                "file_url": os.path.join(folder_path, fname),
                "type": ftype
            })

        payload = {
            "session_id": session_id,
            "email": "user@example.com",
            "goal": "IT transformation",
            "files": file_list,
            "next_action_webhook": ""
        }

        response = requests.post("http://localhost:5000/start_assessment", json=payload)
        return jsonify({"status": "triggered", "assessment_response": response.text}), 200

    return jsonify({"status": "waiting_for_more_input"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
