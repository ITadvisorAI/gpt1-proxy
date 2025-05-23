from flask import Flask, request, jsonify
import requests
import os
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)
BASE_DIR = "temp_sessions"

# === Environment Variables ===
GPT2_ENDPOINT = os.getenv("GPT2_ENDPOINT", "https://it-assessment-api.onrender.com/start_assessment")
DRIVE_ROOT_FOLDER_ID = os.getenv("DRIVE_ROOT_FOLDER_ID")
SERVICE_ACCOUNT_FILE = "/etc/secrets/service_account.json"

# === In-Memory Session Store ===
SESSION_STORE = {}

# === Google Drive Setup ===
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=["https://www.googleapis.com/auth/drive"]
)
drive_service = build('drive', 'v3', credentials=creds)

# === Infer file type ===
def infer_type(name):
    name = name.lower()
    if "asset" in name or "inventory" in name:
        return "asset_inventory"
    elif "gap" in name or "working" in name:
        return "gap_working"
    elif "capacity" in name or "scale" in name:
        return "capacity_plan"
    elif "log" in name or "latency" in name:
        return "log"
    elif "compliance" in name:
        return "compliance_report"
    elif "firewall" in name:
        return "firewall_rules"
    elif "backup" in name:
        return "backup_schedule"
    elif "strategy" in name or "roadmap" in name:
        return "strategy_input"
    return "general"

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

        SESSION_STORE[session_id] = {
            "email": email,
            "goal": goal,
            "folder_url": folder_url,
            "files": []
        }

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

        files_response = [
            {
                "file_name": f["name"],
                "file_url": f["webViewLink"],
                "type": infer_type(f["name"])
            }
            for f in files
        ]

        if session_id in SESSION_STORE:
            SESSION_STORE[session_id]["files"] = files_response

        return jsonify({
            "session_id": session_id,
            "email": email,
            "files": files_response
        }), 200

    except Exception as e:
        print("❌ Error in /list_files:", str(e))
        return jsonify({"error": str(e)}), 500

# === POST /trigger_assessment ===
@app.route("/trigger_assessment", methods=["POST"])
def trigger_assessment():
    try:
        payload = request.get_json(force=True)
        session_id = payload.get("session_id")

        if not session_id or session_id not in SESSION_STORE:
            return jsonify({"error": "Invalid or unknown session_id"}), 400

        session = SESSION_STORE[session_id]
        email = session["email"]
        goal = session["goal"]
        files = session["files"]

        # 🔁 Dynamic fallback: Pull from Drive if memory has no files
        if not files:
            print(f"[WARN] No in-memory files for session {session_id}, checking Drive...")
            folder_query = f"name = '{session_id}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            folders = drive_service.files().list(q=folder_query, fields="files(id)").execute().get('files', [])
            if folders:
                folder_id = folders[0]['id']
                file_query = f"'{folder_id}' in parents and trashed = false"
                files_from_drive = drive_service.files().list(q=file_query, fields="files(id, name, webViewLink)").execute().get('files', [])
                files = [
                    {
                        "file_name": f["name"],
                        "file_url": f["webViewLink"],
                        "type": infer_type(f["name"])
                    } for f in files_from_drive
                ]
                if not files:
                    return jsonify({"error": "Still no files found in Drive for this session"}), 400
                SESSION_STORE[session_id]["files"] = files
            else:
                return jsonify({"error": "Session folder not found in Drive"}), 404

        request_payload = {
            "session_id": session_id,
            "email": email,
            "goal": goal,
            "files": files,
            "next_action_webhook": "https://market-gap-analysis.onrender.com/start_market_gap"
        }

        print(f"🚀 Triggering assessment for {session_id} at {GPT2_ENDPOINT}")
        headers = {"Content-Type": "application/json"}
        response = requests.post(GPT2_ENDPOINT, json=request_payload, headers=headers)
        response.raise_for_status()

        return jsonify({
            "status": "assessment_triggered",
            "gpt2_response": response.text
        }), 200

    except Exception as e:
        print("❌ Error in /trigger_assessment:", str(e))
        return jsonify({"error": str(e)}), 500

# === Health Check ===
@app.route("/", methods=["GET"])
def index():
    return "Proxy Server Running", 200

# === MAIN ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
