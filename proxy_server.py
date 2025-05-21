from flask import Flask, request, jsonify
import requests
import os
import time

from google.oauth2 import service_account
from googleapiclient.discovery import build

# === Flask App ===
app = Flask(__name__)

# === Environment Variables ===
MAKE_WEBHOOK_START_ANALYSIS = os.getenv(
    "MAKE_WEBHOOK_START_ANALYSIS",
    "https://hook.us2.make.com/1ivi9q9x6l253tikb557hemgtl7n2bv9"
)
MAKE_WEBHOOK_START_ASSESSMENT = os.getenv(
    "MAKE_WEBHOOK_START_ASSESSMENT",
    "https://hook.us2.make.com/placeholder-assessment-endpoint"
)
DRIVE_ROOT_FOLDER_ID = os.getenv("DRIVE_ROOT_FOLDER_ID")
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
        email = payload.get("email")
        goal = payload.get("goal")

        if not email or not goal:
            return jsonify({"error": "Missing required fields: email and goal"}), 400

        timestamp = time.strftime("%Y%m%d%H%M%S")
        session_id = f"Temp_{timestamp}_{email}"
        print(f"[DEBUG] Creating session: {session_id}")

        folder_metadata = {
            'name': session_id,
            'parents': [DRIVE_ROOT_FOLDER_ID],
            'mimeType': 'application/vnd.google-apps.folder'
        }

        folder = drive_service.files().create(
            body=folder_metadata,
            fields='id, webViewLink'
        ).execute()

        folder_url = folder.get('webViewLink')
        print(f"[DEBUG] Folder created: {folder_url}")

        tracker_payload = {
            "session_id": session_id,
            "email": email,
            "goal": goal,
            "folder_url": folder_url
        }

        headers = {"Content-Type": "application/json"}
        response = requests.post(MAKE_WEBHOOK_START_ANALYSIS, json=tracker_payload, headers=headers)
        response.raise_for_status()
        print("[DEBUG] Make.com webhook triggered successfully")

        return jsonify({
            "session_id": session_id,
            "folder_url": folder_url,
            "status": "session_created"
        }), 200

    except Exception as e:
        print("❌ Error in /start_analysis:", str(e))
        return jsonify({"error": str(e)}), 500

# === POST /list_files ===
@app.route("/list_files", methods=["POST"])
def list_files():
    try:
        payload = request.get_json(force=True)
        session_id = payload.get("session_id")
        email = payload.get("email")

        if not session_id or not email:
            return jsonify({"error": "Missing session_id or email"}), 400

        print(f"[DEBUG] Listing files for session: {session_id}")

        folder_query = f"name = '{session_id}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        folders = drive_service.files().list(q=folder_query, fields="files(id, name)").execute().get('files', [])

        if not folders:
            return jsonify({"error": f"No folder found for session_id: {session_id}"}), 404

        folder_id = folders[0]['id']

        file_query = f"'{folder_id}' in parents and trashed = false"
        files = drive_service.files().list(q=file_query, fields="files(id, name, mimeType, webViewLink)").execute().get('files', [])

        def infer_type(name):
            name = name.lower()
            if "asset" in name or "inventory" in name:
                return "asset_inventory"
            elif "capacity" in name or "scale" in name:
                return "capacity_plan"
            elif "log" in name or "latency" in name:
                return "network_logs"
            elif "compliance" in name:
                return "compliance_report"
            elif "firewall" in name:
                return "firewall_rules"
            elif "backup" in name:
                return "backup_schedule"
            elif "strategy" in name or "roadmap" in name:
                return "strategy_input"
            return "unspecified"

        files_response = [
            {
                "file_name": f["name"],
                "file_url": f["webViewLink"],
                "type": infer_type(f["name"])
            }
            for f in files
        ]

        return jsonify({
            "session_id": session_id,
            "email": email,
            "files": files_response
        }), 200

    except Exception as e:
        print("❌ Error in /list_files:", str(e))
        return jsonify({"error": str(e)}), 500

# === POST /start_assessment ===
@app.route("/start_assessment", methods=["POST"])
def start_assessment():
    try:
        payload = request.get_json(force=True)
        session_id = payload.get("session_id")
        email = payload.get("email")
        goal = payload.get("goal")
        files = payload.get("files")

        if not session_id or not email or not goal or not files:
            return jsonify({"error": "Missing required fields"}), 400

        print(f"[DEBUG] Starting assessment for: {session_id} ({email})")
        headers = {"Content-Type": "application/json"}
        response = requests.post(MAKE_WEBHOOK_START_ASSESSMENT, json=payload, headers=headers)
        response.raise_for_status()

        return jsonify({
            "status": "assessment_triggered",
            "response": response.text
        }), 200

    except Exception as e:
        print("❌ Error in /start_assessment:", str(e))
        return jsonify({"error": str(e)}), 500

# === Health Check ===
@app.route("/", methods=["GET"])
def index():
    return "Proxy Server Running", 200

# === MAIN ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
