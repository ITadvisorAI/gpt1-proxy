import os
import time
import json
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)
TEMP_FOLDER = "temp_sessions"

# Ensure TEMP_FOLDER exists
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)

@app.route("/")
def index():
    return "GPT1 Proxy Server is live"

@app.route("/start_analysis", methods=["POST"])
def start_analysis():
    try:
        data = request.get_json()
        if not data:
            logging.error("❌ No JSON payload received")
            return jsonify({"error": "No JSON payload received"}), 400

        email = data.get("email")
        goal = data.get("goal")

        if not email or not goal:
            logging.error("❌ Missing required fields: email or goal")
            return jsonify({"error": "Missing required fields"}), 400

        timestamp = time.strftime("%Y%m%d%H%M%S")
        sanitized_email = email.replace("@", "_").replace(".", "_")
        session_id = f"Temp_{timestamp}_{sanitized_email}"

        session_folder = os.path.join(TEMP_FOLDER, session_id)
        os.makedirs(session_folder, exist_ok=True)

        logging.info(f"📁 Created session folder: {session_folder}")
        logging.info(f"📧 Email: {email} | 📝 Goal: {goal}")

        return jsonify({
            "session_id": session_id,
            "folder_url": session_id  # Folder name itself is returned
        }), 200

    except Exception as e:
        logging.exception("🔥 Exception in start_analysis")
        return jsonify({"error": str(e)}), 500

@app.route("/list_files", methods=["POST"])
def list_files():
    try:
        data = request.get_json()
        session_id = data.get("session_id")
        email = data.get("email")

        if not session_id or not email:
            logging.error("❌ Missing session_id or email in list_files")
            return jsonify({"error": "Missing session_id or email"}), 400

        session_folder = os.path.join(TEMP_FOLDER, session_id)
        if not os.path.exists(session_folder):
            logging.warning(f"⚠️ Folder not found: {session_folder}")
            return jsonify({"files": []}), 200

        files = os.listdir(session_folder)
        logging.info(f"📄 Found files in {session_folder}: {files}")
        return jsonify({"files": files}), 200

    except Exception as e:
        logging.exception("🔥 Exception in list_files")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
