"""
Client for communicating with the AI Agent service.
"""

import json
import requests
from typing import Dict, Any, Optional


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
        try:
            response = self.session.post(
                f"{self.base_url}/repair",
                params={"model": model},
                timeout=180
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            return {"error": "Timeout: Repair workflow exceeded 3 minute limit"}
        except requests.ConnectionError as e:
            return {"error": f"Connection failed: Unable to reach AI Agent service ({str(e)})"}
        except requests.HTTPError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def compare_repairs(self) -> Dict[str, Any]:
        """
        Run repair with both models and compare.

        Returns:
            Comparison result dictionary
        """
        try:
            response = self.session.post(
                f"{self.base_url}/repair/compare",
                timeout=360  # 6 minutes for both models
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            return {"error": "Comparison timed out after 6 minutes"}
        except Exception as e:
            return {"error": str(e)}

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

    def compare_chat(self, message: str) -> Dict[str, Any]:
        """
        Send the same message to both models and compare.

        Args:
            message: User message

        Returns:
            Comparison dictionary with both responses
        """
        try:
            response = self.session.post(
                f"{self.base_url}/chat/compare",
                params={"message": message},
                timeout=240
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            return {"error": "Chat comparison timed out"}
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
