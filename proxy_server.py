from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
import requests
import os
import io

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# === Flask App ===
app = Flask(__name__)

# === Constants ===
MAKE_WEBHOOK_START_ANALYSIS = os.getenv(
    "MAKE_WEBHOOK_START_ANALYSIS",
    "https://hook.us2.make.com/1ivi9q9x6l253tikb557hemgtl7n2bv9"
)

DRIVE_TEMP_FOLDER_ID = os.getenv("DRIVE_TEMP_FOLDER_ID")  # Must be set in Render or .env
SERVICE_ACCOUNT_FILE = "/service_account.json"

# === Google Drive Client Setup ===
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=["https://www.googleapis.com/auth/drive"]
)
drive_service = build('drive', 'v3', credentials=creds)

# === POST /start_analysis ===
@app.route("/start_analysis", methods=["POST"])
def start_analysis():
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "No JSON payload received"}), 400

        email = payload.get("email")
        goal = payload.get("goal")
        files = payload.get("files")

        if not email or not goal or not files:
            return jsonify({"error": "Missing one or more required fields: email, goal, files"}), 400

        headers = {"Content-Type": "application/json"}

        print("📩 Forwarding start_analysis request...")
        print(f"📧 Email: {email}")
        print(f"🎯 Goal: {goal}")
        print(f"📎 File count: {len(files)}")

        response = requests.post(MAKE_WEBHOOK_START_ANALYSIS, json=payload, headers=headers)

        return jsonify({
            "status": response.status_code,
            "response": response.text
        }), response.status_code

    except Exception as e:
        print("❌ Error during start_analysis forwarding:", str(e))
        return jsonify({"error": str(e)}), 500

# === POST /upload_to_drive ===
@app.route("/upload_to_drive", methods=["POST"])
def upload_to_drive():
    try:
        uploaded_file = request.files["file"]
        file_type = request.form.get("type", "unspecified")
        email = request.form.get("email", "unknown@example.com")

        if not uploaded_file:
            return jsonify({"error": "No file received"}), 400

        filename = secure_filename(uploaded_file.filename)
        print(f"📤 Uploading: {filename} for user {email} (type: {file_type})")

        file_metadata = {
            'name': filename,
            'parents': [DRIVE_TEMP_FOLDER_ID]
        }

        media = MediaIoBaseUpload(uploaded_file.stream, mimetype=uploaded_file.mimetype)
        uploaded = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink'
        ).execute()

        return jsonify({
            "file_name": uploaded["name"],
            "file_id": uploaded["id"],
            "file_url": uploaded["webViewLink"],
            "type": file_type,
            "email": email
        })

    except Exception as e:
        print("❌ Upload error:", str(e))
        return jsonify({"error": str(e)}), 500

# === GET /
@app.route("/")
def index():
    return "Proxy Server Running", 200

# === MAIN ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
