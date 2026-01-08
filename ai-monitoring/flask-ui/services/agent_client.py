"""
Client for communicating with the AI Agent service.
"""

import json
import logging
import time
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AgentClient:
    """HTTP client for AI Agent API."""

    def __init__(self, base_url: str):
        """
        Initialize the agent client.

        Args:
            base_url: Base URL of the agent service (e.g., http://ai-agent:8001)
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.timeout = 180  # 3 minutes timeout for repairs

    def health_check(self) -> Dict[str, Any]:
        """Check agent service health."""
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def trigger_repair(self, model: str = "a") -> Dict[str, Any]:
        """
        Trigger a repair workflow.

        Args:
            model: Which model to use ("a" or "b")

        Returns:
            Repair result dictionary
        """
        start_time = time.time()
        url = f"{self.base_url}/repair"
        timeout = 180

        logger.info(f"[AGENT-CLIENT] Sending repair request - url={url}, model={model}, timeout={timeout}s")

        try:
            response = self.session.post(
                url,
                params={"model": model},
                timeout=timeout
            )
            elapsed = time.time() - start_time

            logger.info(f"[AGENT-CLIENT] Received response - status={response.status_code}, elapsed={elapsed:.2f}s, model={model}")

            response.raise_for_status()
            return response.json()

        except requests.Timeout as e:
            elapsed = time.time() - start_time
            logger.error(f"[AGENT-CLIENT] Request TIMEOUT - elapsed={elapsed:.2f}s, timeout={timeout}s, model={model}, url={url}")
            return {"error": f"Request timeout after {timeout}s: AI Agent did not respond in time"}

        except requests.ConnectionError as e:
            elapsed = time.time() - start_time
            logger.error(f"[AGENT-CLIENT] CONNECTION ERROR - elapsed={elapsed:.2f}s, model={model}, url={url}, error={str(e)}")
            return {"error": f"Connection failed: Unable to reach AI Agent service ({str(e)})"}

        except requests.HTTPError as e:
            elapsed = time.time() - start_time
            logger.error(f"[AGENT-CLIENT] HTTP ERROR - status={response.status_code}, elapsed={elapsed:.2f}s, model={model}, url={url}")
            return {"error": f"HTTP error {response.status_code}: {str(e)}"}

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[AGENT-CLIENT] UNEXPECTED ERROR - elapsed={elapsed:.2f}s, model={model}, url={url}, error={str(e)}", exc_info=True)
            return {"error": f"Unexpected error: {str(e)}"}

    def send_chat(self, message: str, model: str = "a") -> Dict[str, Any]:
        """
        Send a chat message.

        Args:
            message: User message
            model: Which model to use ("a" or "b")

        Returns:
            Chat response dictionary
        """
        try:
            response = self.session.post(
                f"{self.base_url}/chat",
                json={"message": message, "model": model},
                timeout=120
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            return {"error": "Chat request timed out"}
        except Exception as e:
            return {"error": str(e)}

    def get_status(self) -> Dict[str, Any]:
        """Get agent status and metrics."""
        try:
            response = self.session.get(f"{self.base_url}/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def get_metrics(self) -> Dict[str, Any]:
        """Get detailed metrics for both models."""
        try:
            response = self.session.get(f"{self.base_url}/metrics")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
