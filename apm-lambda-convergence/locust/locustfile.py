from locust import HttpUser, task, between

class WebAppUser(HttpUser):
    """
    User class that defines the behavior of a simulated user for the demo web app.
    """
    # Wait time between tasks for each user, between 1 and 3 seconds.
    wait_time = between(1, 3)

    @task(2) # This task will be picked twice as often as the others
    def load_home_page(self):
        """Simulates a user visiting the home page."""
        self.client.get(
            "/",
            name="Load Home Page" # Group all root requests under this name in the UI
        )

    @task(1)
    def invoke_success(self):
        """
        Simulates a user clicking the 'Invoke Success' button by sending a POST
        request to the /invoke-lambda endpoint with the 'success' action.
        """
        self.client.post(
            "/invoke-lambda",
            json={"action": "success"},
            name="Invoke Lambda (Success)" # Group success calls in the UI
        )

    @task(1)
    def invoke_error(self):
        """
        Simulates a user clicking the 'Invoke Error' button by sending a POST
        request to the /invoke-lambda endpoint with the 'error' action.
        """
        self.client.post(
            "/invoke-lambda",
            json={"action": "error"},
            name="Invoke Lambda (Error)" # Group error calls in the UI
        )

    def on_start(self):
        """
        This method is called when a new user is started.
        Good for login actions or initial setup.
        """
        print("A new simulated user is starting.")

