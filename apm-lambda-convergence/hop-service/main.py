from flask import Flask, jsonify, request # type: ignore
import json
import logging
import os
import requests # type: ignore

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

@app.route('/invoke', methods=['POST'])
def invoke_lambda_proxy():
    """
    Receives a request from the main webapp and forwards it to the API Gateway.
    """
    logging.info("Hop-service received a request to proxy.")
    # Read the environment variable at request time for robustness
    api_gateway_url = os.getenv('API_GATEWAY_URL')

    if not api_gateway_url:
        logging.error("API_GATEWAY_URL is not configured.")
        return jsonify({
            "error": "API_GATEWAY_URL is not configured on the server."
        }), 500

    try:
        # Get the original action ('success' or 'error') from the frontend
        action_data = request.get_json()
        logging.info(f"Forwarding action '{action_data.get('action')}' to API Gateway: {api_gateway_url}")

        # Forward the request to the API Gateway endpoint
        headers = {'Content-Type': 'application/json'}
        response = requests.post(api_gateway_url, headers=headers, json=action_data, timeout=4)
        logging.info(f"Received response from API Gateway with status: {response.status_code}")

        # Let the requests library raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()
        
        # On success, return the JSON response from the Lambda
        return response.json(), response.status_code

    except requests.exceptions.HTTPError as http_err:
        # This block catches non-2xx responses from the API Gateway/Lambda.
        # We try to return the JSON error body from the Lambda if it exists.
        logging.warning(f"HTTP error occurred calling API Gateway: {http_err}")
        try:
            return http_err.response.json(), http_err.response.status_code
        except json.JSONDecodeError:
            # If the error response isn't JSON, return a generic error.
            logging.error(f"Received a non-JSON error response from the API: {http_err.response.text}")
            return jsonify({"error": "Received a non-JSON error response from the API.", "details": http_err.response.text}), 500
            
    except requests.exceptions.RequestException as req_err:
        # This block catches network errors (e.g., timeout, DNS failure)
        logging.error(f"A network error occurred trying to reach the API Gateway: {req_err}")
        return jsonify({"error": "A network error occurred trying to reach the API Gateway.", "details": str(req_err)}), 500
            
    except Exception as e:
        # Catch any other unexpected errors.
        logging.critical(f"An unexpected error occurred in the hop-service: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred in the hop-service.", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=True)
