"""
LangChain agent implementation with dual model routing.

Provides:
- ModelRouter for A/B model comparison
- ReAct agent setup with tool calling
- Async execution support
"""

import os
import logging
from typing import Literal, Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate

from mcp_tools import create_mcp_tools
from observability import NewRelicCallback, MetricsTracker

logger = logging.getLogger(__name__)

# Model configurations
# Use OpenAI-compatible endpoints (/v1/chat/completions) for New Relic instrumentation
# This allows New Relic to automatically create LlmChatCompletionMessage events
OLLAMA_MODEL_A_URL = os.getenv("OLLAMA_MODEL_A_URL", "http://ollama-model-a:11434/v1")
OLLAMA_MODEL_B_URL = os.getenv("OLLAMA_MODEL_B_URL", "http://ollama-model-b:11434/v1")
MODEL_A_NAME = os.getenv("MODEL_A_NAME", "mistral:7b-instruct")
MODEL_B_NAME = os.getenv("MODEL_B_NAME", "ministral-3:8b-instruct-2512-q8_0")


class ModelRouter:
    """
    Manages A/B model routing with separate agent instances.

    Creates and maintains two independent agent executors (Model A and Model B)
    with their own LLM instances, callbacks, and metrics tracking.
    """

    def __init__(self, prompt_template: PromptTemplate):
        """
        Initialize model router with both agents.

        Args:
            prompt_template: PromptTemplate for agent system prompt
        """
        logger.info("=" * 60)
        logger.info("Initializing ModelRouter")
        logger.info("=" * 60)

        # Initialize metrics trackers
        self.metrics_a = MetricsTracker(MODEL_A_NAME)
        self.metrics_b = MetricsTracker(MODEL_B_NAME)

        # Create LLM instances using OpenAI-compatible API
        # This enables New Relic automatic instrumentation for LlmChatCompletionMessage events
        logger.info(f"Model A: {MODEL_A_NAME} at {OLLAMA_MODEL_A_URL}")
        self.model_a = ChatOpenAI(
            model=MODEL_A_NAME,
            base_url=OLLAMA_MODEL_A_URL,
            api_key="ollama",  # Ollama doesn't require real API key, but ChatOpenAI needs one
            temperature=0.1,  # Low temperature for deterministic tool calls
            max_tokens=2048,  # Max output tokens
            # Note: keep_alive is not supported via OpenAI-compatible API
            # Models will auto-unload after default timeout (5 minutes)
        )

        logger.info(f"Model B: {MODEL_B_NAME} at {OLLAMA_MODEL_B_URL}")
        self.model_b = ChatOpenAI(
            model=MODEL_B_NAME,
            base_url=OLLAMA_MODEL_B_URL,
            api_key="ollama",  # Ollama doesn't require real API key, but ChatOpenAI needs one
            temperature=0.1,
            max_tokens=2048,
            # Note: keep_alive is not supported via OpenAI-compatible API
            # Models will auto-unload after default timeout (5 minutes)
        )

        # Create MCP tools (shared between agents)
        self.tools = create_mcp_tools()
        logger.info(f"Created {len(self.tools)} MCP tools")

        # Create agent executors
        logger.info("Creating agent executors...")
        self.agent_a = self._create_agent(
            self.model_a,
            MODEL_A_NAME,
            "a",
            prompt_template
        )
        self.agent_b = self._create_agent(
            self.model_b,
            MODEL_B_NAME,
            "b",
            prompt_template
        )

        logger.info("=" * 60)
        logger.info("ModelRouter initialized successfully")
        logger.info("=" * 60)

    def _create_agent(
        self,
        llm: ChatOpenAI,
        model_name: str,
        model_variant: str,
        prompt_template: PromptTemplate
    ) -> AgentExecutor:
        """
        Create a ReAct agent executor.

        Args:
            llm: ChatOpenAI instance (pointed at Ollama)
            model_name: Full model name
            model_variant: Model identifier ("a" or "b")
            prompt_template: System prompt template

        Returns:
            AgentExecutor configured for tool calling
        """
        # Create New Relic callback for this model
        nr_callback = NewRelicCallback(model_name, model_variant)

        # CRITICAL FIX: Bind callbacks to LLM so it triggers on_llm_start/on_llm_end
        # Without this, only AgentExecutor events fire (on_agent_finish, on_tool_*),
        # but NOT LLM events, which prevents custom attributes from being added to LLM events
        llm_with_callbacks = llm.with_config(callbacks=[nr_callback])

        # Create ReAct agent with callback-enabled LLM
        agent = create_react_agent(
            llm=llm_with_callbacks,
            tools=self.tools,
            prompt=prompt_template,
        )

        # Wrap in AgentExecutor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            callbacks=[nr_callback],
            handle_parsing_errors=True,  # Graceful fallback for parsing errors
            max_iterations=5,  # Allow up to 5 iterations for complex workflows (detect, diagnose, repair, verify, summarize)
            max_execution_time=90,  # 90 second timeout (allows 3-4 tool calls @ 20s each)
            return_intermediate_steps=True,  # Capture tool execution traces
            verbose=True,  # Detailed logging
            early_stopping_method="force",  # Force stop after max iterations
        )

        logger.info(
            f"Created agent executor for {model_variant}: "
            f"max_iterations=5, timeout=90s, tools={len(self.tools)}"
        )

        return agent_executor

    def get_agent(self, model: Literal["a", "b"]) -> AgentExecutor:
        """
        Get agent executor for specified model.

        Args:
            model: Model identifier ("a" or "b")

        Returns:
            AgentExecutor for the specified model
        """
        return self.agent_a if model == "a" else self.agent_b

    def get_metrics(self, model: Literal["a", "b"]) -> MetricsTracker:
        """
        Get metrics tracker for specified model.

        Args:
            model: Model identifier ("a" or "b")

        Returns:
            MetricsTracker for the specified model
        """
        return self.metrics_a if model == "a" else self.metrics_b

    def get_model_name(self, model: Literal["a", "b"]) -> str:
        """
        Get model name for specified model variant.

        Args:
            model: Model identifier ("a" or "b")

        Returns:
            Full model name
        """
        return MODEL_A_NAME if model == "a" else MODEL_B_NAME


# Global router instance (initialized by app.py)
_router = None


def init_router(prompt_template: PromptTemplate) -> ModelRouter:
    """
    Initialize global model router.

    Args:
        prompt_template: System prompt template for agents

    Returns:
        Initialized ModelRouter instance
    """
    global _router
    _router = ModelRouter(prompt_template)
    return _router


def get_router() -> ModelRouter:
    """
    Get global model router instance.

    Returns:
        ModelRouter instance

    Raises:
        RuntimeError: If router not initialized
    """
    if _router is None:
        raise RuntimeError(
            "ModelRouter not initialized. Call init_router() first."
        )
    return _router


async def run_agent_workflow(
    model: Literal["a", "b"],
    prompt: str
) -> Dict[str, Any]:
    """
    Execute agent workflow with specified model.

    Args:
        model: Model identifier ("a" or "b")
        prompt: User prompt/task description

    Returns:
        Dictionary with:
        - output: Agent's final response
        - intermediate_steps: List of (AgentAction, observation) tuples
        - model_name: Model used
        - success: Whether execution succeeded
    """
    import newrelic.agent
    from observability import generate_feedback_rating, record_feedback_event

    router = get_router()
    agent = router.get_agent(model)
    metrics = router.get_metrics(model)
    model_name = router.get_model_name(model)

    import time
    start_time = time.time()
    success = False
    result = None
    error_msg = None

    # Capture trace_id for feedback event
    trace_id = newrelic.agent.current_trace_id()

    try:
        logger.info(f"[AGENT-WORKFLOW] Starting with model {model} ({model_name})")
        logger.info(f"[AGENT-WORKFLOW] Prompt: {prompt[:100]}...")
        logger.debug(f"[AGENT-WORKFLOW] Trace ID: {trace_id}")

        # Execute agent
        result = await agent.ainvoke({"input": prompt})

        success = True
        latency = time.time() - start_time

        # Token counts tracked by New Relic via token_count_callback
        # TODO: Optionally extract from NewRelicCallback for local metrics aggregation
        total_tokens = 0

        # Count tool calls for feedback heuristic
        tool_count = len(result.get('intermediate_steps', []))

        # Record metrics
        metrics.record_request(success=True, latency=latency, tokens=total_tokens)

        # Generate and record feedback event
        rating, category, message = generate_feedback_rating(
            success=True,
            latency_seconds=latency,
            tool_count=tool_count,
            error=None
        )

        if trace_id:
            record_feedback_event(
                trace_id=trace_id,
                rating=rating,
                category=category,
                message=message,
                metadata={
                    'model_variant': model,
                    'model_name': model_name,
                    'tool_count': tool_count,
                    'latency_seconds': round(latency, 2),
                    'prompt_length': len(prompt)
                }
            )

        logger.info(
            f"[AGENT-WORKFLOW] Completed successfully: "
            f"model={model}, latency={latency:.2f}s, "
            f"steps={tool_count}, feedback={rating}"
        )

        return {
            'output': result.get('output', ''),
            'intermediate_steps': result.get('intermediate_steps', []),
            'model_name': model_name,
            'model_variant': model,
            'success': True,
            'latency_seconds': latency,
        }

    except Exception as e:
        latency = time.time() - start_time
        error_msg = str(e)
        metrics.record_request(success=False, latency=latency)

        # Generate and record negative feedback for errors
        rating, category, message = generate_feedback_rating(
            success=False,
            latency_seconds=latency,
            tool_count=0,
            error=error_msg
        )

        if trace_id:
            record_feedback_event(
                trace_id=trace_id,
                rating=rating,
                category=category,
                message=message,
                metadata={
                    'model_variant': model,
                    'model_name': model_name,
                    'error_type': type(e).__name__,
                    'latency_seconds': round(latency, 2)
                }
            )

        logger.error(
            f"[AGENT-WORKFLOW] Failed: model={model}, "
            f"error={type(e).__name__}: {e}",
            exc_info=True
        )

        return {
            'output': f"Error: {str(e)}",
            'intermediate_steps': result.get('intermediate_steps', []) if result else [],
            'model_name': model_name,
            'model_variant': model,
            'success': False,
            'latency_seconds': latency,
            'error': error_msg,
        }


def get_all_metrics() -> Dict[str, Dict[str, Any]]:
    """
    Get metrics for all models.

    Returns:
        Dictionary with model_a and model_b metrics
    """
    router = get_router()
    return {
        'model_a': router.metrics_a.to_dict(),
        'model_b': router.metrics_b.to_dict(),
    }
