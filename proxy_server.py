from flask import Flask, request, jsonify
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

DRIVE_TEMP_FOLDER_ID = os.getenv("DRIVE_TEMP_FOLDER_ID")  # Set in Render dashboard
SERVICE_ACCOUNT_FILE = "/etc/secrets/service_account.json"

# === Google Drive Setup ===
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=["https://www.googleapis.com/auth/drive"]
)
drive_service = build('drive', 'v3', credentials=creds)

# === POST /start_analysis ===
@app.route("/start_analysis", methods=["POST"])
def start_analysis():
    try:
        payload = request.get_json(force=True)
        if not payload:
            return jsonify({"error": "No JSON payload received"}), 400

        email = payload.get("email")
        goal = payload.get("goal")
        files = payload.get("files")

        if not email or not goal or not files:
            return jsonify({"error": "Missing one or more required fields: email, goal, files"}), 400

        print("📩 Forwarding start_analysis request...")
        print(f"📧 Email: {email}")
        print(f"🎯 Goal: {goal}")
        print(f"📎 Files received: {len(files)}")

        headers = {"Content-Type": "application/json"}
        response = requests.post(MAKE_WEBHOOK_START_ANALYSIS, json=payload, headers=headers)

        return jsonify({
            "status": response.status_code,
            "response": response.text
        }), response.status_code

    except Exception as e:
        print("❌ Error in /start_analysis:", str(e))
        return jsonify({"error": str(e)}), 500

# === POST /upload_to_drive ===
@app.route("/upload_to_drive", methods=["POST"])
def upload_to_drive():
    try:
        if "file" not in request.files:
            return jsonify({"error": "Missing file part in the request"}), 400

        uploaded_file = request.files["file"]
        if uploaded_file.filename == "":
            return jsonify({"error": "Uploaded file has no filename"}), 400

        file_type = request.form.get("type", "unspecified")
        email = request.form.get("email", "unknown@example.com")
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

        print(f"✅ File uploaded to Drive: {uploaded['id']}")

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

# === GET / ===
@app.route("/", methods=["GET"])
def index():
    return "Proxy Server Running", 200

# === MAIN ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
