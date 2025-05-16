from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Set this as an environment variable or hardcode it if needed
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL", "https://hook.us2.make.com/1ivi9q9x6l253tikb557hemgtl7n2bv9")

@app.route("/start_session", methods=["POST"])
def start_session():
    try:
        payload = request.get_json()
        headers = {"Content-Type": "application/json"}
        response = requests.post(MAKE_WEBHOOK_URL, json=payload, headers=headers)
        return jsonify({"status": response.status_code, "response": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index():
    return "Proxy Server Running", 200
