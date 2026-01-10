"""
Locust passive load generation for AI monitoring demo.

This file defines passive background traffic for:
1. Realistic AI monitoring data in New Relic
2. A/B model comparison with feedback events
3. Diverse prompt testing (MCP, chat, errors, boundaries)

Configured for 5-10 requests per hour for continuous demo data.
"""

import os
import random

from locust import HttpUser, task, constant_pacing

# Import comprehensive prompt pool (copied during Docker build)
try:
    from prompt_pool import get_weighted_random_prompt, get_prompt_stats
    print("[LOCUST] Loaded prompt pool:", get_prompt_stats())
except ImportError as e:
    print(f"[LOCUST] WARNING: Could not import prompt_pool: {e}")
    print("[LOCUST] Falling back to basic prompts")

# Configuration
AI_AGENT_URL = os.getenv("AI_AGENT_URL", "http://ai-agent:8001")
FLASK_UI_URL = os.getenv("FLASK_UI_URL", "http://flask-ui:8501")


# NOTE: ModelAUser, ModelBUser, ChatModelAUser, ChatModelBUser classes removed
# Replaced with single PassiveLoadUser that uses comprehensive prompt pool


class PassiveLoadUser(HttpUser):
    """
    Passive load generator for realistic AI monitoring demo data.

    Configuration:
    - Runs 5-10 requests per hour (configured via constant_pacing)
    - Uses comprehensive 18-prompt pool with weighted distribution:
      - MCP prompts: 15% (healthy: 10%, degraded: 5%)
      - Simple chat: 35%
      - Complex chat: 30%
      - Error prompts: 10%
      - Boundary testing: 8%
      - Abusive language: 2%
    - Sends each prompt to both Model A and Model B for comparison
    - Automatically generates feedback events via New Relic integration

    Usage:
    - Designed to run continuously in the background
    - Provides realistic demo data for New Relic AI monitoring
    """
    host = AI_AGENT_URL

    # 5-10 requests per hour = 1 request every 6-12 minutes
    # Since each task sends to both models (2 requests), we pace at 12 minutes
    # This gives ~10 requests/hour total (5 per model)
    wait_time = constant_pacing(720)  # 12 minutes = 720 seconds

    def on_start(self):
        """
        Execute immediately when user spawns (before any wait_time).

        This ensures the first request happens right away for immediate
        feedback that load generation is working, then subsequent requests
        follow the 720s pacing interval.
        """
        print("[LOCUST] on_start: Sending initial request immediately...")
        self.send_weighted_prompt_to_both_models()

    @task
    def send_weighted_prompt_to_both_models(self):
        """
        Send a weighted-random prompt from the comprehensive pool to both models.

        Uses realistic distribution across all prompt categories for varied
        telemetry data in New Relic.
        """
        try:
            prompt_data = get_weighted_random_prompt()
        except NameError:
            # Fallback if prompt_pool not imported
            prompt_data = {
                "prompt": "Check the current system status",
                "category": "fallback",
                "description": "Fallback prompt"
            }

        message = prompt_data["prompt"]
        category = prompt_data["category"]
        description = prompt_data.get("description", "")
        endpoint = prompt_data.get("endpoint", "/chat")
        workflow = prompt_data.get("workflow", "N/A")

        print(f"[LOCUST] Sending prompt: {category} - {description[:50]} (endpoint={endpoint})")

        # Send to Model A
        self._send_to_model(
            message=message,
            model="a",
            category=category,
            description=description,
            prompt_data=prompt_data
        )

        # Send to Model B
        self._send_to_model(
            message=message,
            model="b",
            category=category,
            description=description,
            prompt_data=prompt_data
        )

    def _send_to_model(self, message: str, model: str, category: str, description: str, prompt_data: dict):
        """
        Send a prompt to a specific model using appropriate endpoint.

        Args:
            message: The prompt text
            model: Model identifier ("a" or "b")
            category: Prompt category for stats grouping
            description: Human-readable description
            prompt_data: Full prompt dictionary with endpoint/workflow info
        """
        # Determine endpoint and parameters based on prompt configuration
        endpoint = prompt_data.get('endpoint', '/chat')
        use_workflow = prompt_data.get('use_workflow', False)
        workflow_name = prompt_data.get('workflow', None)

        if use_workflow and workflow_name and endpoint == '/repair':
            # MCP tool prompts: Use /repair endpoint with backend workflow
            url = f"/repair?model={model}&workflow={workflow_name}"
            request_body = None  # /repair with workflow doesn't need body
            print(f"[LOCUST] Sending to /repair with workflow={workflow_name}, model={model}")
        else:
            # Conversational prompts: Use /chat endpoint
            url = "/chat"
            request_body = {"message": message, "model": model}

        with self.client.post(
            url,
            json=request_body,
            catch_response=True,
            name=f"{category} (Model {model.upper()})",
            timeout=120  # 2 minute timeout for complex workflows
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    response.success()
                    endpoint_label = f"workflow={workflow_name}" if use_workflow else "chat"
                    print(
                        f"[LOCUST] ✓ Model {model.upper()}: {category} "
                        f"({endpoint_label}, {response.elapsed.total_seconds():.1f}s)"
                    )
                except Exception as e:
                    response.failure(f"Invalid JSON response: {e}")
            else:
                response.failure(
                    f"Model {model.upper()} failed: HTTP {response.status_code}"
                )
                print(f"[LOCUST] ✗ Model {model.upper()}: {category} failed")


# ===== Usage Notes =====
#
# This locustfile is designed for passive background load generation.
#
# To run passive load for demo data generation (recommended):
#   locust -f locustfile.py --host http://ai-agent:8001 --headless \
#     --users 1 --spawn-rate 1 --run-time 24h
#
# Configuration:
#   - 1 user = ~10 requests/hour (5 per model)
#   - Comprehensive 18-prompt pool with weighted distribution
#   - Automatic feedback event generation via New Relic
#   - A/B model comparison (each prompt sent to both models)
#
# The load generation automatically starts with the service and runs
# continuously in the background to provide realistic demo data.
#
