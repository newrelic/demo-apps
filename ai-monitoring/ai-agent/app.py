"""
AI Agent FastAPI Service - LangChain Implementation

Provides:
- /repair endpoint for autonomous tool workflows
- /chat endpoint for conversational AI with tool access
- /status and /metrics endpoints for monitoring
- A/B model comparison support
"""

import os
import logging
import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import newrelic.agent

# LangChain agent components
from langchain_agent import (
    init_router,
    get_router,
    run_agent_workflow,
    get_all_metrics,
)
from prompts import REPAIR_PROMPT_TEMPLATE, CHAT_PROMPT_TEMPLATE
from workflows import get_workflow_prompt
from prompt_pool import list_all_prompts, get_prompt_stats
from models import (
    RepairResult,
    ChatRequest,
    ChatResponse,
    AgentStatus,
    ToolCall,
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.

    Initializes ModelRouter with agents on startup.
    """
    logger.info("=" * 60)
    logger.info("🤖 AI Agent Service Starting (LangChain)")
    logger.info("=" * 60)
    logger.info(f"Model A: {os.getenv('MODEL_A_NAME')} at {os.getenv('OLLAMA_MODEL_A_URL')}")
    logger.info(f"Model B: {os.getenv('MODEL_B_NAME')} at {os.getenv('OLLAMA_MODEL_B_URL')}")
    logger.info(f"MCP Server: {os.getenv('MCP_SERVER_URL')}")
    logger.info("=" * 60)

    # Initialize LangChain agent router
    try:
        init_router(REPAIR_PROMPT_TEMPLATE)
        logger.info("✅ ModelRouter initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize ModelRouter: {e}", exc_info=True)
        raise

    # Register New Relic application (for metadata)
    try:
        application = newrelic.agent.register_application(timeout=10.0)
        logger.info("✅ New Relic application registered")

        # Register token count callback (for providers without token counts in responses)
        from observability import token_count_callback
        newrelic.agent.set_llm_token_count_callback(token_count_callback, application=application)
        logger.info("✅ New Relic LLM token count callback registered")
    except Exception as e:
        logger.warning(f"⚠️  Failed to register NR application or token callback: {e}")

    logger.info("=" * 60)
    logger.info("Service ready to accept requests")
    logger.info("=" * 60)

    yield

    logger.info("AI Agent Service shutting down...")


# Create FastAPI application
app = FastAPI(
    title="AI Agent Service",
    description="LangChain-based AI agent for system monitoring and repair with A/B model comparison",
    version="2.0.0",  # Bumped for LangChain migration
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
        "version": "2.0.0-langchain",
        "uptime_seconds": time.time() - start_time
    }


# ===== Repair Workflow Endpoint =====

@app.post("/repair", response_model=RepairResult)
async def trigger_repair(
    model: Literal["a", "b"] = "a",
    deterministic: bool = False,
    workflow: str = None
):
    """
    Trigger autonomous repair workflow.

    Args:
        model: Which model to use ("a" or "b")
        deterministic: If True, uses predictable workflow for load testing
        workflow: Optional workflow name (e.g., "minimal_single_tool") - overrides deterministic

    Returns:
        RepairResult with actions taken and outcome
    """
    start_time_req = time.time()
    logger.info(f"[REPAIR] Request: model={model}, deterministic={deterministic}, workflow={workflow}")

    try:
        # Get prompt - workflow parameter overrides deterministic
        if workflow:
            prompt = get_workflow_prompt(workflow)
            logger.info(f"[REPAIR] Using custom workflow: {workflow}")
        elif deterministic:
            prompt = get_workflow_prompt("repair_deterministic")
            logger.info("[REPAIR] Using deterministic workflow")
        else:
            prompt = get_workflow_prompt("repair_open_ended")
            logger.info("[REPAIR] Using open-ended workflow")

        # Execute agent workflow
        result = await run_agent_workflow(model, prompt)

        # Extract tool calls from intermediate steps
        tool_calls = []
        actions_taken = []

        for step in result.get('intermediate_steps', []):
            if len(step) >= 2:
                action, observation = step[0], step[1]

                # Extract tool name and arguments
                tool_name = action.tool if hasattr(action, 'tool') else str(action)
                tool_input = action.tool_input if hasattr(action, 'tool_input') else {}

                tool_calls.append(ToolCall(
                    tool_name=tool_name,
                    arguments=tool_input if isinstance(tool_input, dict) else {},
                    success=True,
                    result=str(observation)[:200]  # Truncate for brevity
                ))

                # Build human-readable action description
                if "health" in tool_name.lower():
                    actions_taken.append("Checked system health")
                elif "logs" in tool_name.lower():
                    service = tool_input.get('service_name', 'service') if isinstance(tool_input, dict) else 'service'
                    actions_taken.append(f"Retrieved logs from {service}")
                elif "restart" in tool_name.lower():
                    service = tool_input.get('service_name', 'service') if isinstance(tool_input, dict) else 'service'
                    actions_taken.append(f"Restarted {service}")
                elif "diagnostics" in tool_name.lower():
                    service = tool_input.get('service_name', 'service') if isinstance(tool_input, dict) else 'service'
                    actions_taken.append(f"Ran diagnostics on {service}")
                elif "database" in tool_name.lower():
                    actions_taken.append("Checked database status")
                elif "config" in tool_name.lower():
                    actions_taken.append("Updated service configuration")
                else:
                    actions_taken.append(f"Executed {tool_name}")

        # Determine which services were restarted
        containers_restarted = []
        for tool_call in tool_calls:
            if "restart" in tool_call.tool_name.lower():
                service_name = tool_call.arguments.get('service_name', 'unknown')
                containers_restarted.append(service_name)

        elapsed = time.time() - start_time_req
        logger.info(
            f"[REPAIR] Completed: model={model}, success={result['success']}, "
            f"latency={elapsed:.2f}s, tools={len(tool_calls)}"
        )

        return RepairResult(
            success=result['success'],
            actions_taken=actions_taken if actions_taken else ["No actions needed"],
            containers_restarted=containers_restarted,
            final_status=result['output'],
            model_used=result['model_name'],
            latency_seconds=result['latency_seconds'],
            tool_calls=tool_calls,
            ai_reasoning=None  # ReAct traces captured in tool_calls
        )

    except Exception as e:
        elapsed = time.time() - start_time_req
        logger.error(
            f"[REPAIR] Failed: model={model}, elapsed={elapsed:.2f}s, error={str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Repair workflow failed: {str(e)}")


# ===== Chat Endpoint =====

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the AI agent.

    Args:
        request: ChatRequest with message and model selection

    Returns:
        ChatResponse with agent's reply
    """
    logger.info(f"[CHAT] Request: model={request.model}, message={request.message[:50]}...")

    try:
        # Execute chat workflow
        result = await run_agent_workflow(request.model, request.message)

        model_name = result['model_name']

        logger.info(
            f"[CHAT] Completed: model={request.model}, "
            f"latency={result['latency_seconds']:.2f}s"
        )

        return ChatResponse(
            response=result['output'],
            model_used=model_name,
            latency_seconds=result['latency_seconds']
        )

    except Exception as e:
        logger.error(f"[CHAT] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


# ===== Prompts Endpoint =====

@app.get("/prompts")
async def get_prompts():
    """
    Get list of available prompts from the prompt pool.

    Returns:
        Dictionary with prompt list and statistics
    """
    try:
        prompts = list_all_prompts()
        stats = get_prompt_stats()

        # Format prompts for UI consumption
        formatted_prompts = [
            {
                'id': idx,
                'prompt': p['prompt'],
                'category': p['category'],
                'description': p.get('description', ''),
                'preview': p['prompt'][:80] + ('...' if len(p['prompt']) > 80 else ''),
                'endpoint': p.get('endpoint', '/chat'),
                'use_workflow': p.get('use_workflow', False),
                'workflow': p.get('workflow', None)
            }
            for idx, p in enumerate(prompts)
        ]

        return {
            'success': True,
            'prompts': formatted_prompts,
            'total': len(formatted_prompts),
            'stats': stats
        }
    except Exception as e:
        logger.error(f"[PROMPTS] Failed to get prompts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get prompts: {str(e)}")


# ===== Status and Metrics Endpoints =====

@app.get("/status", response_model=AgentStatus)
async def get_status():
    """
    Get current agent status and metrics.

    Returns:
        AgentStatus with metrics for both models
    """
    try:
        all_metrics = get_all_metrics()

        return AgentStatus(
            status="running",
            model_a_metrics=all_metrics['model_a'],
            model_b_metrics=all_metrics['model_b'],
            uptime_seconds=time.time() - start_time
        )

    except Exception as e:
        logger.error(f"[STATUS] Failed: {e}", exc_info=True)
        return AgentStatus(
            status="error",
            model_a_metrics={},
            model_b_metrics={},
            uptime_seconds=time.time() - start_time
        )


@app.get("/metrics")
async def get_metrics_endpoint():
    """
    Get detailed metrics for both models.

    Returns:
        Dictionary with metrics for Model A and Model B, plus cache stats
    """
    try:
        from cache import get_cache_stats

        metrics = get_all_metrics()
        metrics['cache_stats'] = get_cache_stats()
        return metrics
    except Exception as e:
        logger.error(f"[METRICS] Failed: {e}", exc_info=True)
        return {
            "error": str(e),
            "model_a": {},
            "model_b": {},
            "cache_stats": {}
        }


# ===== Debug Endpoints =====

@app.post("/debug/direct-llm")
async def debug_direct_llm(model: Literal["a", "b"] = "a", message: str = "Hello"):
    """
    Direct LLM call without agent orchestration (for debugging).

    Args:
        model: Which model to use ("a" or "b")
        message: Test message

    Returns:
        Raw LLM response with timing
    """
    logger.info(f"[DEBUG-LLM] Direct call: model={model}, message={message[:50]}...")

    try:
        router = get_router()
        llm = router.model_a if model == "a" else router.model_b
        model_name = router.get_model_name(model)

        start_time_llm = time.time()

        # Direct LLM invocation (no tools, no agent)
        from langchain.schema import HumanMessage
        response = await llm.ainvoke([HumanMessage(content=message)])

        latency = time.time() - start_time_llm

        logger.info(f"[DEBUG-LLM] Success: latency={latency:.2f}s")

        return {
            "success": True,
            "model": model_name,
            "model_variant": model,
            "response": response.content,
            "latency_seconds": latency,
        }

    except Exception as e:
        logger.error(f"[DEBUG-LLM] Failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "model": model,
        }


# ===== Root Endpoint =====

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "ai-agent",
        "version": "2.0.0-langchain",
        "description": "LangChain-based AI agent for system monitoring and repair",
        "framework": "langchain",
        "models": {
            "a": os.getenv("MODEL_A_NAME", "mistral:7b-instruct"),
            "b": os.getenv("MODEL_B_NAME", "ministral-3:8b-instruct-2512-q8_0")
        },
        "endpoints": {
            "repair": "POST /repair?model={a|b}&workflow={workflow_name}",
            "chat": "POST /chat (body: {message, model})",
            "prompts": "GET /prompts",
            "status": "GET /status",
            "metrics": "GET /metrics",
            "health": "GET /health",
            "debug": "POST /debug/direct-llm?model={a|b}&message=..."
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
