"""
LangChain tool wrappers for MCP Server.

Provides StructuredTool interfaces for all MCP server operations,
enabling type-safe tool calling with schema validation.
"""

import os
import logging
import httpx
from typing import List
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool
import newrelic.agent

from cache import system_health_cache, database_status_cache

logger = logging.getLogger(__name__)

# MCP Server configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:8002")

# HTTP client for MCP server (async)
_mcp_client = None


def get_mcp_client() -> httpx.AsyncClient:
    """Get or create MCP HTTP client."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = httpx.AsyncClient(base_url=MCP_SERVER_URL, timeout=60.0)
    return _mcp_client


async def call_mcp_tool(tool_path: str, method: str = "GET", data: dict = None) -> str:
    """
    Call an MCP server tool via HTTP (async).

    Args:
        tool_path: API path (e.g., "/tools/system_health")
        method: HTTP method (GET or POST)
        data: Optional data for POST requests

    Returns:
        Tool result as string
    """
    try:
        logger.info(f"[MCP-TOOL] Calling: {method} {tool_path}")
        client = get_mcp_client()

        if method == "GET":
            response = await client.get(tool_path)
        else:
            response = await client.post(tool_path, json=data or {})

        logger.info(f"[MCP-TOOL] Response: status={response.status_code}")

        if response.status_code == 200:
            result = response.json().get("result", "")
            logger.debug(f"[MCP-TOOL] Result length: {len(result)}")
            return result
        else:
            error_msg = f"HTTP {response.status_code}"
            logger.error(f"[MCP-TOOL] Error: {error_msg}")
            return f"Error: {error_msg}"

    except Exception as e:
        logger.error(f"[MCP-TOOL] Exception: {type(e).__name__}: {e}")
        return f"Error calling tool: {str(e)}"


# ===== Tool Input Schemas =====


class ServiceLogsInput(BaseModel):
    """Input schema for service_logs tool."""
    service_name: str = Field(description="Name of the service (e.g., 'api-gateway', 'auth-service')")
    lines: int = Field(default=50, description="Number of log lines to retrieve", ge=1, le=1000)


class ServiceRestartInput(BaseModel):
    """Input schema for service_restart tool."""
    service_name: str = Field(description="Name of the service to restart")


class ServiceConfigUpdateInput(BaseModel):
    """Input schema for service_config_update tool."""
    service_name: str = Field(description="Name of the service")
    key: str = Field(description="Configuration key to update")
    value: str = Field(description="New configuration value")


class ServiceDiagnosticsInput(BaseModel):
    """Input schema for service_diagnostics tool."""
    service_name: str = Field(description="Name of the service to diagnose")


# ===== Tool Functions =====


async def system_health_func() -> str:
    """
    Check overall system health including all services and resource usage.

    Returns comprehensive system status including:
    - Service health status
    - CPU, memory, disk usage metrics
    - Network throughput
    """
    # Check cache first
    cache_key = "system_health"
    cached = system_health_cache.get(cache_key)

    # Record cache hit/miss to New Relic
    txn = newrelic.agent.current_transaction()
    if txn:
        txn.add_custom_attribute('tool.system_health.cache_hit', cached is not None)

    if cached:
        logger.info("[MCP-TOOL] Cache hit: system_health")
        return cached

    # Cache miss - make real call
    logger.info("[MCP-TOOL] Cache miss: system_health")
    result = await call_mcp_tool("/tools/system_health")
    system_health_cache.set(cache_key, result)
    return result


async def service_logs_func(service_name: str, lines: int = 50) -> str:
    """
    Retrieve recent logs from a specific service.

    Use this to diagnose issues or understand service behavior by examining
    recent log entries.

    Args:
        service_name: Name of the service (e.g., 'api-gateway', 'auth-service')
        lines: Number of log lines to retrieve (default: 50, max: 1000)

    Returns:
        Recent log entries from the specified service
    """
    return await call_mcp_tool(
        "/tools/service_logs",
        "POST",
        {"service_name": service_name, "lines": lines}
    )


async def service_restart_func(service_name: str) -> str:
    """
    Restart a specific service.

    Use this to recover from failures or apply configuration changes.
    The service will be gracefully restarted.

    Args:
        service_name: Name of the service to restart

    Returns:
        Status of the restart operation including restart time
    """
    return await call_mcp_tool(
        "/tools/service_restart",
        "POST",
        {"service_name": service_name}
    )


async def database_status_func() -> str:
    """
    Check database health and performance metrics.

    Returns comprehensive database status including:
    - Connection pool status and utilization
    - Query performance metrics (avg time, slow queries)
    - Cache hit rates
    - Replication lag

    Use this to diagnose database-related issues.
    """
    # Check cache first
    cache_key = "database_status"
    cached = database_status_cache.get(cache_key)

    # Record cache hit/miss to New Relic
    txn = newrelic.agent.current_transaction()
    if txn:
        txn.add_custom_attribute('tool.database_status.cache_hit', cached is not None)

    if cached:
        logger.info("[MCP-TOOL] Cache hit: database_status")
        return cached

    # Cache miss - make real call
    logger.info("[MCP-TOOL] Cache miss: database_status")
    result = await call_mcp_tool("/tools/database_status")
    database_status_cache.set(cache_key, result)
    return result


async def service_config_update_func(service_name: str, key: str, value: str) -> str:
    """
    Update a configuration value for a service.

    Note: Service restart is typically required for changes to take effect.

    Args:
        service_name: Name of the service
        key: Configuration key to update
        value: New configuration value

    Returns:
        Status of the configuration update
    """
    return await call_mcp_tool(
        "/tools/service_config_update",
        "POST",
        {"service_name": service_name, "key": key, "value": value}
    )


async def service_diagnostics_func(service_name: str) -> str:
    """
    Run comprehensive diagnostics on a service.

    Returns detailed health check results including:
    - Health check results for all dependencies
    - Resource usage metrics (CPU, memory, disk, network)
    - Recent errors
    - Recommendations for issues found

    Use this for deep troubleshooting of service issues.

    Args:
        service_name: Name of the service to diagnose

    Returns:
        Comprehensive diagnostic report for the service
    """
    return await call_mcp_tool(
        "/tools/service_diagnostics",
        "POST",
        {"service_name": service_name}
    )


# ===== Tool Creation =====


def create_mcp_tools() -> List[StructuredTool]:
    """
    Create LangChain StructuredTool objects for all MCP server tools.

    Returns:
        List of StructuredTool instances ready for use with LangChain agents
    """
    tools = [
        StructuredTool.from_function(
            func=system_health_func,
            name="system_health",
            description="Check system health: service status, CPU/memory/disk usage, network throughput.",
            coroutine=system_health_func,
        ),
        StructuredTool.from_function(
            func=database_status_func,
            name="database_status",
            description="Check database health: connection pool, query performance, cache hit rates, replication lag.",
            coroutine=database_status_func,
        ),
        StructuredTool.from_function(
            func=service_restart_func,
            name="service_restart",
            description="Restart a service to recover from failures. Args: service_name (str).",
            args_schema=ServiceRestartInput,
            coroutine=service_restart_func,
        ),
        # DISABLED FOR PERFORMANCE - Not needed for core demo workflows
        # StructuredTool.from_function(
        #     func=service_logs_func,
        #     name="service_logs",
        #     description="Retrieve recent logs from a service. Args: service_name (str), lines (int, default 50).",
        #     args_schema=ServiceLogsInput,
        #     coroutine=service_logs_func,
        # ),
        # StructuredTool.from_function(
        #     func=service_config_update_func,
        #     name="service_config_update",
        #     description="Update service configuration. Args: service_name (str), key (str), value (str).",
        #     args_schema=ServiceConfigUpdateInput,
        #     coroutine=service_config_update_func,
        # ),
        # StructuredTool.from_function(
        #     func=service_diagnostics_func,
        #     name="service_diagnostics",
        #     description="Run comprehensive diagnostics on a service. Args: service_name (str).",
        #     args_schema=ServiceDiagnosticsInput,
        #     coroutine=service_diagnostics_func,
        # ),
    ]

    logger.info(f"[MCP-TOOLS] Created {len(tools)} tools")
    for tool in tools:
        logger.debug(f"[MCP-TOOLS] - {tool.name}: {tool.description[:80]}...")

    return tools


async def cleanup_mcp_client():
    """Close MCP HTTP client."""
    global _mcp_client
    if _mcp_client is not None:
        await _mcp_client.aclose()
        _mcp_client = None
        logger.info("[MCP-TOOLS] Client closed")
