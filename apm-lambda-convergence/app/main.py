from flask import Flask, render_template, jsonify, request # type: ignore
import logging
import os
import requests # type: ignore
import newrelic.agent # type: ignore

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

@app.before_request
def before_request():
    """Disable New Relic browser autorum before each request; this would usually be in the .ini"""
    newrelic.agent.disable_browser_autorum()

# The internal Docker network URL for the hop-service
HOP_SERVICE_URL = "http://hop-service:8001/invoke"

@app.route('/')
def home():
    """Renders the main page."""
    logging.info("Serving home page.")
    return render_template('index.html', version=os.getenv('APP_VERSION', 'local'))

@app.route('/health')
def health_check():
    """A simple health check endpoint."""
    logging.info("Health check endpoint was called.")
    return jsonify({"status": "ok"}), 200

@app.route('/invoke-lambda', methods=['POST'])
def invoke_lambda():
    """Invokes the backend Lambda function via the hop service."""
    logging.info("Received request to invoke Lambda.")
    try:
        action_data = request.get_json()
        logging.info(f"Action data received: {action_data}")
        headers = {'Content-Type': 'application/json'}

        # Make the request to the intermediate hop-service
        logging.info(f"Forwarding request to hop-service at {HOP_SERVICE_URL}")
        response = requests.post(HOP_SERVICE_URL, headers=headers, json=action_data, timeout=5)
        logging.info(f"Received response from hop-service with status code: {response.status_code}")

        # The hop-service is already handling HTTP errors from the API Gateway.
        # We can now simply forward the response (whether it's a success or a JSON error)
        # and its status code directly to the browser.
        return response.json(), response.status_code

    except requests.exceptions.RequestException as req_err:
        # This block now only catches true network errors (e.g., timeout, DNS failure)
        # between the webapp and the hop-service.
        logging.error(f"A network error occurred trying to reach hop-service: {req_err}")
        return jsonify({"error": "A network error occurred between the webapp and the hop-service.", "details": str(req_err)}), 500
            
    except Exception as e:
        logging.error(f"An unexpected error occurred in webapp: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred in the webapp.", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
