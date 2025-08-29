import json
import platform

def handler(event, context):
    """
    Handles both success and error invocation scenarios based on the payload.
    """
    print(f"Request received: {event}")

    try:
        # The event from the frontend/boto3 is a string, needs parsing
        body = json.loads(event.get('body') or event)
        action = body.get("action")

        if action == "success":
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "message": "Lambda invoked successfully!",
                    "python_version": platform.python_version()
                })
            }
        elif action == "error":
            # This simulates a handled error
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "error": "This is a simulated failure from the Lambda."
                })
            }
        else:
            # This simulates a catastrophic failure
            raise ValueError("Invalid action specified in payload.")

    except Exception as e:
        print(f"An error occurred: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "An unexpected error occurred inside the Lambda.",
                "details": str(e)
            })
        }
