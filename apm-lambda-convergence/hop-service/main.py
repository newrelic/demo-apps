from flask import Flask, jsonify, request
import os
import requests
import json

app = Flask(__name__)

# The URL for the deployed API Gateway endpoint
API_GATEWAY_URL = os.getenv('API_GATEWAY_URL')

@app.route('/health')
def health_check():
    """A simple health check endpoint."""
    return jsonify({"status": "ok"}), 200

@app.route('/invoke', methods=['POST'])
def invoke():
    """Receives a request and forwards it to the API Gateway."""
    if not API_GATEWAY_URL:
        return jsonify({
            "error": "API_GATEWAY_URL is not configured on the hop service."
        }), 500

    try:
        # Get the original action data from the main webapp
        action_data = request.get_json()

        # Forward the request to the API Gateway endpoint
        headers = {'Content-Type': 'application/json'}
        response = requests.post(API_GATEWAY_URL, headers=headers, json=action_data)

        response.raise_for_status()
        
        # Return the JSON response from the Lambda function
        return response.json(), response.status_code

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        try:
            return http_err.response.json(), http_err.response.status_code
        except json.JSONDecodeError:
            return jsonify({"error": "Received a non-JSON error response from the API.", "details": http_err.response.text}), 500
            
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=True)
