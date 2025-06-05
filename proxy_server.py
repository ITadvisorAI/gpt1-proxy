from flask import Flask, request, jsonify
import os
import requests
import logging
from threading import Thread

app = Flask(__name__)
TEMP_FOLDER = "temp_sessions"
IT_ASSESSMENT_URL = os.getenv("IT_ASSESSMENT_URL", "https://it-assessment.onrender.com/start_assessment")

logging.basicConfig(level=logging.INFO)

def trigger_it_assessment(payload):
    try:
        logging.info("🚀 Triggering IT Assessment with payload:")
        logging.info(payload)
        response = requests.post(IT_ASSESSMENT_URL, json=payload)
        response.raise_for_status()
        logging.info("✅ IT Assessment triggered successfully")
    except Exception as e:
        logging.error(f"🔥 Failed to trigger IT Assessment: {e}")

@app.route("/", methods=["GET", "HEAD"])
def health_check():
    return "Proxy Server is running", 200

@app.route("/start_analysis", methods=["POST"])
def start_analysis():
    try:
        data = request.get_json(force=True)
        session_id = data.get("session_id")
        email = data.get("email")
        files = data.get("files")
        next_action_webhook = data.get("next_action_webhook", "")

        if not session_id or not email or not files:
            logging.error("❌ Missing required fields in request")
            return jsonify({"error": "Missing session_id, email, or files"}), 400

        session_folder = os.path.join(TEMP_FOLDER, session_id)
        os.makedirs(session_folder, exist_ok=True)
        logging.info(f"📁 Created session folder: {session_folder}")

        # Save metadata for debugging
        with open(os.path.join(session_folder, "metadata.json"), "w") as f:
            import json
            json.dump(data, f, indent=2)

        logging.info("📧 Email: %s | 📂 Files: %d", email, len(files))

        # Trigger assessment in background
        thread = Thread(target=trigger_it_assessment, args=(data,))
        thread.start()

        return jsonify({"status": "Trigger sent"}), 200

    except Exception as e:
        logging.error(f"🔥 Error in /start_analysis: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
