import os
import uuid
from flask import Flask, request, jsonify

app = Flask(__name__)

# Set absolute path for temp_sessions directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_FOLDER = os.path.join(BASE_DIR, 'temp_sessions')
os.makedirs(TEMP_FOLDER, exist_ok=True)  # Ensure the temp_sessions folder exists

@app.route('/')
def index():
    return 'GPT1 Proxy Server is live'

@app.route('/start_analysis', methods=['POST'])
def start_analysis():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON payload received"}), 400

        email = data.get('email')
        goal = data.get('goal')

        if not email or not goal:
            return jsonify({"error": "Missing required fields in request"}), 400

        # Create session ID
        safe_email = email.replace('@', '_').replace('.', '_')
        session_id = f"Temp_{uuid.uuid4().hex[:8]}_{safe_email}"
        session_folder = os.path.join(TEMP_FOLDER, session_id)

        os.makedirs(session_folder, exist_ok=True)
        print(f"📁 Creating session folder at: {session_folder}")

        # Debug check
        if os.path.exists(session_folder):
            print(f"✅ Folder exists: {session_folder}")
        else:
            print(f"❌ Failed to create folder: {session_folder}")

        # Simulate upload folder URL
        folder_url = f"https://drive.google.com/folderview?id={session_id}"

        return jsonify({
            "session_id": session_id,
            "folder_url": folder_url
        }), 200

    except Exception as e:
        print(f"🔥 Exception in /start_analysis: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/list_files', methods=['POST'])
def list_files():
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        email = data.get('email')

        if not session_id or not email:
            return jsonify({"error": "Missing session_id or email"}), 400

        session_folder = os.path.join(TEMP_FOLDER, session_id)
        if not os.path.exists(session_folder):
            print(f"⚠️ Session folder not found: {session_folder}")
            return jsonify({"files": []}), 200

        files = os.listdir(session_folder)
        print(f"📂 Listed {len(files)} files in: {session_folder}")
        return jsonify({"files": files}), 200

    except Exception as e:
        print(f"🔥 Exception in /list_files: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
