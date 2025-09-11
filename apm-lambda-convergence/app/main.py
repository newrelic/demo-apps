from flask import Flask, render_template, jsonify, request
import os
import requests
import json

app = Flask(__name__)

# The internal Docker network URL for the hop-service
HOP_SERVICE_URL = "http://hop-service:8001/invoke"

@app.route('/')
def home():
    """Renders the main page."""
    return render_template('index.html', version=os.getenv('APP_VERSION', 'local'))

@app.route('/health')
def health_check():
    """A simple health check endpoint."""
    return jsonify({"status": "ok"}), 200

@app.route('/invoke-lambda', methods=['POST'])
def invoke_lambda():
    """Invokes the backend Lambda function via the hop service."""
    try:
        action_data = request.get_json()
        headers = {'Content-Type': 'application/json'}

        # Make the request to the intermediate hop-service
        response = requests.post(HOP_SERVICE_URL, headers=headers, json=action_data, timeout=5)

        # The hop-service is already handling HTTP errors from the API Gateway.
        # We can now simply forward the response (whether it's a success or a JSON error)
        # and its status code directly to the browser.
        return response.json(), response.status_code

    except requests.exceptions.RequestException as req_err:
        # This block now only catches true network errors (e.g., timeout, DNS failure)
        # between the webapp and the hop-service.
        print(f"--- WEBAPP-ERROR: A network error occurred trying to reach hop-service: {req_err} ---")
        return jsonify({"error": "A network error occurred between the webapp and the hop-service.", "details": str(req_err)}), 500
            
    except Exception as e:
        print(f"An error occurred in webapp: {e}")
        return jsonify({"error": "An internal server error occurred in the webapp.", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
