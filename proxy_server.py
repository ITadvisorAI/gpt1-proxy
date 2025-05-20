from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Webhook URLs for different tasks
MAKE_WEBHOOK_START_SESSION = os.getenv("MAKE_WEBHOOK_START_SESSION", "https://hook.us2.make.com/1ivi9q9x6l253tikb557hemgtl7n2bv9")
MAKE_WEBHOOK_UPLOAD_FILES = os.getenv("MAKE_WEBHOOK_UPLOAD_FILES", "https://hook.us2.make.com/5cbueoibwl1jf1tbp2nmjx99mbrns1ie")

@app.route("/start_session", methods=["POST"])
def start_session():
    try:
        payload = request.get_json()
        headers = {"Content-Type": "application/json"}
        response = requests.post(MAKE_WEBHOOK_START_SESSION, json=payload, headers=headers)
        return jsonify({"status": response.status_code, "response": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/upload_files", methods=["POST"])
def upload_files():
    try:
        payload = request.get_json()
        headers = {"Content-Type": "application/json"}
        response = requests.post(MAKE_WEBHOOK_UPLOAD_FILES, json=payload, headers=headers)
        return jsonify({"status": response.status_code, "response": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index():
    return "Proxy Server Running", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # default to 5000 for local testing
    app.run(host="0.0.0.0", port=port)
