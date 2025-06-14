from flask import Flask, request, jsonify
import requests
import os
import time
import json
import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

GPT2_ENDPOINT = os.getenv(
    "GPT2_ENDPOINT",
    "https://it-assessment-api.onrender.com/start_assessment"
)
DRIVE_ROOT_FOLDER_ID = os.getenv("DRIVE_ROOT_FOLDER_ID")
SERVICE_ACCOUNT_FILE = "/etc/secrets/service_account.json"
SESSION_TRACKER_SHEET_ID = "1eSIPIUaQfnoQD7QCyleHyQv1d9Sfy73Z70pnGl8hrYs"

SESSION_STORE = {}

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=[
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets"
    ]
)
drive_service = build('drive', 'v3', credentials=creds)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(SESSION_TRACKER_SHEET_ID).sheet1

def infer_type(name):
    name = name.lower()
    if "asset" in name or "inventory" in name:
        return "asset_inventory"
    elif "gap" in name or "working" in name:
        return "gap_working"
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
    return "general"

@app.route("/start_analysis", methods=["POST"])
def start_analysis():
    try:
        payload = request.get_json(force=True)
        email = payload.get("email")
        goal = payload.get("goal")

        if not email or not goal:
            return jsonify({"error": "Missing required fields"}), 400

        timestamp = time.strftime("%Y%m%d%H%M%S")
        session_id = f"Temp_{timestamp}_{email.replace('@', '_').replace('.', '_')}"
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

        # ✅ Grant public write access to the folder
        drive_service.permissions().create(
            fileId=folder['id'],
            body={"type": "anyone", "role": "writer"},
            fields="id"
        ).execute()
        print(f"[DEBUG] Shared folder with public write access")

        folder_url = folder.get('webViewLink')
        print(f"[DEBUG] Folder created at: {folder_url}")

        # Store folder ID for downstream GPT calls
        SESSION_STORE[session_id] = {
            "email": email,
            "goal": goal,
            "folder_url": folder_url,
            "folder_id": folder['id'],
            "files": []
        }

        sheet.append_row([
            timestamp,
            email,
            session_id,
            goal,
            folder_url,
            "Session Created"
        ])

        return jsonify({
            "session_id": session_id,
            "folder_url": folder_url,
            "status": "session_created"
        }), 200

    except Exception as e:
        print("❌ Error in /start_analysis:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route("/list_files", methods=["POST"])
def list_files():
    try:
        payload = request.get_json(force=True)
        session_id = payload.get("session_id")
        email = payload.get("email")

        print(f"[DEBUG] Listing files for session: {session_id}")

        if not session_id or not email:
            return jsonify({"error": "Missing session_id or email"}), 400

        folder_query = (
            f"name = '{session_id}' and mimeType = 'application/vnd.google-apps.folder' "
            "and trashed = false"
        )
        folders = drive_service.files().list(
            q=folder_query,
            fields="files(id, name)",
            spaces="drive",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute().get('files', [])

        if not folders:
            return jsonify({"error": f"No folder found for session_id: {session_id}"}), 404

        folder_id = folders[0]['id']
        file_query = f"'{folder_id}' in parents and trashed = false"

        resp = drive_service.files().list(
            q=file_query,
            spaces="drive",
            fields="files(id, name, mimeType, webViewLink)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        print(
            f"[DEBUG] Drive API returned files for session {session_id}: {resp.get('files', [])}",
            flush=True
        )

        files = resp.get('files', [])

        for f in files:
            try:
                drive_service.permissions().create(
                    fileId=f["id"],
                    body={"role": "reader", "type": "anyone"},
                    fields="id"
                ).execute()
            except Exception as share_error:
                print(
                    f"⚠️ Could not make file public: {f['name']} – {share_error}"
                )

        files_response = [
            {
                "file_name": f["name"],
                "file_url": (
                    f"https://drive.google.com/uc?export=download&id={f['id']}"
                ),
                "type": infer_type(f["name"])
            }
            for f in files
        ]

        SESSION_STORE[session_id]["files"] = files_response

        return jsonify({
            "session_id": session_id,
            "email": email,
            "files": files_response
        }), 200

    except Exception as e:
        print("❌ Error in /list_files:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route("/user_message", methods=["POST"])
def user_message():
    try:
        data = request.get_json(force=True)
        print(f"[DEBUG] Raw payload: {data}", flush=True)
        session_id = data.get("session_id")
        message = data.get("message", "").lower().strip()
        print(f"[DEBUG] Parsed message for session {session_id}: {message}", flush=True)

        if session_id not in SESSION_STORE:
            return jsonify({"error": "Invalid session_id"}), 400

        # Refresh file list inside user_message
        folder_query = (
            f"name = '{session_id}' and mimeType = 'application/vnd.google-apps.folder' "
            "and trashed = false"
        )
        folders = drive_service.files().list(
            q=folder_query,
            fields="files(id, name)",
            spaces="drive",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute().get('files', [])
        if folders:
            folder_id = folders[0]['id']
            resp = drive_service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                spaces="drive",
                fields="files(id, name, mimeType, webViewLink)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            fresh_files = resp.get('files', [])
            SESSION_STORE[session_id]["files"] = [
                {"file_name": f["name"], "file_url": f"https://drive.google.com/uc?export=download&id={f['id']}", "type": infer_type(f["name"]) }
                for f in fresh_files
            ]

        files_ready = SESSION_STORE[session_id].get("files")

        if (
            ("upload" in message and ("done" in message or "uploaded" in message))
            or message == "retry"
        ):
            if not files_ready:
                print(
                    f"[WARN] Files not ready for session {session_id}. Delaying assessment trigger."
                )
                return jsonify({"status": "waiting_for_files"}), 200

            payload = {
                "session_id": session_id,
                "email": SESSION_STORE[session_id]["email"],
                "goal": SESSION_STORE[session_id]["goal"],
                "folder_id": SESSION_STORE[session_id]["folder_id"],
                "files": files_ready
            }

            print(f"[DEBUG] Triggering GPT2 POST to: {GPT2_ENDPOINT}")
            print(f"[DEBUG] Full payload:\n{json.dumps(payload, indent=2)}")

            try:
                response = requests.post(GPT2_ENDPOINT, json=payload)
                print(f"[DEBUG] GPT2 responded with status: {response.status_code}")
                print(f"[DEBUG] GPT2 response body: {response.text}")
                sheet.append_row([
                    time.strftime("%Y%m%d%H%M%S"),
                    SESSION_STORE[session_id]["email"],
                    session_id,
                    SESSION_STORE[session_id]["goal"],
                    SESSION_STORE[session_id]["folder_url"],
                    "Assessment Triggered"
                ])
                return jsonify({"status": "triggered"}), 200

            except Exception as post_error:
                print(f"❌ POST to GPT2 failed: {post_error}")
                return jsonify({"error": str(post_error)}), 500

        if message.startswith("yes"):
            return jsonify({"status": "already_triggered"}), 200

        return jsonify({"status": "waiting_for_more_input"}), 200

    except Exception as e:
        print("❌ Error in /user_message:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def index():
    return "Proxy Server Running", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"[INFO] Starting server on port {port}")
    app.run(host="0.0.0.0", port=port)
