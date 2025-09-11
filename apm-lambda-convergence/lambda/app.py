import json
import platform
import urllib3 # type: ignore
import newrelic.agent # type: ignore
import logging

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
    Handles the gracefully handled error path.
    This version simulates a failure to connect to a downstream service using the native urllib3 library.
    """
    logger.info("Simulating a downstream connection failure.")
    http = urllib3.PoolManager()
    try:
        # Attempt to call a non-existent downstream API using the native library.
        # The timeout ensures the function doesn't hang for too long.
        http.request(
            'GET',
            "http://api.external.dependency/data",
            timeout=2.0
        )

        # This part should ideally not be reached
        logger.warning("Downstream API call unexpectedly succeeded.")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Downstream API call unexpectedly succeeded."
            })
        }
    except urllib3.exceptions.MaxRetryError as e:
        # This is the expected outcome: the API call failed due to a connection error.
        logger.error(f"Downstream API failure: {e}")
        return {
            "statusCode": 503, # Service Unavailable is appropriate here
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
        # Step 1: Evaluate JSON from the request body.
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
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "An unexpected error occurred inside the Lambda.",
                "details": str(e)
            })
        }
