from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Webhook URL for the unified analysis flow
MAKE_WEBHOOK_START_ANALYSIS = os.getenv(
    "MAKE_WEBHOOK_START_ANALYSIS",
    "https://hook.us2.make.com/1ivi9q9x6l253tikb557hemgtl7n2bv9"  # Replace with your actual webhook if needed
)

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

@app.route("/")
def index():
    return "Proxy Server Running", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # default to 5000 for local testing
    app.run(host="0.0.0.0", port=port)
