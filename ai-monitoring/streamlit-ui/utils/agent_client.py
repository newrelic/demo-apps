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
            return {"error": "Repair workflow timed out after 3 minutes"}
        except Exception as e:
            return {"error": str(e)}

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


class MCPClient:
    """HTTP client for MCP Server (for direct tool access if needed)."""

    def __init__(self, base_url: str):
        """
        Initialize the MCP client.

        Args:
            base_url: Base URL of the MCP server (e.g., http://mcp-server:8002)
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.timeout = 30

    def docker_ps(self) -> Dict[str, Any]:
        """List all Docker containers."""
        try:
            response = self.session.get(f"{self.base_url}/tools/docker_ps")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def get_container_logs(self, service_name: str, lines: int = 50) -> Dict[str, Any]:
        """Get container logs."""
        try:
            response = self.session.post(
                f"{self.base_url}/tools/docker_logs",
                json={"service_name": service_name, "lines": lines}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def start_load_test(self, users: int = 10, spawn_rate: int = 2, duration: int = 1800) -> Dict[str, Any]:
        """
        Start a Locust load test with PassiveLoadUser.

        Args:
            users: Number of concurrent users (default: 10)
            spawn_rate: Users to spawn per second (default: 2)
            duration: Test duration in seconds (default: 1800 = 30 minutes)

        Returns:
            Result dictionary with success/error status
        """
        try:
            response = self.session.post(
                f"{self.base_url}/tools/locust_start_test",
                json={
                    "users": users,
                    "spawn_rate": spawn_rate,
                    "duration": duration
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            return {"error": "Load test start request timed out"}
        except requests.RequestException as e:
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"error": f"Failed to start load test: {str(e)}"}

    def get_load_test_stats(self) -> Dict[str, Any]:
        """
        Get current load test statistics.

        Returns:
            Dictionary with test stats including status, requests, RPS, etc.
            Returns {"error": "..."} on failure.
        """
        try:
            response = self.session.get(
                f"{self.base_url}/tools/locust_get_stats",
                timeout=10
            )
            response.raise_for_status()
            result = response.json()

            # Parse the JSON string in result field (MCP returns stringified JSON)
            if "result" in result:
                return json.loads(result["result"])
            return result
        except requests.Timeout:
            return {"error": "Stats request timed out"}
        except requests.RequestException as e:
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"error": f"Failed to get stats: {str(e)}"}

    def stop_load_test(self) -> Dict[str, Any]:
        """
        Stop the currently running load test.

        Returns:
            Result dictionary with success/error message
        """
        try:
            response = self.session.get(
                f"{self.base_url}/tools/locust_stop_test",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            return {"error": "Stop request timed out"}
        except requests.RequestException as e:
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"error": f"Failed to stop load test: {str(e)}"}
