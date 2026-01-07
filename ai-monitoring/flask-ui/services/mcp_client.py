"""
Client for communicating with the MCP Server.
"""

import json
import requests
from typing import Dict, Any


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
