import os
import uuid
from flask import Flask, request, jsonify

app = Flask(__name__)

TEMP_FOLDER = 'temp_sessions'

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

        # Create session ID and temp folder
        session_id = f"Temp_{uuid.uuid4().hex[:8]}_{email}"
        session_folder = os.path.join(TEMP_FOLDER, session_id)
        os.makedirs(session_folder, exist_ok=True)

        # Placeholder: Simulate upload folder URL
        folder_url = f"https://drive.google.com/folderview?id={session_id}"

        return jsonify({
            "session_id": session_id,
            "folder_url": folder_url
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/list_files', methods=['POST'])
def list_files():
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        email = data.get('email')

        if not session_id or not email:
            return jsonify({"error": "Missing session_id or email"}), 400

        # Simulate listing files in session folder
        session_folder = os.path.join(TEMP_FOLDER, session_id)
        if not os.path.exists(session_folder):
            return jsonify({"files": []})

        files = os.listdir(session_folder)
        return jsonify({"files": files}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
