"""
AI Agent - PydanticAI reasoning engine with model routing.

This module contains the core agent logic with tool wrappers for MCP server.
"""

import os
import logging
import time
import httpx
from typing import Literal
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider

from prompts import REPAIR_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT
from models import RepairResult, ModelMetrics

logger = logging.getLogger(__name__)

# MCP Server configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:8002")

# Model configurations
OLLAMA_MODEL_A_URL = os.getenv("OLLAMA_MODEL_A_URL", "http://ollama-model-a:11434/v1")
OLLAMA_MODEL_B_URL = os.getenv("OLLAMA_MODEL_B_URL", "http://ollama-model-b:11434/v1")
MODEL_A_NAME = os.getenv("MODEL_A_NAME", "llama3.2:1b")
MODEL_B_NAME = os.getenv("MODEL_B_NAME", "qwen2.5:0.5b")

# HTTP client for MCP server
mcp_client = httpx.Client(base_url=MCP_SERVER_URL, timeout=60.0)

# Metrics tracking
model_a_metrics = ModelMetrics(model_name=MODEL_A_NAME)
model_b_metrics = ModelMetrics(model_name=MODEL_B_NAME)


# ===== Tool Wrappers for MCP Server =====

def call_mcp_tool(tool_path: str, method: str = "GET", data: dict = None) -> str:
    """
    Call an MCP server tool via HTTP.

    Args:
        tool_path: API path (e.g., "/tools/docker_ps")
        method: HTTP method (GET or POST)
        data: Optional data for POST requests

    Returns:
        Tool result as string
    """
    try:
        if method == "GET":
            response = mcp_client.get(tool_path)
        else:
            response = mcp_client.post(tool_path, json=data or {})

        if response.status_code == 200:
            result = response.json().get("result", "")
            return result
        else:
            return f"Error: HTTP {response.status_code}"

    except Exception as e:
        logger.error(f"MCP tool call failed: {e}")
        return f"Error calling tool: {str(e)}"


# ===== Model Instantiation =====

# We explicitly create OllamaModel instances to avoid "Unknown model" inference errors.
# Note: PydanticAI's OllamaModel expects the /v1 suffix for the OpenAI-compatible endpoint.
model_a = OpenAIChatModel(
    model_name=MODEL_A_NAME,
    provider=OllamaProvider(base_url=OLLAMA_MODEL_A_URL)
)

model_b = OpenAIChatModel(
    model_name=MODEL_B_NAME,
    provider=OllamaProvider(base_url=OLLAMA_MODEL_B_URL)
)


# ===== Repair Agent =====

# Model A - Fast baseline
repair_agent_a = Agent(
    model_a,
    system_prompt=REPAIR_SYSTEM_PROMPT,
    output_type=RepairResult,
    retries=3,  # Allow 3 retries for output validation with small models
    tool_timeout=120.0,  # 120 second timeout for individual tool calls
)

# Model B - Premium comparison
repair_agent_b = Agent(
    model_b,
    system_prompt=REPAIR_SYSTEM_PROMPT,
    output_type=RepairResult,
    retries=3,  # Allow 3 retries for output validation with small models
    tool_timeout=120.0,  # 120 second timeout for individual tool calls
)


# ===== Tool Definitions =====

@repair_agent_a.tool
@repair_agent_b.tool
async def docker_ps(ctx: RunContext) -> str:
    """List all Docker containers with their status."""
    logger.info("Tool called: docker_ps")
    return call_mcp_tool("/tools/docker_ps")


@repair_agent_a.tool
@repair_agent_b.tool
async def docker_logs(ctx: RunContext, service_name: str, lines: int = 50) -> str:
    """
    Read recent logs from a container.

    Args:
        service_name: Name of the container
        lines: Number of log lines to retrieve
    """
    logger.info(f"Tool called: docker_logs({service_name}, {lines})")
    return call_mcp_tool("/tools/docker_logs", "POST", {
        "service_name": service_name,
        "lines": lines
    })


@repair_agent_a.tool
@repair_agent_b.tool
async def docker_restart(ctx: RunContext, service_name: str) -> str:
    """
    Restart a container.

    Args:
        service_name: Name of the container to restart
    """
    logger.info(f"Tool called: docker_restart({service_name})")
    return call_mcp_tool("/tools/docker_restart", "POST", {
        "service_name": service_name
    })


@repair_agent_a.tool
@repair_agent_b.tool
async def docker_inspect(ctx: RunContext, service_name: str) -> str:
    """
    Get detailed container information including environment variables.

    Args:
        service_name: Name of the container to inspect
    """
    logger.info(f"Tool called: docker_inspect({service_name})")
    return call_mcp_tool("/tools/docker_inspect", "POST", {
        "service_name": service_name
    })


@repair_agent_a.tool
@repair_agent_b.tool
async def docker_update_env(ctx: RunContext, service_name: str, key: str, value: str) -> str:
    """
    Update an environment variable for a container.

    Args:
        service_name: Name of the container
        key: Environment variable name
        value: New value
    """
    logger.info(f"Tool called: docker_update_env({service_name}, {key})")
    return call_mcp_tool("/tools/docker_update_env", "POST", {
        "service_name": service_name,
        "key": key,
        "value": value
    })


@repair_agent_a.tool
@repair_agent_b.tool
async def locust_start_test(ctx: RunContext, users: int = 10, spawn_rate: int = 2, duration: int = 60) -> str:
    """
    Start a load test.

    Args:
        users: Number of concurrent users
        spawn_rate: Users to spawn per second
        duration: Test duration in seconds
    """
    logger.info(f"Tool called: locust_start_test({users}, {spawn_rate}, {duration})")
    return call_mcp_tool("/tools/locust_start_test", "POST", {
        "users": users,
        "spawn_rate": spawn_rate,
        "duration": duration
    })


@repair_agent_a.tool
@repair_agent_b.tool
async def locust_get_stats(ctx: RunContext) -> str:
    """Get current load test statistics."""
    logger.info("Tool called: locust_get_stats")
    return call_mcp_tool("/tools/locust_get_stats")


@repair_agent_a.tool
@repair_agent_b.tool
async def locust_stop_test(ctx: RunContext) -> str:
    """Stop the running load test."""
    logger.info("Tool called: locust_stop_test")
    return call_mcp_tool("/tools/locust_stop_test")


# ===== Chat Agents =====

chat_agent_a = Agent(
    model_a,
    system_prompt=CHAT_SYSTEM_PROMPT,
)

chat_agent_b = Agent(
    model_b,
    system_prompt=CHAT_SYSTEM_PROMPT,
)

# Add same tools to chat agents
for tool_func in [docker_ps, docker_logs, docker_restart, docker_inspect,
                   docker_update_env, locust_start_test, locust_get_stats, locust_stop_test]:
    chat_agent_a.tool(tool_func)
    chat_agent_b.tool(tool_func)


# ===== Agent Execution Functions =====

async def run_repair_workflow(model: Literal["a", "b"] = "a") -> RepairResult:
    """
    Execute the repair workflow with the specified model.

    Args:
        model: Which model to use ("a" or "b")

    Returns:
        RepairResult with actions taken and final status
    """
    start_time = time.time()
    agent = repair_agent_a if model == "a" else repair_agent_b
    model_name = MODEL_A_NAME if model == "a" else MODEL_B_NAME
    metrics = model_a_metrics if model == "a" else model_b_metrics

    logger.info(f"=" * 60)
    logger.info(f"Starting repair workflow with Model {model.upper()} ({model_name})")
    logger.info(f"=" * 60)

    try:
        result = await agent.run(
            "Check the system for failures and repair them. "
            "Follow the repair workflow systematically."
        )

        latency = time.time() - start_time
        result.output.model_used = model_name
        result.output.latency_seconds = latency

        # Update metrics
        metrics.total_requests += 1
        metrics.successful_requests += 1
        metrics.avg_latency_seconds = (
            (metrics.avg_latency_seconds * (metrics.total_requests - 1) + latency)
            / metrics.total_requests
        )

        logger.info(f"Repair workflow completed in {latency:.2f}s")
        return result.output

    except Exception as e:
        logger.error(f"Repair workflow failed: {e}", exc_info=True)
        metrics.total_requests += 1
        metrics.failed_requests += 1

        return RepairResult(
            success=False,
            actions_taken=[f"Error: {str(e)}"],
            final_status=f"Failed: {str(e)}",
            model_used=model_name,
            latency_seconds=time.time() - start_time
        )


async def run_chat(message: str, model: Literal["a", "b"] = "a") -> tuple[str, float]:
    """
    Execute a chat interaction with the specified model.

    Args:
        message: User message
        model: Which model to use ("a" or "b")

    Returns:
        Tuple of (response_text, latency)
    """
    start_time = time.time()
    agent = chat_agent_a if model == "a" else chat_agent_b
    model_name = MODEL_A_NAME if model == "a" else MODEL_B_NAME
    metrics = model_a_metrics if model == "a" else model_b_metrics

    logger.info(f"Chat request to Model {model.upper()}: {message[:50]}...")

    try:
        result = await agent.run(message)
        latency = time.time() - start_time

        # Update metrics
        metrics.total_requests += 1
        metrics.successful_requests += 1
        metrics.avg_latency_seconds = (
            (metrics.avg_latency_seconds * (metrics.total_requests - 1) + latency)
            / metrics.total_requests
        )

        logger.info(f"Chat completed in {latency:.2f}s")
        return result.output, latency

    except Exception as e:
        logger.error(f"Chat failed: {e}", exc_info=True)
        metrics.total_requests += 1
        metrics.failed_requests += 1

        return f"Error: {str(e)}", time.time() - start_time


def get_metrics() -> tuple[ModelMetrics, ModelMetrics]:
    """Get current metrics for both models."""
    return model_a_metrics, model_b_metrics
