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

        # ✅ Generate session ID here (self-contained logic)
        session_id = f"Temp_{uuid.uuid4().hex[:8]}_{email.replace('@', '_').replace('.', '_')}"
        session_folder = os.path.join(TEMP_FOLDER, session_id)
        os.makedirs(session_folder, exist_ok=True)
        print(f"📁 Session folder created at: {session_folder}")

        return jsonify({
            "session_id": session_id,
            "folder_url": f"https://drive.google.com/folderview?id={session_id}"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
