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

from agent import run_repair_workflow, run_chat, get_metrics, model_a_metrics, model_b_metrics
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

# Track service start time
start_time = time.time()


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
    logger.info(f"Repair endpoint called with model={model}")

    try:
        result = await run_repair_workflow(model)
        return result

    except Exception as e:
        logger.error(f"Repair workflow failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Repair workflow failed: {str(e)}")


@app.post("/repair/compare", response_model=ComparisonResult)
async def compare_repairs():
    """
    Run repair workflow with both models and compare results.

    Returns:
        ComparisonResult with side-by-side comparison
    """
    logger.info("Running repair comparison with both models")

    try:
        # Run both models in sequence
        result_a = await run_repair_workflow("a")
        result_b = await run_repair_workflow("b")

        # Determine winner based on success and latency
        winner = None
        reason = ""

        if result_a.success and not result_b.success:
            winner = "a"
            reason = "Model A succeeded while Model B failed"
        elif result_b.success and not result_a.success:
            winner = "b"
            reason = "Model B succeeded while Model A failed"
        elif result_a.success and result_b.success:
            if result_a.latency_seconds < result_b.latency_seconds:
                winner = "a"
                reason = f"Both succeeded, but Model A was faster ({result_a.latency_seconds:.2f}s vs {result_b.latency_seconds:.2f}s)"
            elif result_b.latency_seconds < result_a.latency_seconds:
                winner = "b"
                reason = f"Both succeeded, but Model B was faster ({result_b.latency_seconds:.2f}s vs {result_a.latency_seconds:.2f}s)"
            else:
                winner = "tie"
                reason = "Both models performed equally"
        else:
            winner = "tie"
            reason = "Both models failed"

        return ComparisonResult(
            model_a_result=result_a,
            model_b_result=result_b,
            winner=winner,
            reason=reason
        )

    except Exception as e:
        logger.error(f"Comparison failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


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


@app.post("/chat/compare")
async def compare_chat(message: str):
    """
    Send the same message to both models and compare responses.

    Args:
        message: User message

    Returns:
        Comparison of both model responses
    """
    logger.info("Running chat comparison with both models")

    try:
        # Run both models in parallel
        import asyncio
        results = await asyncio.gather(
            run_chat(message, "a"),
            run_chat(message, "b")
        )

        response_a, latency_a = results[0]
        response_b, latency_b = results[1]

        return {
            "model_a": {
                "model": os.getenv("MODEL_A_NAME"),
                "response": response_a,
                "latency_seconds": latency_a
            },
            "model_b": {
                "model": os.getenv("MODEL_B_NAME"),
                "response": response_b,
                "latency_seconds": latency_b
            }
        }

    except Exception as e:
        logger.error(f"Chat comparison failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat comparison failed: {str(e)}")


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


# ===== Root Endpoint =====

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "ai-agent",
        "version": "1.0.0",
        "description": "Autonomous AI agent for system monitoring and repair",
        "models": {
            "a": os.getenv("MODEL_A_NAME", "llama3.2:1b"),
            "b": os.getenv("MODEL_B_NAME", "qwen2.5:0.5b")
        },
        "endpoints": {
            "repair": "POST /repair?model={a|b}",
            "repair_compare": "POST /repair/compare",
            "chat": "POST /chat",
            "chat_compare": "POST /chat/compare?message=...",
            "status": "GET /status",
            "metrics": "GET /metrics",
            "health": "GET /health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
