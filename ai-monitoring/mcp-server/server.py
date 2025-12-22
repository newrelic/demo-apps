"""
MCP Server - Exposes Docker and Locust operations as MCP tools.

This server provides the "hands" for the AI agent, allowing it to:
- Inspect and control Docker containers
- Trigger and monitor load tests
- Diagnose system issues
"""

import logging
from fastmcp import FastMCP

# Import tool functions
from tools.docker_tools import (
    docker_ps,
    read_service_logs,
    restart_container,
    inspect_container,
    update_container_env
)
from tools.locust_tools import (
    run_load_test,
    get_load_test_results,
    stop_load_test
)
from config import MCP_PORT, LOG_LEVEL

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("AI Monitoring MCP Server")

logger.info("=" * 60)
logger.info("🔧 MCP Server Initializing")
logger.info("=" * 60)


# ===== Docker Tools =====

@mcp.tool()
def docker_container_list() -> str:
    """
    List all Docker containers with their current status.

    Use this tool to check the health of all containers in the system.
    Returns container names, statuses, images, and health information.
    """
    logger.info("Tool called: docker_container_list")
    return docker_ps()


@mcp.tool()
def docker_logs(service_name: str, lines: int = 50) -> str:
    """
    Read recent logs from a specific container.

    Args:
        service_name: Name of the container (e.g., 'ai-monitoring-target-app')
        lines: Number of log lines to retrieve (default: 50)

    Use this tool to diagnose issues by examining container logs.
    """
    logger.info(f"Tool called: docker_logs({service_name}, lines={lines})")
    return read_service_logs(service_name, lines)


@mcp.tool()
def docker_restart(service_name: str) -> str:
    """
    Restart a specific container.

    Args:
        service_name: Name of the container to restart

    Use this tool to recover from crashes or apply configuration changes.
    """
    logger.info(f"Tool called: docker_restart({service_name})")
    return restart_container(service_name)


@mcp.tool()
def docker_inspect(service_name: str) -> str:
    """
    Get detailed information about a container.

    Args:
        service_name: Name of the container to inspect

    Returns detailed information including environment variables, state, and health.
    Useful for diagnosing configuration issues.
    """
    logger.info(f"Tool called: docker_inspect({service_name})")
    return inspect_container(service_name)


@mcp.tool()
def docker_update_env(service_name: str, key: str, value: str) -> str:
    """
    Update an environment variable for a container.

    Args:
        service_name: Name of the container
        key: Environment variable name
        value: New value for the variable

    Note: Container needs to be restarted for changes to take effect.
    """
    logger.info(f"Tool called: docker_update_env({service_name}, {key}=***)")
    return update_container_env(service_name, key, value)


# ===== Locust Tools =====

@mcp.tool()
def locust_start_test(users: int = 10, spawn_rate: int = 2, duration: int = 60) -> str:
    """
    Start a load test using Locust.

    Args:
        users: Number of concurrent users (default: 10)
        spawn_rate: Users to spawn per second (default: 2)
        duration: Test duration in seconds (default: 60)

    Use this tool to verify system health under load after making repairs.
    """
    logger.info(f"Tool called: locust_start_test(users={users}, spawn_rate={spawn_rate}, duration={duration})")
    return run_load_test(users, spawn_rate, duration)


@mcp.tool()
def locust_get_stats() -> str:
    """
    Get current load test statistics.

    Returns metrics including:
    - Total requests and failures
    - Average response time
    - Requests per second
    - Failure rate

    Use this tool to check if the system is handling load correctly.
    """
    logger.info("Tool called: locust_get_stats")
    return get_load_test_results()


@mcp.tool()
def locust_stop_test() -> str:
    """
    Stop the currently running load test.

    Use this tool to halt load testing when needed.
    """
    logger.info("Tool called: locust_stop_test")
    return stop_load_test()


# ===== Health Check Endpoint =====

@mcp.tool()
def health_check() -> str:
    """Check MCP server health."""
    return "MCP Server is healthy"


# ===== HTTP API for Agent Communication =====

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn

app = FastAPI(title="MCP Server HTTP API")


class ToolRequest(BaseModel):
    """Generic tool request model."""
    service_name: Optional[str] = None
    lines: Optional[int] = 50
    key: Optional[str] = None
    value: Optional[str] = None
    users: Optional[int] = 10
    spawn_rate: Optional[int] = 2
    duration: Optional[int] = 60


@app.get("/health")
async def http_health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mcp-server"}


@app.get("/tools/docker_ps")
async def api_docker_ps():
    """List all containers."""
    return {"result": docker_ps()}


@app.post("/tools/docker_logs")
async def api_docker_logs(request: ToolRequest):
    """Read container logs."""
    if not request.service_name:
        raise HTTPException(status_code=400, detail="service_name is required")
    return {"result": read_service_logs(request.service_name, request.lines or 50)}


@app.post("/tools/docker_restart")
async def api_docker_restart(request: ToolRequest):
    """Restart a container."""
    if not request.service_name:
        raise HTTPException(status_code=400, detail="service_name is required")
    return {"result": restart_container(request.service_name)}


@app.post("/tools/docker_inspect")
async def api_docker_inspect(request: ToolRequest):
    """Inspect a container."""
    if not request.service_name:
        raise HTTPException(status_code=400, detail="service_name is required")
    return {"result": inspect_container(request.service_name)}


@app.post("/tools/docker_update_env")
async def api_docker_update_env(request: ToolRequest):
    """Update container environment variable."""
    if not all([request.service_name, request.key, request.value]):
        raise HTTPException(status_code=400, detail="service_name, key, and value are required")
    return {"result": update_container_env(request.service_name, request.key, request.value)}


@app.post("/tools/locust_start_test")
async def api_locust_start_test(request: ToolRequest):
    """Start load test."""
    return {"result": run_load_test(
        request.users or 10,
        request.spawn_rate or 2,
        request.duration or 60
    )}


@app.get("/tools/locust_get_stats")
async def api_locust_get_stats():
    """Get load test statistics."""
    return {"result": get_load_test_results()}


@app.get("/tools/locust_stop_test")
async def api_locust_stop_test():
    """Stop load test."""
    return {"result": stop_load_test()}


if __name__ == "__main__":
    logger.info(f"Starting MCP Server on port {MCP_PORT}")
    logger.info("Available tools:")
    logger.info("  - docker_container_list: List all containers")
    logger.info("  - docker_logs: Read container logs")
    logger.info("  - docker_restart: Restart a container")
    logger.info("  - docker_inspect: Inspect container details")
    logger.info("  - docker_update_env: Update environment variable")
    logger.info("  - locust_start_test: Start load test")
    logger.info("  - locust_get_stats: Get load test results")
    logger.info("  - locust_stop_test: Stop load test")
    logger.info("=" * 60)

    # Run the HTTP API server
    uvicorn.run(app, host="0.0.0.0", port=MCP_PORT)
