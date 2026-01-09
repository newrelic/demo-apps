"""
AI Agent FastAPI Service - HTTP API for the autonomous repair agent.

Exposes endpoints for repair workflows, chat interactions, and model comparison.
"""

import os
import logging
import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import newrelic.agent

from httpx_instrumentation import apply_httpx_patch
from agent import (
    run_repair_workflow,
    run_minimal_repair_workflow,
    run_minimal_repair_workflow_manual,
    run_chat,
    run_debug_test,
    run_direct_llm_test,
    get_metrics,
    model_a_metrics,
    model_b_metrics
)
from models import (
    RepairResult,
    ChatRequest,
    ChatResponse,
    AgentStatus,
    ComparisonResult
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress uvicorn access logs (noisy from polling/health checks)
logging.getLogger('uvicorn.access').setLevel(logging.WARNING)

# Track service start time
start_time = time.time()

# Token counting cache for New Relic callback
_token_cache = {}


def ollama_token_count_callback(model: str, content: str) -> int:
    """
    New Relic callback to provide token counts for LLM calls.

    Since Ollama provides token counts in responses (unlike some APIs),
    we use a cache mechanism: store tokens when we get the response,
    then return them when NR calls this callback.

    Args:
        model: LLM model name (e.g., "mistral:7b-instruct")
        content: Message content/prompt

    Returns:
        Token count or None if not available
    """
    # Create cache key from model + content hash
    cache_key = f"{model}:{hash(content)}"
    token_count = _token_cache.get(cache_key)

    if token_count is not None:
        logger.debug(f"[TOKEN CALLBACK] Returning {token_count} tokens for {model}")
        return token_count

    # Fallback: rough estimate based on character count
    # OpenAI rule of thumb: ~4 chars per token
    estimated = len(content) // 4
    logger.debug(f"[TOKEN CALLBACK] Estimating {estimated} tokens for {model} (no cached data)")
    return estimated


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("=" * 60)
    logger.info("🤖 AI Agent Service Starting")
    logger.info("=" * 60)
    logger.info(f"Model A: {os.getenv('MODEL_A_NAME')} at {os.getenv('OLLAMA_MODEL_A_URL')}")
    logger.info(f"Model B: {os.getenv('MODEL_B_NAME')} at {os.getenv('OLLAMA_MODEL_B_URL')}")
    logger.info(f"MCP Server: {os.getenv('MCP_SERVER_URL')}")
    logger.info("=" * 60)

    # Register New Relic token counting callback
    try:
        application = newrelic.agent.register_application(timeout=10.0)
        newrelic.agent.set_llm_token_count_callback(ollama_token_count_callback, application)
        logger.info("✅ New Relic token count callback registered")
    except Exception as e:
        logger.warning(f"⚠️  Failed to register NR token callback: {e}")

    # Apply httpx monkey-patch to capture PydanticAI tokens
    try:
        apply_httpx_patch()
    except Exception as e:
        logger.warning(f"⚠️  Failed to apply httpx patch: {e}")

    yield
    logger.info("AI Agent Service shutting down...")


# Create FastAPI application
app = FastAPI(
    title="AI Agent Service",
    description="Autonomous AI agent for system monitoring and repair with A/B model comparison",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Health Check =====

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ai-agent",
        "uptime_seconds": time.time() - start_time
    }


# ===== Repair Workflow Endpoints =====

@app.post("/repair", response_model=RepairResult)
async def trigger_repair(model: Literal["a", "b"] = "a"):
    """
    Trigger an autonomous repair workflow.

    Args:
        model: Which model to use ("a" or "b")

    Returns:
        RepairResult with actions taken and outcome
    """
    start_time = time.time()
    logger.info(f"[REPAIR-ENDPOINT] Request received - model={model}, timestamp={start_time}")

    try:
        if model == "a":
            logger.info(f"[REPAIR-ENDPOINT] Executing repair with Model A")
        elif model == "b":
            logger.info(f"[REPAIR-ENDPOINT] Executing repair with Model B")

        logger.info(f"[REPAIR-ENDPOINT] About to call run_repair_workflow(model={model})")
        result = await run_repair_workflow(model)
        logger.info(f"[REPAIR-ENDPOINT] run_repair_workflow returned")

        elapsed = time.time() - start_time
        actions_count = len(result.get("actions_taken", [])) if isinstance(result, dict) else len(result.actions_taken)
        logger.info(f"[REPAIR-ENDPOINT] Repair completed successfully - model={model}, elapsed={elapsed:.2f}s, actions={actions_count}")

        return result

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[REPAIR-ENDPOINT] Repair failed - model={model}, elapsed={elapsed:.2f}s, error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Repair workflow failed: {str(e)}")


@app.post("/repair/minimal", response_model=RepairResult)
async def trigger_minimal_repair(model: Literal["a", "b"] = "a"):
    """
    Trigger a MINIMAL repair workflow (only 2 tools for debugging).

    This is a simplified version with reduced context to test if the issue is compute-related.

    Args:
        model: Which model to use ("a" or "b")

    Returns:
        RepairResult with actions taken and outcome
    """
    logger.info(f"[MINIMAL-REPAIR] Request received - model={model}")

    try:
        result = await run_minimal_repair_workflow(model)
        logger.info(f"[MINIMAL-REPAIR] Completed - success={result.success}")
        return result

    except Exception as e:
        logger.error(f"[MINIMAL-REPAIR] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Minimal repair failed: {str(e)}")


@app.post("/repair/manual", response_model=RepairResult)
async def trigger_manual_repair(model: Literal["a", "b"] = "a"):
    """
    Trigger a MANUAL repair workflow (bypasses PydanticAI).

    This directly calls Ollama, parses tool calls from text, executes them,
    and feeds results back. Works around Ollama's lack of function calling support.

    Args:
        model: Which model to use ("a" or "b")

    Returns:
        RepairResult with actions taken and outcome
    """
    logger.info(f"[MANUAL-REPAIR] Request received - model={model}")

    try:
        result = await run_minimal_repair_workflow_manual(model)
        logger.info(f"[MANUAL-REPAIR] Completed - success={result.success}")
        return result

    except Exception as e:
        logger.error(f"[MANUAL-REPAIR] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Manual repair failed: {str(e)}")



# ===== Chat Endpoints =====

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the AI agent.

    Args:
        request: ChatRequest with message and model selection

    Returns:
        ChatResponse with agent's reply
    """
    logger.info(f"Chat endpoint called with model={request.model}")

    try:
        response_text, latency = await run_chat(request.message, request.model)

        model_name = os.getenv(f"MODEL_{request.model.upper()}_NAME")

        return ChatResponse(
            response=response_text,
            model_used=model_name,
            latency_seconds=latency
        )

    except Exception as e:
        logger.error(f"Chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


# ===== Status and Metrics Endpoints =====

@app.get("/status", response_model=AgentStatus)
async def get_status():
    """
    Get current agent status and metrics.

    Returns:
        AgentStatus with metrics for both models
    """
    metrics_a, metrics_b = get_metrics()

    return AgentStatus(
        status="running",
        model_a_metrics=metrics_a,
        model_b_metrics=metrics_b,
        uptime_seconds=time.time() - start_time
    )


@app.get("/metrics")
async def get_metrics_endpoint():
    """
    Get detailed metrics for both models.

    Returns:
        Dictionary with metrics for Model A and Model B
    """
    metrics_a, metrics_b = get_metrics()

    return {
        "model_a": {
            "name": metrics_a.model_name,
            "total_requests": metrics_a.total_requests,
            "successful_requests": metrics_a.successful_requests,
            "failed_requests": metrics_a.failed_requests,
            "success_rate": (
                metrics_a.successful_requests / metrics_a.total_requests
                if metrics_a.total_requests > 0 else 0
            ),
            "avg_latency_seconds": metrics_a.avg_latency_seconds
        },
        "model_b": {
            "name": metrics_b.model_name,
            "total_requests": metrics_b.total_requests,
            "successful_requests": metrics_b.successful_requests,
            "failed_requests": metrics_b.failed_requests,
            "success_rate": (
                metrics_b.successful_requests / metrics_b.total_requests
                if metrics_b.total_requests > 0 else 0
            ),
            "avg_latency_seconds": metrics_b.avg_latency_seconds
        }
    }


# ===== Debug Endpoints =====

@app.post("/debug/test")
async def debug_test(message: str = "Hello, can you respond?", model: Literal["a", "b"] = "a"):
    """
    Test minimal agent with NO TOOLS to diagnose PydanticAI hanging.

    Args:
        message: Test message
        model: Which model to use ("a" or "b")

    Returns:
        Test result dictionary
    """
    logger.info(f"Debug test endpoint called - model={model}")
    result = await run_debug_test(message, model)
    return result


@app.post("/debug/direct-llm")
async def debug_direct_llm(model: Literal["a", "b"] = "a"):
    """
    Bypass PydanticAI and call Ollama directly to diagnose issues.

    Args:
        model: Which model to use ("a" or "b")

    Returns:
        Test result dictionary
    """
    logger.info(f"Direct LLM test endpoint called - model={model}")
    result = await run_direct_llm_test(model)
    return result


# ===== Root Endpoint =====

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "ai-agent",
        "version": "1.0.0",
        "description": "Autonomous AI agent for system monitoring and repair",
        "models": {
            "a": os.getenv("MODEL_A_NAME", "mistral:7b-instruct"),
            "b": os.getenv("MODEL_B_NAME", "ministral-3:8b-instruct-2512-q8_0")
        },
        "endpoints": {
            "repair": "POST /repair?model={a|b}",
            "chat": "POST /chat",
            "status": "GET /status",
            "metrics": "GET /metrics",
            "health": "GET /health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
