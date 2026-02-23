import os
from locust import HttpUser, task, between

TARGET = os.getenv("TARGET_HOST", "http://app-1:8080")

class SimpleUser(HttpUser):
    host = TARGET
    wait_time = between(0.1, 1)

    @task
    def hello(self):
        self.client.get("/hello")
