import json
import logging
import platform
import random
import time
import urllib3 # type: ignore
import uuid
import newrelic.agent # type: ignore

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def _handle_success(body):
    """
    Handles the successful invocation path.
    """
    logger.info("Handling successful invocation.")
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "message": "Lambda invoked successfully!",
            "python_version": platform.python_version()
        })
    }

def _handle_error(body):
    """
    Handles gracefully handled error paths by randomly selecting
    one of the available error simulation functions.
    """
    # Define the possible error types and randomly select one.
    error_options = ["timeout", "service_error", "parsing_error", "connection_error"]
    error_type = random.choice(error_options)

    logger.info(f"Randomly selected error type to simulate: '{error_type}'")

    # 1. Simulate the downstream service taking too long to respond.
    if error_type == "timeout":
        logger.info("Simulating a 5-second delay to cause a timeout.")
        time.sleep(5) 
        # The request from the hop-service should time out before this completes.
        # If it doesn't, we return an error indicating the timeout simulation failed.
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Simulated timeout did not get interrupted as expected."})
        }

    # 2. Simulate the downstream service returning a 503 Service Unavailable error.
    elif error_type == "service_error":
        logger.error("Simulating a 503 Service Unavailable error from a downstream API.")
        newrelic.agent.notice_error()
        return {
            "statusCode": 503,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "This is a simulated 503 error from a downstream API.",
                "details": "The dependency service is currently unavailable."
            })
        }

    # 3. Simulate receiving malformed JSON from a downstream service.
    elif error_type == "parsing_error":
        malformed_json = '{"message": "Success", "data": [incomplete_array}'
        logger.error(f"Simulating a JSON parsing error with payload: {malformed_json}")
        try:
            json.loads(malformed_json)
        except json.JSONDecodeError as e:
            newrelic.agent.notice_error()
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "error": "Failed to parse response from downstream API.",
                    "details": str(e)
                })
            }

    # 4. Simulate a failure to connect to a downstream service.
    else: # This will be the "connection_error" case
        http = urllib3.PoolManager()
        try:
            http.request(
                'GET',
                "http://api.external.dependency/data",
                timeout=2.0,
                retries=1
            )
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Downstream API call unexpectedly succeeded."})
            }
        except urllib3.exceptions.MaxRetryError as e:
            logger.error(f"Downstream API connection failure: {e}")
            newrelic.agent.notice_error()
            return {
                "statusCode": 503,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "error": "This is a simulated failure to connect to a downstream API.",
                    "details": str(e)
                })
            }

# https://docs.newrelic.com/docs/apm/agents/python-agent/python-agent-api/backgroundtask-python-agent-api/
@newrelic.agent.background_task()
def handler(event, context):
    """
    Main Lambda handler that routes requests based on the payload.
    """
    logger.info(f"Request received: {event}")

    try:
        # Generate a random user ID to help errors inbox show impacted users
        user_id = str(uuid.uuid4())
        newrelic.agent.set_user_id(user_id)
        logging.info(f"User ID for this transaction: {user_id}")

        # This will raise a json.JSONDecodeError if the payload is malformed.
        body_str = event.get('body') or '{}'
        body = json.loads(body_str)
        action = body.get("action")
        logger.info(f"Parsed action from body: '{action}'")

        # Step 2: Route to the appropriate method based on the action.
        if action == "success":
            return _handle_success(body)
        elif action == "error":
            return _handle_error(body)
        else:
            # Handle cases where the action is missing or unknown.
            logger.warning(f"Invalid or missing action specified: '{action}'")
            raise ValueError(f"Invalid or missing action specified in payload: '{action}'")

    except json.JSONDecodeError as e:
        # This block specifically catches malformed JSON from the client.
        logger.error(f"JSON Decode Error: {e}", exc_info=True)

        # Explicitly notify New Relic of the handled exception ***
        newrelic.agent.notice_error()

        return {
            "statusCode": 400, # Bad Request, as the client sent invalid data
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Malformed JSON in request body.",
                "details": str(e)
            })
        }
    except Exception as e:
        # This is a catch-all for any other unexpected errors (like the ValueError above).
        logger.critical(f"An unexpected error occurred: {e}", exc_info=True)

        # Explicitly notify New Relic of the handled exception ***
        newrelic.agent.notice_error()

        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "An unexpected error occurred inside the Lambda.",
                "details": str(e)
            })
        }
