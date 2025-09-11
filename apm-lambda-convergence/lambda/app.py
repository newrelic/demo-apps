import json
import platform
import urllib3
import newrelic.agent

def _handle_success(body):
    """
    Handles the successful invocation path.
    """
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
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Downstream API call unexpectedly succeeded."
            })
        }
    except urllib3.exceptions.MaxRetryError as e:
        # This is the expected outcome: the API call failed due to a connection error.
        print(f"Downstream API failure: {e}")
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
    print(f"Request received: {event}")

    try:
        # Step 1: Evaluate JSON from the request body.
        # This will raise a json.JSONDecodeError if the payload is malformed.
        body_str = event.get('body') or '{}'
        body = json.loads(body_str)
        action = body.get("action")

        # Step 2: Route to the appropriate method based on the action.
        if action == "success":
            return _handle_success(body)
        elif action == "error":
            return _handle_error(body)
        else:
            # Handle cases where the action is missing or unknown.
            raise ValueError(f"Invalid or missing action specified in payload: '{action}'")

    except json.JSONDecodeError as e:
        # This block specifically catches malformed JSON from the client.
        print(f"JSON Decode Error: {e}")
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
        print(f"An unexpected error occurred: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "An unexpected error occurred inside the Lambda.",
                "details": str(e)
            })
        }
