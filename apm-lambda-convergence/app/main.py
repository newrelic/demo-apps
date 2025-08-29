from flask import Flask, render_template, jsonify, request
import os
import requests
import json

app = Flask(__name__)

# The URL for the deployed API Gateway endpoint
API_GATEWAY_URL = os.getenv('API_GATEWAY_URL')

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
    """Invokes the backend Lambda function via API Gateway."""
    if not API_GATEWAY_URL:
        return jsonify({
            "error": "API_GATEWAY_URL is not configured on the server."
        }), 500

    try:
        # Get the original action ('success' or 'error') from the frontend
        action_data = request.get_json()

        # Forward the request to the API Gateway endpoint
        headers = {'Content-Type': 'application/json'}
        response = requests.post(API_GATEWAY_URL, headers=headers, json=action_data)

        # Ensure the response from the API Gateway is valid JSON
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        
        # Return the JSON response from the Lambda function directly to the frontend
        return response.json(), response.status_code

    except requests.exceptions.HTTPError as http_err:
        # Handle HTTP errors from API Gateway (e.g., 403 Forbidden, 502 Bad Gateway)
        print(f"HTTP error occurred: {http_err}")
        try:
            # Try to return the error response from the API/Lambda if available
            return http_err.response.json(), http_err.response.status_code
        except json.JSONDecodeError:
            return jsonify({"error": "Received a non-JSON error response from the API.", "details": http_err.response.text}), 500
            
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)