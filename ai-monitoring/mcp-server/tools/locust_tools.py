"""
Locust tools for MCP server.
Provides load testing operations via Locust HTTP API.
"""

import json
import logging
import httpx
from config import LOCUST_URL

logger = logging.getLogger(__name__)

# Initialize HTTP client for Locust API
locust_client = httpx.Client(base_url=LOCUST_URL, timeout=30.0)


def run_load_test(users: int = 10, spawn_rate: int = 2, duration: int = 60) -> str:
    """
    Start a load test using Locust.

    Args:
        users: Number of concurrent users to simulate (default: 10)
        spawn_rate: Users to spawn per second (default: 2)
        duration: Test duration in seconds (default: 60)

    Returns:
        Success or error message
    """
    try:
        # Start the load test via Locust's HTTP API
        response = locust_client.post(
            "/swarm",
            data={
                "user_count": users,
                "spawn_rate": spawn_rate,
                "host": "http://target-app:8000"
            }
        )

        if response.status_code == 200:
            logger.info(f"Load test started: {users} users, {spawn_rate}/s spawn rate, {duration}s duration")
            return (f"✓ Load test started successfully\n"
                    f"Users: {users}\n"
                    f"Spawn rate: {spawn_rate}/s\n"
                    f"Duration: {duration}s\n"
                    f"Target: http://target-app:8000")
        else:
            error_msg = f"Failed to start load test: HTTP {response.status_code}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    except httpx.RequestError as e:
        error_msg = f"Error connecting to Locust: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"
    except Exception as e:
        error_msg = f"Error starting load test: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"


def get_load_test_results() -> str:
    """
    Get current load test statistics from Locust.

    Returns:
        JSON string with load test metrics including:
        - Request statistics (count, failures, avg response time)
        - RPS (requests per second)
        - Error rates
    """
    try:
        response = locust_client.get("/stats/requests")

        if response.status_code == 200:
            stats = response.json()

            # Extract key metrics
            total_stats = stats.get('stats', [])
            if not total_stats:
                return json.dumps({"message": "No load test data available yet"})

            # Find aggregate stats
            aggregate = next((s for s in total_stats if s.get('name') == 'Aggregated'), None)

            if aggregate:
                result = {
                    "status": "running" if stats.get('state') == 'running' else "stopped",
                    "total_requests": aggregate.get('num_requests', 0),
                    "total_failures": aggregate.get('num_failures', 0),
                    "avg_response_time": aggregate.get('avg_response_time', 0),
                    "min_response_time": aggregate.get('min_response_time', 0),
                    "max_response_time": aggregate.get('max_response_time', 0),
                    "requests_per_second": aggregate.get('current_rps', 0),
                    "failure_rate": aggregate.get('fail_ratio', 0),
                    "user_count": stats.get('user_count', 0)
                }
            else:
                result = {"message": "Aggregate stats not available", "raw_stats": total_stats}

            logger.info("Retrieved load test results")
            return json.dumps(result, indent=2)

        else:
            error_msg = f"Failed to get load test results: HTTP {response.status_code}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})

    except httpx.RequestError as e:
        error_msg = f"Error connecting to Locust: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error getting load test results: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})


def stop_load_test() -> str:
    """
    Stop the currently running load test.

    Returns:
        Success or error message
    """
    try:
        response = locust_client.get("/stop")

        if response.status_code == 200:
            logger.info("Load test stopped successfully")
            return "✓ Load test stopped successfully"
        else:
            error_msg = f"Failed to stop load test: HTTP {response.status_code}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    except httpx.RequestError as e:
        error_msg = f"Error connecting to Locust: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"
    except Exception as e:
        error_msg = f"Error stopping load test: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"
