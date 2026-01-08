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
from tools.system_tools import (
    check_system_health,
    get_service_logs,
    restart_service,
    check_database_status,
    update_configuration,
    run_diagnostics
)
from config import MCP_PORT, LOG_LEVEL

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress noisy HTTP request logs from httpx (polling endpoints)
logging.getLogger('httpx').setLevel(logging.WARNING)
# Note: uvicorn access logs disabled via access_log=False in uvicorn.run()

# Initialize FastMCP server
mcp = FastMCP("AI Monitoring MCP Server")

logger.info("=" * 60)
logger.info("🔧 MCP Server Initializing")
logger.info("=" * 60)


# ===== System Operations Tools =====

@mcp.tool()
def system_health() -> str:
    """
    Check overall system health including all services and resource usage.

    Returns:
    - Status of all monitored services
    - CPU, memory, and disk usage metrics
    - Network throughput

    Use this to get a comprehensive view of system status.
    """
    logger.info("Tool called: system_health")
    return check_system_health()


@mcp.tool()
def service_logs(service_name: str, lines: int = 50) -> str:
    """
    Retrieve recent logs from a specific service.

    Args:
        service_name: Name of the service (e.g., 'api-gateway', 'auth-service')
        lines: Number of log lines to retrieve (default: 50)

    Use this to diagnose issues or understand service behavior.
    """
    logger.info(f"Tool called: service_logs({service_name}, lines={lines})")
    return get_service_logs(service_name, lines)


@mcp.tool()
def service_restart(service_name: str) -> str:
    """
    Restart a specific service.

    Args:
        service_name: Name of the service to restart

    Use this to recover from failures or apply configuration changes.
    Simulates a graceful service restart with appropriate delay.
    """
    logger.info(f"Tool called: service_restart({service_name})")
    return restart_service(service_name)


@mcp.tool()
def database_status() -> str:
    """
    Check database health and performance metrics.

    Returns:
    - Connection pool status and utilization
    - Query performance metrics (avg time, slow queries)
    - Cache hit rates
    - Replication lag

    Use this to diagnose database-related issues.
    """
    logger.info("Tool called: database_status")
    return check_database_status()


@mcp.tool()
def service_config_update(service_name: str, key: str, value: str) -> str:
    """
    Update a configuration value for a service.

    Args:
        service_name: Name of the service
        key: Configuration key to update
        value: New configuration value

    Note: Service restart typically required for changes to take effect.
    """
    logger.info(f"Tool called: service_config_update({service_name}, {key}=***)")
    return update_configuration(service_name, key, value)


@mcp.tool()
def service_diagnostics(service_name: str) -> str:
    """
    Run comprehensive diagnostics on a service.

    Args:
        service_name: Name of the service to diagnose

    Returns:
    - Health check results for all dependencies
    - Resource usage metrics
    - Recent errors
    - Recommendations for issues found

    Use this for deep troubleshooting of service issues.
    """
    logger.info(f"Tool called: service_diagnostics({service_name})")
    return run_diagnostics(service_name)


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


@app.get("/health")
async def http_health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mcp-server"}


@app.get("/tools/system_health")
async def api_system_health():
    """Check overall system health."""
    return {"result": check_system_health()}


@app.post("/tools/service_logs")
async def api_service_logs(request: ToolRequest):
    """Read service logs."""
    if not request.service_name:
        raise HTTPException(status_code=400, detail="service_name is required")
    return {"result": get_service_logs(request.service_name, request.lines or 50)}


@app.post("/tools/service_restart")
async def api_service_restart(request: ToolRequest):
    """Restart a service."""
    if not request.service_name:
        raise HTTPException(status_code=400, detail="service_name is required")
    return {"result": restart_service(request.service_name)}


@app.get("/tools/database_status")
async def api_database_status():
    """Check database status."""
    return {"result": check_database_status()}


@app.post("/tools/service_config_update")
async def api_service_config_update(request: ToolRequest):
    """Update service configuration."""
    if not all([request.service_name, request.key, request.value]):
        raise HTTPException(status_code=400, detail="service_name, key, and value are required")
    return {"result": update_configuration(request.service_name, request.key, request.value)}


@app.post("/tools/service_diagnostics")
async def api_service_diagnostics(request: ToolRequest):
    """Run service diagnostics."""
    if not request.service_name:
        raise HTTPException(status_code=400, detail="service_name is required")
    return {"result": run_diagnostics(request.service_name)}


if __name__ == "__main__":
    logger.info(f"Starting MCP Server on port {MCP_PORT}")
    logger.info("Available tools:")
    logger.info("  - system_health: Check overall system health")
    logger.info("  - service_logs: Read service logs")
    logger.info("  - service_restart: Restart a service")
    logger.info("  - database_status: Check database health")
    logger.info("  - service_config_update: Update service configuration")
    logger.info("  - service_diagnostics: Run comprehensive diagnostics")
    logger.info("=" * 60)

    # Run the HTTP API server
    uvicorn.run(app, host="0.0.0.0", port=MCP_PORT, access_log=False)
