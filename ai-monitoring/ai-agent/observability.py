"""
New Relic observability integration for LangChain agents.

Provides callback handlers for:
- LLM token tracking and recording
- Custom attributes for model comparison
- Performance metrics
- LLM feedback events with binary ratings
"""

import logging
import time
import random
from typing import Any, Dict, List, Optional
import newrelic.agent
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import LLMResult

logger = logging.getLogger(__name__)


def token_count_callback(model: str, content: Dict[str, Any]) -> int:
    """
    Callback for New Relic LLM token counting.

    Workaround for NR agent bug preventing automatic token capture.

    Args:
        model: Model name
        content: Message content dict with token usage

    Returns:
        Token count extracted from content
    """
    # LangChain typically provides token usage in different formats
    # Try to extract from various possible locations
    if isinstance(content, dict):
        # Check for direct token usage
        if 'token_usage' in content:
            usage = content['token_usage']
            if isinstance(usage, dict):
                return usage.get('total_tokens', 0)

        # Check for usage_metadata (OpenAI format)
        if 'usage_metadata' in content:
            metadata = content['usage_metadata']
            if isinstance(metadata, dict):
                return metadata.get('total_tokens', 0)

    return 0


def record_feedback_event(
    trace_id: str,
    rating: str,
    category: str = None,
    message: str = None,
    metadata: Dict[str, Any] = None
):
    """
    Record LLM feedback event to New Relic.

    Args:
        trace_id: Trace ID where the chat completion occurred
        rating: Binary rating (e.g., "thumbs_up", "thumbs_down")
        category: Optional category of feedback
        message: Optional freeform feedback text
        metadata: Optional additional metadata
    """
    try:
        newrelic.agent.record_llm_feedback_event(
            trace_id=trace_id,
            rating=rating,
            category=category,
            message=message,
            metadata=metadata or {}
        )
        logger.debug(f"[NR-FEEDBACK] Recorded feedback: trace_id={trace_id}, rating={rating}")
    except Exception as e:
        logger.warning(f"[NR-FEEDBACK] Failed to record feedback event: {e}")


def generate_feedback_rating(
    success: bool,
    latency_seconds: float,
    tool_count: int = 0,
    error: str = None
) -> tuple[str, str, str]:
    """
    Generate realistic feedback rating based on response metrics.

    Uses heuristics to simulate user feedback:
    - Failures = thumbs_down
    - Very slow responses (>60s) = likely thumbs_down
    - Very fast successful responses (<5s) = likely thumbs_up
    - Multiple tool calls with success = likely thumbs_up
    - Otherwise, weighted random with bias toward positive

    Args:
        success: Whether the request succeeded
        latency_seconds: Response latency
        tool_count: Number of tools invoked
        error: Error message if any

    Returns:
        Tuple of (rating, category, message)
    """
    # Failure scenarios
    if not success:
        return (
            "thumbs_down",
            "error",
            f"Request failed: {error[:100] if error else 'unknown error'}"
        )

    # Very slow response (>60s) - 80% negative
    if latency_seconds > 60:
        if random.random() < 0.8:
            return (
                "thumbs_down",
                "slow_response",
                f"Response took too long ({latency_seconds:.0f}s)"
            )
        else:
            return (
                "thumbs_up",
                "accurate",
                "Slow but accurate response"
            )

    # Very fast successful response (<5s) - 90% positive
    if latency_seconds < 5:
        if random.random() < 0.9:
            return (
                "thumbs_up",
                "fast",
                f"Quick and helpful response ({latency_seconds:.1f}s)"
            )
        else:
            return (
                "thumbs_down",
                "inaccurate",
                "Response seemed too brief"
            )

    # Multiple tool calls with success - 85% positive
    if tool_count >= 2:
        if random.random() < 0.85:
            return (
                "thumbs_up",
                "thorough",
                f"Good diagnostic process with {tool_count} tools"
            )
        else:
            return (
                "thumbs_down",
                "overcomplicated",
                "Used too many tools unnecessarily"
            )

    # Single tool call - 75% positive
    if tool_count == 1:
        if random.random() < 0.75:
            return (
                "thumbs_up",
                "helpful",
                "Helpful response"
            )
        else:
            return (
                "thumbs_down",
                "incomplete",
                "Response lacked detail"
            )

    # No tool calls (conversational) - 70% positive
    if random.random() < 0.7:
        return (
            "thumbs_up",
            "informative",
            "Clear explanation"
        )
    else:
        return (
            "thumbs_down",
            "unhelpful",
            "Expected more detailed information"
        )


class NewRelicCallback(BaseCallbackHandler):
    """
    LangChain callback handler for New Relic instrumentation.

    Records:
    - LLM token usage (manual workaround for NR agent bug)
    - Custom attributes for model comparison
    - Agent execution metrics
    """

    def __init__(self, model_name: str, model_variant: str):
        """
        Initialize callback handler.

        Args:
            model_name: Full model name (e.g., "mistral:7b-instruct")
            model_variant: Model identifier ("a" or "b")
        """
        self.model_name = model_name
        self.model_variant = model_variant
        self.llm_start_time = None
        self.tool_calls = []

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Called when LLM starts generating."""
        self.llm_start_time = time.time()

        # Add custom attributes for model tracking
        txn = newrelic.agent.current_transaction()
        if txn:
            txn.add_custom_attribute('llm.model.variant', self.model_variant)
            txn.add_custom_attribute('llm.model.name', self.model_name)
            txn.add_custom_attribute('llm.vendor', 'ollama')
            txn.add_custom_attribute('agent.framework', 'langchain')
            txn.add_custom_attribute('agent.type', 'react')

        logger.debug(f"[NR-CALLBACK] LLM start: model={self.model_name}, variant={self.model_variant}")

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """
        Called when LLM finishes generating.

        Extracts token counts and records to New Relic.
        """
        latency_ms = (time.time() - self.llm_start_time) * 1000 if self.llm_start_time else 0

        # Extract token usage from LLM response
        llm_output = response.llm_output or {}
        token_usage = llm_output.get('token_usage', {})

        prompt_tokens = token_usage.get('prompt_tokens', 0)
        completion_tokens = token_usage.get('completion_tokens', 0)
        total_tokens = token_usage.get('total_tokens', 0)

        # TEMPORARY WORKAROUND: Manual token recording due to NR agent bug
        # TODO: Remove once New Relic fixes automatic token capture
        try:
            newrelic.agent.record_llm_chat_completion_summary(
                model=self.model_name,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                llm_vendor='ollama',
                response_time_ms=latency_ms,
            )
            logger.info(
                f"[NR-LLM] Recorded completion: model={self.model_name}, "
                f"tokens={total_tokens} ({prompt_tokens}p + {completion_tokens}c), "
                f"latency={latency_ms:.0f}ms"
            )
        except Exception as e:
            logger.warning(f"[NR-LLM] Failed to record completion: {e}")

        # Add token counts as custom attributes for analysis
        txn = newrelic.agent.current_transaction()
        if txn:
            txn.add_custom_attribute('llm.prompt_tokens', prompt_tokens)
            txn.add_custom_attribute('llm.completion_tokens', completion_tokens)
            txn.add_custom_attribute('llm.total_tokens', total_tokens)
            txn.add_custom_attribute('llm.latency_ms', latency_ms)

    def on_llm_error(
        self, error: BaseException, **kwargs: Any
    ) -> None:
        """Called when LLM encounters an error."""
        logger.error(f"[NR-CALLBACK] LLM error: {error}")

        # Record error in New Relic
        txn = newrelic.agent.current_transaction()
        if txn:
            txn.add_custom_attribute('llm.error', str(error))
            txn.add_custom_attribute('llm.error_type', type(error).__name__)

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Called when agent starts using a tool."""
        tool_name = serialized.get('name', 'unknown')
        self.tool_calls.append(tool_name)

        logger.debug(f"[NR-CALLBACK] Tool start: {tool_name}")

        # Track tool invocation
        txn = newrelic.agent.current_transaction()
        if txn:
            txn.add_custom_attribute(f'tool.{tool_name}.invoked', True)

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when tool finishes execution."""
        logger.debug(f"[NR-CALLBACK] Tool end: output length={len(output)}")

    def on_tool_error(
        self, error: BaseException, **kwargs: Any
    ) -> None:
        """Called when tool encounters an error."""
        logger.error(f"[NR-CALLBACK] Tool error: {error}")

        # Record tool error
        txn = newrelic.agent.current_transaction()
        if txn:
            txn.add_custom_attribute('tool.error', str(error))
            txn.add_custom_attribute('tool.error_type', type(error).__name__)

    def on_agent_finish(self, finish: Dict[str, Any], **kwargs: Any) -> None:
        """Called when agent completes execution."""
        # Record final metrics
        txn = newrelic.agent.current_transaction()
        if txn:
            txn.add_custom_attribute('agent.tool_calls', len(self.tool_calls))
            txn.add_custom_attribute('agent.success', True)

            # Record which tools were used
            if self.tool_calls:
                txn.add_custom_attribute('agent.tools_used', ','.join(self.tool_calls))

        logger.info(
            f"[NR-CALLBACK] Agent finished: "
            f"model={self.model_variant}, tools_used={len(self.tool_calls)}"
        )

    def on_agent_action(self, action: Any, **kwargs: Any) -> None:
        """Called when agent takes an action."""
        logger.debug(f"[NR-CALLBACK] Agent action: {action}")


class MetricsTracker:
    """
    Simple in-memory metrics tracker for model comparison.

    Tracks:
    - Request counts
    - Success/failure rates
    - Average latency
    - Total tokens used
    """

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.avg_latency_seconds = 0.0
        self.total_tokens = 0

    def record_request(self, success: bool, latency: float, tokens: int = 0):
        """Record a request execution."""
        self.total_requests += 1

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        # Update rolling average latency
        self.avg_latency_seconds = (
            (self.avg_latency_seconds * (self.total_requests - 1) + latency)
            / self.total_requests
        )

        self.total_tokens += tokens

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'model_name': self.model_name,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.success_rate,
            'avg_latency_seconds': self.avg_latency_seconds,
            'total_tokens': self.total_tokens,
        }
