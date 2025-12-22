"""
Locust load tests with A/B model comparison.

This file defines load testing scenarios including:
1. Standard target-app traffic simulation
2. A/B testing for Model A vs Model B agent performance
"""

import os
import random
from locust import HttpUser, task, between, constant_pacing

# Configuration
TARGET_APP_URL = os.getenv("TARGET_APP_URL", "http://target-app:8000")
AI_AGENT_URL = os.getenv("AI_AGENT_URL", "http://ai-agent:8001")


class TargetAppUser(HttpUser):
    """
    Base user class that simulates traffic to the target application.

    This represents normal business traffic hitting the application endpoints.
    """
    host = TARGET_APP_URL
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    @task(3)
    def get_health(self):
        """Check health endpoint (most frequent)."""
        self.client.get("/health", name="GET /health")

    @task(2)
    def get_orders(self):
        """Fetch all orders."""
        self.client.get("/orders", name="GET /orders")

    @task(2)
    def get_products(self):
        """Browse product catalog."""
        self.client.get("/products", name="GET /products")

    @task(1)
    def create_order(self):
        """Create a new order."""
        products = ["Widget", "Gadget", "Doohickey", "Thingamajig"]
        product = random.choice(products)
        amount = round(random.uniform(10.0, 500.0), 2)

        self.client.post(
            "/orders",
            json={"product": product, "amount": amount},
            name="POST /orders"
        )

    @task(1)
    def get_specific_product(self):
        """Get a specific product by ID."""
        product_id = random.randint(1, 5)
        self.client.get(f"/products/{product_id}", name="GET /products/:id")


class ModelAUser(HttpUser):
    """
    User class that triggers AI agent repairs using Model A (Llama 3.2 3B).

    This simulates monitoring traffic where Model A is used for diagnostics.
    50% of AI agent traffic uses Model A.
    """
    host = AI_AGENT_URL
    wait_time = constant_pacing(30)  # Run every 30 seconds

    @task
    def check_system_health_model_a(self):
        """
        Periodically check system health and trigger repairs with Model A.

        This simulates an automated monitoring workflow using the smaller, faster model.
        """
        with self.client.get("/status", catch_response=True, name="Agent Status (Model A)") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status check failed: {response.status_code}")

        # Occasionally trigger a repair workflow (20% of the time)
        if random.random() < 0.2:
            with self.client.post(
                "/repair?model=a",
                catch_response=True,
                name="Repair Workflow (Model A)",
                timeout=120  # Repairs can take time
            ) as response:
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        response.success()
                    else:
                        response.failure(f"Repair failed: {result.get('final_status')}")
                else:
                    response.failure(f"Repair request failed: {response.status_code}")


class ModelBUser(HttpUser):
    """
    User class that triggers AI agent repairs using Model B (Llama 3.3 7B).

    This simulates monitoring traffic where Model B is used for diagnostics.
    50% of AI agent traffic uses Model B.
    """
    host = AI_AGENT_URL
    wait_time = constant_pacing(30)  # Run every 30 seconds

    @task
    def check_system_health_model_b(self):
        """
        Periodically check system health and trigger repairs with Model B.

        This simulates an automated monitoring workflow using the larger, more capable model.
        """
        with self.client.get("/status", catch_response=True, name="Agent Status (Model B)") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status check failed: {response.status_code}")

        # Occasionally trigger a repair workflow (20% of the time)
        if random.random() < 0.2:
            with self.client.post(
                "/repair?model=b",
                catch_response=True,
                name="Repair Workflow (Model B)",
                timeout=120  # Repairs can take time
            ) as response:
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        response.success()
                    else:
                        response.failure(f"Repair failed: {result.get('final_status')}")
                else:
                    response.failure(f"Repair request failed: {response.status_code}")


class ChatModelAUser(HttpUser):
    """
    User class that sends chat messages to Model A.

    This simulates users interacting with the chat interface using Model A.
    """
    host = AI_AGENT_URL
    wait_time = constant_pacing(45)  # Chat every 45 seconds

    @task
    def send_chat_message_model_a(self):
        """Send a chat message to Model A."""
        messages = [
            "What is the current system status?",
            "How many containers are running?",
            "Tell me about the target application.",
            "What tools do you have access to?",
            "How do you diagnose failures?"
        ]

        message = random.choice(messages)

        with self.client.post(
            "/chat",
            json={"message": message, "model": "a"},
            catch_response=True,
            name="Chat (Model A)",
            timeout=60
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Chat failed: {response.status_code}")


class ChatModelBUser(HttpUser):
    """
    User class that sends chat messages to Model B.

    This simulates users interacting with the chat interface using Model B.
    """
    host = AI_AGENT_URL
    wait_time = constant_pacing(45)  # Chat every 45 seconds

    @task
    def send_chat_message_model_b(self):
        """Send a chat message to Model B."""
        messages = [
            "What is the current system status?",
            "How many containers are running?",
            "Tell me about the target application.",
            "What tools do you have access to?",
            "How do you diagnose failures?"
        ]

        message = random.choice(messages)

        with self.client.post(
            "/chat",
            json={"message": message, "model": "b"},
            catch_response=True,
            name="Chat (Model B)",
            timeout=60
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Chat failed: {response.status_code}")


# ===== Usage Notes =====
#
# To run with all user classes (A/B split):
#   locust -f locustfile.py --host http://target-app:8000
#
# To run only target app traffic:
#   locust -f locustfile.py --host http://target-app:8000 TargetAppUser
#
# To run only Model A traffic:
#   locust -f locustfile.py --host http://ai-agent:8001 ModelAUser
#
# For A/B comparison in the UI:
#   - Set ModelAUser and ModelBUser to equal weights
#   - Monitor response times and success rates separately
#   - Compare metrics in the Locust UI under "Type" column
#
