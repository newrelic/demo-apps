"""
Locust load tests with A/B model comparison.

This file defines load testing scenarios including:
1. Flask UI traffic simulation
2. A/B testing for Model A vs Model B agent performance
3. Chat interface load testing
"""

import os
import random
from locust import HttpUser, task, between, constant_pacing

# Configuration
AI_AGENT_URL = os.getenv("AI_AGENT_URL", "http://ai-agent:8001")
FLASK_UI_URL = os.getenv("FLASK_UI_URL", "http://flask-ui:8501")


# NOTE: TargetAppUser class removed - target-app service no longer exists in current architecture
# Current architecture focuses on Flask UI and AI Agent services


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
    User class that triggers AI agent repairs using Model B (Llama 3.1 8B).

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


# ===== Prompt Pools for PassiveLoadUser =====

# Tool-invoking prompts (40%) - trigger MCP tool usage
TOOL_PROMPTS = [
    "Check the current system status and tell me if there are any issues",
    "What services are running right now?",
    "Can you check the logs for the api-gateway service?",
    "Run diagnostics on all services",
    "Are there any failed services?",
    "Inspect the health of the authentication service",
    "Show me the system status",
    "Check if the database service needs to be restarted",
    "What's the health status of all services?",
    "Investigate why the system might be slow",
    "List all running services with their status",
    "Check the auth-service logs",
    "What's wrong with the api-gateway?",
    "Diagnose any failures in the system",
    "Show me the service health checks",
]

# Simple conversational prompts (50%) - no tool usage
SIMPLE_PROMPTS = [
    "Hello",
    "What tools do you have access to?",
    "Tell me about yourself",
    "What can you help me with?",
    "Explain what you do",
    "What is this system for?",
    "How do you diagnose failures?",
    "What models are you using?",
    "Thanks for your help",
    "Can you explain your capabilities?",
    "What's your purpose?",
    "How does this demo work?",
    "Tell me about the AI monitoring demo",
    "What's the difference between the two models?",
    "Hi there",
]

# Error-causing prompts (10%) - trigger various errors
ERROR_PROMPTS = [
    "",  # Empty message
    "   ",  # Whitespace only
    "A" * 5000,  # Very long prompt (may timeout)
    '{"invalid": "json}',  # Malformed JSON characters
    "Restart all containers immediately without checking anything",  # May cause agent errors
    "Delete everything now",  # Unreasonable request
    "\x00\x01\x02",  # Control characters
    "🔥" * 500,  # Emoji spam
]


class PassiveLoadUser(HttpUser):
    """
    Passive load generator for demo data generation.

    Sends prompts to both Model A and Model B sequentially with
    weighted distribution: 40% tool-invoking, 50% simple, 10% error-causing.
    Designed to create realistic AI monitoring data for New Relic demos.
    """
    host = AI_AGENT_URL
    wait_time = constant_pacing(18)  # Each user sends ~3.3 request cycles/min

    @task(40)
    def send_tool_prompt_to_both_models(self):
        """Send a tool-invoking prompt to both models."""
        prompt = random.choice(TOOL_PROMPTS)
        self._send_to_both_models(prompt, "Tool Prompt")

    @task(50)
    def send_simple_prompt_to_both_models(self):
        """Send a simple prompt to both models."""
        prompt = random.choice(SIMPLE_PROMPTS)
        self._send_to_both_models(prompt, "Simple Prompt")

    @task(10)
    def send_error_prompt_to_both_models(self):
        """Send an error-causing prompt to both models."""
        prompt = random.choice(ERROR_PROMPTS)
        self._send_to_both_models(prompt, "Error Prompt")

    def _send_to_both_models(self, message: str, prompt_type: str):
        """
        Send the same message to both Model A and Model B sequentially.

        Args:
            message: The prompt to send
            prompt_type: Category for Locust stats grouping
        """
        # Send to Model A
        with self.client.post(
            "/chat",
            json={"message": message, "model": "a"},
            catch_response=True,
            name=f"{prompt_type} (Model A)",
            timeout=120
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Model A failed: {response.status_code}")

        # Send to Model B
        with self.client.post(
            "/chat",
            json={"message": message, "model": "b"},
            catch_response=True,
            name=f"{prompt_type} (Model B)",
            timeout=120
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Model B failed: {response.status_code}")


# ===== Usage Notes =====
#
# To run with all user classes (A/B split):
#   locust -f locustfile.py --host http://ai-agent:8001
#
# To run only Model A traffic:
#   locust -f locustfile.py --host http://ai-agent:8001 ModelAUser
#
# To run only Model B traffic:
#   locust -f locustfile.py --host http://ai-agent:8001 ModelBUser
#
# To run passive load for demo data generation:
#   locust -f locustfile.py --host http://ai-agent:8001 PassiveLoadUser --users 10 --run-time 30m
#
# For A/B comparison in the UI:
#   - Set ModelAUser and ModelBUser to equal weights
#   - Monitor response times and success rates separately
#   - Compare metrics in the Locust UI under "Type" column
#
