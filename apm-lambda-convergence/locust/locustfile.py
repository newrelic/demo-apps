from locust import HttpUser, task, between

class WebAppUser(HttpUser):
    """
    User class that defines the behavior of a simulated user for the demo web app.
    """
    # Each user will wait a random time between 0.5 and 2 seconds after each task.
    wait_time = between(0.5, 2)

    @task(47)
    def successful_journey(self):
        """
        Simulates a user journey:
        1. Load the home page.
        2. Invoke the 'success' action.
        This is the most common user path.
        """
        # Step 1: Load the home page
        self.client.get(
            "/",
            name="Journey - Load Home Page"
        )
        
        # Step 2: Invoke the success action
        self.client.post(
            "/invoke-lambda",
            json={"action": "success"},
            name="Journey - Invoke Lambda (Success)"
        )

    @task(2)
    def error_journey(self):
        """
        Simulates a user journey that results in a handled error (400 response).
        This task weight results in an error rate of ~4%.
        """
        # Step 1: Load the home page
        self.client.get(
            "/",
            name="Journey - Load Home Page" # Grouped with the other home page loads
        )

        # Step 2: Invoke the error action
        self.client.post(
            "/invoke-lambda",
            json={"action": "error"},
            name="Journey - Invoke Lambda (Error)"
        )

    @task(1)
    def malformed_json_journey(self):
        """
        Simulates a client sending a malformed JSON payload,
        which will cause an unhandled exception in the Lambda (500 response).
        This task weight results in an error rate of ~2%.
        """
        # Step 1: Load the home page
        self.client.get(
            "/",
            name="Journey - Load Home Page" # Grouped with the other home page loads
        )

        # Step 2: Post a broken JSON string
        self.client.post(
            "/invoke-lambda",
            data='{"action": "bad-json", "extra-key": }', # Malformed JSON
            headers={'Content-Type': 'application/json'},
            name="Journey - Invoke Lambda (Bad JSON)"
        )

    def on_start(self):
        """
        This method is called when a new user is started.
        """
        print("A new simulated user is starting.")
