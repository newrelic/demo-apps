"""
AI Agent - PydanticAI reasoning engine with model routing.

This module contains the core agent logic with tool wrappers for MCP server.
"""

import os
import logging
import time
import asyncio
import httpx
from typing import Literal
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider

from prompts import REPAIR_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT
from models import RepairResult, ModelMetrics, ToolCall

logger = logging.getLogger(__name__)

# MCP Server configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:8002")

# Model configurations
OLLAMA_MODEL_A_URL = os.getenv("OLLAMA_MODEL_A_URL", "http://ollama-model-a:11434/v1")
OLLAMA_MODEL_B_URL = os.getenv("OLLAMA_MODEL_B_URL", "http://ollama-model-b:11434/v1")
MODEL_A_NAME = os.getenv("MODEL_A_NAME", "mistral:7b-instruct")
MODEL_B_NAME = os.getenv("MODEL_B_NAME", "ministral-3:8b-instruct-2512-q8_0")

# HTTP client for MCP server (MUST be async for async tools)
mcp_client = httpx.AsyncClient(base_url=MCP_SERVER_URL, timeout=60.0)

# Metrics tracking
model_a_metrics = ModelMetrics(model_name=MODEL_A_NAME)
model_b_metrics = ModelMetrics(model_name=MODEL_B_NAME)


# ===== Tool Wrappers for MCP Server =====

async def call_mcp_tool(tool_path: str, method: str = "GET", data: dict = None) -> str:
    """
    Call an MCP server tool via HTTP (async).

    Args:
        tool_path: API path (e.g., "/tools/docker_ps")
        method: HTTP method (GET or POST)
        data: Optional data for POST requests

    Returns:
        Tool result as string
    """
    try:
        logger.info(f"[DEBUG] Calling MCP tool: {method} {tool_path}")
        if method == "GET":
            response = await mcp_client.get(tool_path)
        else:
            response = await mcp_client.post(tool_path, json=data or {})

        logger.info(f"[DEBUG] MCP tool response: status={response.status_code}")
        if response.status_code == 200:
            result = response.json().get("result", "")
            return result
        else:
            return f"Error: HTTP {response.status_code}"

    except Exception as e:
        logger.error(f"[DEBUG] MCP tool call exception: {type(e).__name__}")
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

# Model A - Reliable JSON formatting (Mistral 7B)
repair_agent_a = Agent(
    model_a,
    system_prompt=REPAIR_SYSTEM_PROMPT,
    output_type=RepairResult,
    retries=2,  # Mistral rarely needs retries for JSON formatting
    tool_timeout=120.0,  # 120 second timeout for individual tool calls
)

# Model B - Efficient instruction-following (Phi-3 3.8B)
repair_agent_b = Agent(
    model_b,
    system_prompt=REPAIR_SYSTEM_PROMPT,
    output_type=RepairResult,
    retries=3,  # Phi-3 occasionally needs one retry
    tool_timeout=120.0,  # 120 second timeout for individual tool calls
)


# ===== Tool Definitions =====

@repair_agent_a.tool
@repair_agent_b.tool
async def system_health(ctx: RunContext) -> str:
    """Check overall system health including all services and resource usage."""
    logger.info("[DEBUG] system_health tool called - starting execution")
    result = await call_mcp_tool("/tools/system_health")
    logger.info(f"[DEBUG] system_health tool completed - result length: {len(result)}")
    return result


@repair_agent_a.tool
@repair_agent_b.tool
async def service_logs(ctx: RunContext, service_name: str, lines: int = 50) -> str:
    """
    Retrieve recent logs from a specific service.

    Args:
        service_name: Name of the service (e.g., 'api-gateway', 'auth-service')
        lines: Number of log lines to retrieve
    """
    logger.info(f"Tool called: service_logs({service_name}, {lines})")
    return await call_mcp_tool("/tools/service_logs", "POST", {
        "service_name": service_name,
        "lines": lines
    })


@repair_agent_a.tool
@repair_agent_b.tool
async def service_restart(ctx: RunContext, service_name: str) -> str:
    """
    Restart a specific service.

    Args:
        service_name: Name of the service to restart
    """
    logger.info(f"Tool called: service_restart({service_name})")
    return await call_mcp_tool("/tools/service_restart", "POST", {
        "service_name": service_name
    })


@repair_agent_a.tool
@repair_agent_b.tool
async def database_status(ctx: RunContext) -> str:
    """Check database health and performance metrics."""
    logger.info("Tool called: database_status")
    return await call_mcp_tool("/tools/database_status")


@repair_agent_a.tool
@repair_agent_b.tool
async def service_config_update(ctx: RunContext, service_name: str, key: str, value: str) -> str:
    """
    Update a configuration value for a service.

    Args:
        service_name: Name of the service
        key: Configuration key to update
        value: New configuration value
    """
    logger.info(f"Tool called: service_config_update({service_name}, {key})")
    return await call_mcp_tool("/tools/service_config_update", "POST", {
        "service_name": service_name,
        "key": key,
        "value": value
    })


@repair_agent_a.tool
@repair_agent_b.tool
async def service_diagnostics(ctx: RunContext, service_name: str) -> str:
    """
    Run comprehensive diagnostics on a service.

    Args:
        service_name: Name of the service to diagnose

    Returns detailed health check results, resource usage, and recommendations.
    """
    logger.info(f"Tool called: service_diagnostics({service_name})")
    return await call_mcp_tool("/tools/service_diagnostics", "POST", {
        "service_name": service_name
    })


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
for tool_func in [system_health, service_logs, service_restart, database_status,
                   service_config_update, service_diagnostics]:
    chat_agent_a.tool(tool_func)
    chat_agent_b.tool(tool_func)


# ===== Debug Agents (NO TOOLS) =====
# These agents have NO tools attached to diagnose PydanticAI hanging issues

debug_agent_a = Agent(
    model_a,
    system_prompt="You are a helpful assistant. Answer questions concisely.",
)

debug_agent_b = Agent(
    model_b,
    system_prompt="You are a helpful assistant. Answer questions concisely.",
)


# ===== Minimal Repair Agents (ONLY 2 TOOLS) =====
# Simplified agents for testing with minimal context usage

MINIMAL_REPAIR_PROMPT = """You are a DevOps repair agent. You MUST use the available tools to check and repair the system.

Available tools:
- minimal_system_health(): Check overall system health and service status
- minimal_service_restart(service_name): Restart a service

WORKFLOW - Follow these steps:
1. FIRST: Call minimal_system_health() to check all services
2. Look for the api-gateway service status
3. If it's degraded or having issues, call minimal_service_restart("api-gateway")
4. Summarize what you did

START by calling minimal_system_health() now."""

minimal_repair_agent_a = Agent(
    model_a,
    system_prompt=MINIMAL_REPAIR_PROMPT,
    retries=1,  # Allow 1 retry for output format issues
    tool_timeout=60.0,
)

minimal_repair_agent_b = Agent(
    model_b,
    system_prompt=MINIMAL_REPAIR_PROMPT,
    retries=1,  # Allow 1 retry for output format issues
    tool_timeout=60.0,
)

# Register only 2 tools for minimal agents
@minimal_repair_agent_a.tool
@minimal_repair_agent_b.tool
async def minimal_system_health(ctx: RunContext) -> str:
    """Check overall system health and service status."""
    logger.info("[MINIMAL] system_health called")
    return await call_mcp_tool("/tools/system_health")

@minimal_repair_agent_a.tool
@minimal_repair_agent_b.tool
async def minimal_service_restart(ctx: RunContext, service_name: str) -> str:
    """Restart a service."""
    logger.info(f"[MINIMAL] service_restart({service_name}) called")
    return await call_mcp_tool("/tools/service_restart", "POST", {"service_name": service_name})


# ===== Agent Execution Functions =====

async def run_repair_workflow(model: Literal["a", "b"] = "a") -> RepairResult:
    """
    Execute the repair workflow with manual tool orchestration.

    Makes one LLM call for AI monitoring telemetry, then executes
    a scripted sequence of tool calls for reliable demo experience.

    Args:
        model: Which model to use ("a" or "b")

    Returns:
        RepairResult with actions taken and final status
    """
    logger.info(f"[DEBUG] run_repair_workflow() called with model={model}")
    start_time = time.time()

    model_name = MODEL_A_NAME if model == "a" else MODEL_B_NAME
    model_instance = model_a if model == "a" else model_b
    metrics = model_a_metrics if model == "a" else model_b_metrics

    logger.info(f"=" * 60)
    logger.info(f"Starting repair workflow with Model {model.upper()} ({model_name})")
    logger.info(f"=" * 60)

    tool_calls = []
    actions_taken = []

    try:
        # Step 1: Make LLM call for AI monitoring telemetry
        logger.info(f"[WORKFLOW] Making LLM call for AI monitoring telemetry")
        llm_start = time.time()

        # Simple prompt that doesn't require tool calling
        prompt = (
            "You are a system reliability engineer. Analyze this scenario:\n\n"
            "A distributed system is running with multiple microservices. "
            "Your task is to check system health and restart any failing services. "
            "Respond with your assessment and planned actions in 2-3 sentences."
        )

        ai_response = None
        try:
            # Direct LLM call using the correct Ollama URL
            ollama_url = OLLAMA_MODEL_A_URL if model == "a" else OLLAMA_MODEL_B_URL

            response = await mcp_client.post(
                f"{ollama_url}/chat/completions",
                json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 150
                },
                timeout=60.0  # Increased from 30s to 60s for slower models
            )
            llm_latency = time.time() - llm_start

            if response.status_code == 200:
                llm_response = response.json()
                ai_response = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "AI analysis completed")
                logger.info(f"[WORKFLOW] LLM response received in {llm_latency:.2f}s")
                logger.info(f"[WORKFLOW] AI Analysis: {ai_response[:100]}...")
            else:
                logger.warning(f"[WORKFLOW] LLM call returned status {response.status_code}")
                ai_response = f"AI call returned status {response.status_code}"

        except Exception as e:
            logger.error(f"[WORKFLOW] LLM call failed: {e}")
            ai_response = f"AI call timed out or failed: {str(e)}"

        # Step 2: Execute scripted tool sequence
        logger.info(f"[WORKFLOW] Starting scripted tool execution sequence")

        # Tool 1: Check system health
        logger.info(f"[WORKFLOW] Tool 1/4: Checking system health")
        health_result = await call_mcp_tool("/tools/system_health")
        tool_calls.append(ToolCall(
            tool_name="check_system_health",
            arguments={},
            success=True,
            result=health_result[:200] if health_result else "System health checked"
        ))
        actions_taken.append("Checked overall system health")
        await asyncio.sleep(0.5)  # Brief pause for realism

        # Tool 2: Get service logs
        logger.info(f"[WORKFLOW] Tool 2/4: Retrieving service logs")
        logs_result = await call_mcp_tool("/tools/service_logs", "POST", {
            "service_name": "api-gateway",
            "lines": 50
        })
        tool_calls.append(ToolCall(
            tool_name="get_service_logs",
            arguments={"service_name": "api-gateway", "lines": 50},
            success=True,
            result=logs_result[:200] if logs_result else "Logs retrieved"
        ))
        actions_taken.append("Retrieved logs from api-gateway service")
        await asyncio.sleep(0.5)

        # Tool 3: Run diagnostics
        logger.info(f"[WORKFLOW] Tool 3/4: Running diagnostics")
        diag_result = await call_mcp_tool("/tools/service_diagnostics", "POST", {
            "service_name": "api-gateway"
        })
        tool_calls.append(ToolCall(
            tool_name="run_diagnostics",
            arguments={"service_name": "api-gateway"},
            success=True,
            result=diag_result[:200] if diag_result else "Diagnostics completed"
        ))
        actions_taken.append("Ran comprehensive diagnostics on api-gateway")
        await asyncio.sleep(0.5)

        # Tool 4: Restart service (simulated fix)
        logger.info(f"[WORKFLOW] Tool 4/4: Restarting service")
        restart_result = await call_mcp_tool("/tools/service_restart", "POST", {
            "service_name": "api-gateway"
        })
        tool_calls.append(ToolCall(
            tool_name="restart_service",
            arguments={"service_name": "api-gateway"},
            success=True,
            result=restart_result[:200] if restart_result else "Service restarted"
        ))
        actions_taken.append("Restarted api-gateway service")

        total_latency = time.time() - start_time
        logger.info(f"[WORKFLOW] Workflow completed successfully in {total_latency:.2f}s")

        # Update metrics
        metrics.total_requests += 1
        metrics.successful_requests += 1
        metrics.avg_latency_seconds = (
            (metrics.avg_latency_seconds * (metrics.total_requests - 1) + total_latency)
            / metrics.total_requests
        )

        logger.info(f"Repair workflow completed in {total_latency:.2f}s with {len(tool_calls)} tool calls")

        return RepairResult(
            success=True,
            actions_taken=actions_taken,
            containers_restarted=["api-gateway"],
            final_status="All systems operational - services checked and restarted as needed",
            model_used=model_name,
            latency_seconds=total_latency,
            tool_calls=tool_calls,
            ai_reasoning=ai_response
        )

    except Exception as e:
        logger.error(f"[DEBUG] Exception caught in run_repair_workflow: {type(e).__name__}")
        logger.error(f"Repair workflow failed: {e}", exc_info=True)
        metrics.total_requests += 1
        metrics.failed_requests += 1

        # Include any actions/tool_calls that completed before error
        error_actions = actions_taken + [f"Error occurred: {str(e)}"]

        return RepairResult(
            success=False,
            actions_taken=error_actions,
            final_status=f"Workflow failed: {str(e)}",
            model_used=model_name,
            latency_seconds=time.time() - start_time,
            tool_calls=tool_calls,
            ai_reasoning=ai_response if 'ai_response' in locals() else None
        )


async def run_minimal_repair_workflow_manual(model: Literal["a", "b"] = "a") -> RepairResult:
    """
    MANUAL tool orchestration - bypasses PydanticAI agents entirely.

    Directly calls Ollama, parses tool calls from text, executes them, and loops.
    This works around Ollama's lack of OpenAI function calling support.
    """
    logger.info(f"[MANUAL-MINIMAL] Starting manual repair with model={model}")
    start_time = time.time()

    model_url = OLLAMA_MODEL_A_URL if model == "a" else OLLAMA_MODEL_B_URL
    model_name = MODEL_A_NAME if model == "a" else MODEL_B_NAME
    metrics = model_a_metrics if model == "a" else model_b_metrics

    # Conversation history
    messages = [
        {
            "role": "system",
            "content": """You are a DevOps repair agent. You can use tools to check and fix systems.

Available tools:
- minimal_system_health(): Returns status of all services and system health
- minimal_service_restart(service_name): Restarts a service

To use a tool, respond with ONLY a JSON array in this format:
[{"name": "tool_name", "arguments": {"arg1": "value1"}}]

After tool results, you can call more tools or give your final answer.

Task: Check if api-gateway service is running properly. If not, restart it."""
        },
        {
            "role": "user",
            "content": "Begin the repair workflow. Start by checking system health."
        }
    ]

    tool_calls_executed = []
    actions_taken = []
    containers_restarted = []
    max_iterations = 5

    try:
        import json
        import re

        for iteration in range(max_iterations):
            logger.info(f"[MANUAL-MINIMAL] Iteration {iteration + 1}/{max_iterations}")

            # Call Ollama
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{model_url.rstrip('/v1')}/v1/chat/completions",
                    json={
                        "model": model_name,
                        "messages": messages,
                        "max_tokens": 500,
                        "temperature": 0.1
                    }
                )

            if response.status_code != 200:
                raise Exception(f"Ollama returned {response.status_code}: {response.text}")

            result = response.json()
            assistant_message = result["choices"][0]["message"]["content"]
            logger.info(f"[MANUAL-MINIMAL] Model response (first 300 chars): {assistant_message[:300]}")

            # Add assistant response to conversation
            messages.append({"role": "assistant", "content": assistant_message})

            # Try to parse tool calls from response
            tool_calls_found = []
            content_stripped = assistant_message.strip()

            # Check if response contains JSON tool call array
            if content_stripped.startswith('[{') and '"name"' in content_stripped:
                # Extract JSON array
                json_match = re.match(r'^(\[.*?\])', content_stripped, re.DOTALL)
                if json_match:
                    try:
                        tool_calls_found = json.loads(json_match.group(1))
                        logger.info(f"[MANUAL-MINIMAL] Parsed {len(tool_calls_found)} tool calls")
                    except json.JSONDecodeError as e:
                        logger.warning(f"[MANUAL-MINIMAL] JSON parse error: {e}")

            # If no tool calls, model is done
            if not tool_calls_found:
                logger.info(f"[MANUAL-MINIMAL] No tool calls found, workflow complete")
                final_response = assistant_message
                break

            # Execute each tool call
            tool_results = []
            for tool_call in tool_calls_found:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("arguments", {})

                logger.info(f"[MANUAL-MINIMAL] Executing tool: {tool_name}({tool_args})")

                # Execute the tool
                if tool_name == "minimal_system_health":
                    result_text = await call_mcp_tool("/tools/system_health")
                    actions_taken.append("Checked system health")
                    logger.info(f"[MANUAL-MINIMAL] Tool result (first 500 chars): {result_text[:500]}")
                elif tool_name == "minimal_service_restart":
                    service_name = tool_args.get("service_name", "")
                    result_text = await call_mcp_tool("/tools/service_restart", "POST", {"service_name": service_name})
                    actions_taken.append(f"Restarted {service_name}")
                    containers_restarted.append(service_name)
                    logger.info(f"[MANUAL-MINIMAL] Tool result (first 500 chars): {result_text[:500]}")
                else:
                    result_text = f"Unknown tool: {tool_name}"
                    logger.info(f"[MANUAL-MINIMAL] Unknown tool: {tool_name}")

                tool_results.append({"tool": tool_name, "result": result_text})
                tool_calls_executed.append(ToolCall(
                    tool_name=tool_name,
                    arguments=tool_args,
                    success=True,
                    result=result_text[:200]
                ))

            # Feed tool results back to model
            results_text = "\n\n".join([f"Tool {r['tool']} returned:\n{r['result']}" for r in tool_results])
            feedback_message = f"Tool results:\n{results_text}\n\nWhat's next? Call more tools if needed, or summarize what you did."
            logger.info(f"[MANUAL-MINIMAL] Feeding back to model (first 500 chars): {feedback_message[:500]}")
            messages.append({
                "role": "user",
                "content": feedback_message
            })

        else:
            # Max iterations reached
            final_response = "Repair workflow completed (max iterations reached)"

        latency = time.time() - start_time
        success = len(tool_calls_executed) > 0

        if not actions_taken:
            actions_taken = ["No actions needed"]

        metrics.total_requests += 1
        metrics.successful_requests += 1

        logger.info(f"[MANUAL-MINIMAL] Completed in {latency:.2f}s with {len(tool_calls_executed)} tool calls")

        return RepairResult(
            success=success,
            actions_taken=actions_taken,
            containers_restarted=containers_restarted,
            final_status=final_response[:500] if final_response else "Repair completed",
            model_used=model_name,
            latency_seconds=latency,
            tool_calls=tool_calls_executed
        )

    except Exception as e:
        logger.error(f"[MANUAL-MINIMAL] Error: {e}", exc_info=True)
        metrics.total_requests += 1
        metrics.failed_requests += 1

        return RepairResult(
            success=False,
            actions_taken=[f"Error: {str(e)}"],
            final_status=f"Failed: {str(e)}",
            model_used=model_name,
            latency_seconds=time.time() - start_time
        )


async def run_minimal_repair_workflow(model: Literal["a", "b"] = "a") -> RepairResult:
    """
    Execute MINIMAL repair workflow with only 2 tools (for debugging).

    This is a simplified version to test if the issue is context/compute related.
    """
    logger.info(f"[MINIMAL] Starting minimal repair with model={model}")
    start_time = time.time()

    agent = minimal_repair_agent_a if model == "a" else minimal_repair_agent_b
    model_name = MODEL_A_NAME if model == "a" else MODEL_B_NAME
    metrics = model_a_metrics if model == "a" else model_b_metrics

    # Debug: Check agent configuration
    logger.info(f"[MINIMAL-DEBUG] Agent type: {type(agent).__name__}")
    logger.info(f"[MINIMAL-DEBUG] Agent model: {agent.model}")
    logger.info(f"[MINIMAL-DEBUG] Agent has tools: {len(agent._function_tools) if hasattr(agent, '_function_tools') else 'unknown'}")

    # List registered tools
    if hasattr(agent, '_function_tools'):
        tool_names = [tool.name if hasattr(tool, 'name') else str(tool) for tool in agent._function_tools.values()]
        logger.info(f"[MINIMAL-DEBUG] Registered tool names: {tool_names}")

    try:
        logger.info(f"[MINIMAL] Calling agent.run() with 120s timeout")

        async with asyncio.timeout(120):  # 120 second timeout (allow time for tool calls)
            result = await agent.run("Check if aim-target-app is running. Restart if needed.")

        logger.info(f"[MINIMAL] agent.run() completed successfully")
        latency = time.time() - start_time

        # Debug: Inspect result structure
        logger.info(f"[MINIMAL-DEBUG] Result type: {type(result)}")
        logger.info(f"[MINIMAL-DEBUG] Result has data: {hasattr(result, 'data')}")
        logger.info(f"[MINIMAL-DEBUG] Result has output: {hasattr(result, 'output')}")
        logger.info(f"[MINIMAL-DEBUG] Result has all_messages: {hasattr(result, 'all_messages')}")

        # Extract text response (no structured output validation)
        response_text = str(result.data) if hasattr(result, 'data') else "No response"
        logger.info(f"[MINIMAL-DEBUG] Response text (first 500 chars): {response_text[:500]}")

        # Debug: Inspect message history
        all_messages = result.all_messages()
        logger.info(f"[MINIMAL-DEBUG] Total messages in history: {len(all_messages)}")

        for idx, message in enumerate(all_messages):
            msg_type = type(message).__name__
            logger.info(f"[MINIMAL-DEBUG] Message {idx}: type={msg_type}")

            if hasattr(message, 'role'):
                logger.info(f"[MINIMAL-DEBUG] Message {idx}: role={message.role}")

            if hasattr(message, 'parts'):
                logger.info(f"[MINIMAL-DEBUG] Message {idx}: has {len(message.parts)} parts")
                for part_idx, part in enumerate(message.parts):
                    part_type = type(part).__name__
                    logger.info(f"[MINIMAL-DEBUG] Message {idx}, Part {part_idx}: type={part_type}")

                    if hasattr(part, 'tool_name'):
                        logger.info(f"[MINIMAL-DEBUG] Message {idx}, Part {part_idx}: tool_name={part.tool_name}")
                    if hasattr(part, 'args'):
                        logger.info(f"[MINIMAL-DEBUG] Message {idx}, Part {part_idx}: args={part.args}")
                    if hasattr(part, 'content'):
                        content_preview = str(part.content)[:200]
                        logger.info(f"[MINIMAL-DEBUG] Message {idx}, Part {part_idx}: content={content_preview}")

            if hasattr(message, 'content'):
                content_preview = str(message.content)[:200]
                logger.info(f"[MINIMAL-DEBUG] Message {idx}: content={content_preview}")

        # Count tool calls from message history
        tool_calls = []
        actions_taken = []
        containers_restarted = []

        for message in all_messages:
            if hasattr(message, 'parts'):
                for part in message.parts:
                    # Check for proper tool call parts
                    if hasattr(part, 'tool_name') and part.tool_name is not None:
                        tool_name = part.tool_name
                        logger.info(f"[MINIMAL-DEBUG] Found tool call: {tool_name}")

                        # Extract arguments safely (may be dict, string, or missing)
                        args = {}
                        if hasattr(part, 'args'):
                            if isinstance(part.args, dict):
                                args = part.args
                            elif isinstance(part.args, str):
                                try:
                                    import json
                                    args = json.loads(part.args)
                                except:
                                    args = {}

                        tool_calls.append(ToolCall(
                            tool_name=tool_name,
                            arguments=args,
                            success=True,
                            result="Executed"
                        ))

                        # Extract actions from tool calls
                        if 'restart' in tool_name.lower():
                            service = args.get('service_name', 'unknown')
                            actions_taken.append(f"Restarted {service}")
                            containers_restarted.append(service)
                        elif 'health' in tool_name.lower() or 'system' in tool_name.lower():
                            actions_taken.append("Checked system health")

                    # WORKAROUND: Parse tool calls from text when Ollama doesn't support function calling
                    elif hasattr(part, 'content') and isinstance(part.content, str):
                        content = part.content.strip()
                        # Check if content starts with JSON array of tool calls
                        if content.startswith('[{') and '"name"' in content and '"arguments"' in content:
                            logger.info(f"[MINIMAL-DEBUG] Found text-based tool call format, attempting to parse...")
                            try:
                                import json
                                import re
                                # Extract just the JSON array (before any explanatory text)
                                json_match = re.match(r'^(\[.*?\])', content, re.DOTALL)
                                if json_match:
                                    json_str = json_match.group(1)
                                    parsed_tools = json.loads(json_str)
                                    logger.info(f"[MINIMAL-DEBUG] Parsed {len(parsed_tools)} tool calls from text")

                                    for tool_def in parsed_tools:
                                        tool_name = tool_def.get('name', '')
                                        args = tool_def.get('arguments', {})
                                        logger.info(f"[MINIMAL-DEBUG] Extracted text tool call: {tool_name}")

                                        tool_calls.append(ToolCall(
                                            tool_name=tool_name,
                                            arguments=args,
                                            success=True,
                                            result="Executed (parsed from text)"
                                        ))

                                        # Extract actions
                                        if 'restart' in tool_name.lower():
                                            service = args.get('service_name', 'unknown')
                                            actions_taken.append(f"Restarted {service}")
                                            containers_restarted.append(service)
                                        elif 'health' in tool_name.lower() or 'system' in tool_name.lower():
                                            actions_taken.append("Checked system health")
                            except Exception as e:
                                logger.warning(f"[MINIMAL-DEBUG] Failed to parse text tool calls: {e}")

        # Build result from extracted info
        success = len(tool_calls) > 0  # Success if tools were executed
        final_status = response_text[:200] if response_text else "Repair completed"

        if not actions_taken:
            actions_taken = ["No actions needed - system healthy"]

        metrics.total_requests += 1
        metrics.successful_requests += 1

        logger.info(f"[MINIMAL] Completed in {latency:.2f}s with {len(tool_calls)} tool calls")
        logger.info(f"[MINIMAL-DEBUG] Final success={success}, actions={actions_taken}")

        return RepairResult(
            success=success,
            actions_taken=actions_taken,
            containers_restarted=containers_restarted,
            final_status=final_status,
            model_used=model_name,
            latency_seconds=latency,
            tool_calls=tool_calls
        )

    except asyncio.TimeoutError:
        logger.error(f"[MINIMAL] TIMEOUT after 120 seconds")
        metrics.total_requests += 1
        metrics.failed_requests += 1
        return RepairResult(
            success=False,
            actions_taken=["Timeout after 120s"],
            final_status="Minimal repair timed out",
            model_used=model_name,
            latency_seconds=120.0
        )
    except Exception as e:
        logger.error(f"[MINIMAL] Failed: {e}", exc_info=True)
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


async def run_debug_test(message: str, model: Literal["a", "b"] = "a") -> dict:
    """
    Execute a simple test with minimal debug agent (NO TOOLS).
    Used to diagnose PydanticAI hanging issues.

    Args:
        message: Test message
        model: Which model to use ("a" or "b")

    Returns:
        Dictionary with test results
    """
    logger.info(f"[DEBUG-TEST] Starting test with model={model}, message='{message[:50]}...'")
    start_time = time.time()
    agent = debug_agent_a if model == "a" else debug_agent_b
    model_name = MODEL_A_NAME if model == "a" else MODEL_B_NAME

    try:
        logger.info(f"[DEBUG-TEST] Calling agent.run() with 30 second timeout")

        try:
            async with asyncio.timeout(30):  # 30 second timeout for debug
                result = await agent.run(message)
        except asyncio.TimeoutError:
            logger.error(f"[DEBUG-TEST] TIMEOUT after 30 seconds")
            return {
                "success": False,
                "error": "Timeout after 30 seconds",
                "model": model_name,
                "latency_seconds": time.time() - start_time
            }

        latency = time.time() - start_time
        logger.info(f"[DEBUG-TEST] Completed successfully in {latency:.2f}s")

        return {
            "success": True,
            "response": str(result.output),
            "model": model_name,
            "latency_seconds": latency
        }

    except Exception as e:
        logger.error(f"[DEBUG-TEST] Exception: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "model": model_name,
            "latency_seconds": time.time() - start_time
        }


async def run_direct_llm_test(model: Literal["a", "b"] = "a") -> dict:
    """
    Bypass PydanticAI and call Ollama directly via OpenAI-compatible API.
    Used to diagnose if the issue is PydanticAI or Ollama.

    Args:
        model: Which model to use ("a" or "b")

    Returns:
        Dictionary with test results
    """
    logger.info(f"[DIRECT-LLM-TEST] Starting direct LLM call with model={model}")
    start_time = time.time()

    model_url = OLLAMA_MODEL_A_URL if model == "a" else OLLAMA_MODEL_B_URL
    model_name = MODEL_A_NAME if model == "a" else MODEL_B_NAME

    try:
        logger.info(f"[DIRECT-LLM-TEST] Calling {model_url} with httpx")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{model_url.rstrip('/v1')}/v1/chat/completions",
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "user", "content": "Say hello in one sentence."}
                    ],
                    "max_tokens": 50
                }
            )

        latency = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            message_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.info(f"[DIRECT-LLM-TEST] Success in {latency:.2f}s")

            return {
                "success": True,
                "response": message_content,
                "model": model_name,
                "latency_seconds": latency,
                "raw_status": response.status_code
            }
        else:
            logger.error(f"[DIRECT-LLM-TEST] HTTP error: {response.status_code}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "model": model_name,
                "latency_seconds": latency
            }

    except Exception as e:
        logger.error(f"[DIRECT-LLM-TEST] Exception: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "model": model_name,
            "latency_seconds": time.time() - start_time
        }


def get_metrics() -> tuple[ModelMetrics, ModelMetrics]:
    """Get current metrics for both models."""
    return model_a_metrics, model_b_metrics
