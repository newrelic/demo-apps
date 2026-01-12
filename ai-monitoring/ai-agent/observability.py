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
import tiktoken

logger = logging.getLogger(__name__)

# Cache tiktoken encoders
_TIKTOKEN_ENCODERS = {}


def _get_tiktoken_encoder(model: str):
    """
    Get or create cached tiktoken encoder for the given model.

    Args:
        model: Model name (e.g., "mistral:7b-instruct")

    Returns:
        tiktoken encoder
    """
    # Use cl100k_base encoding for most models (GPT-4, GPT-3.5-turbo baseline)
    # This is a reasonable approximation for Ollama models too
    encoding_name = "cl100k_base"

    if encoding_name not in _TIKTOKEN_ENCODERS:
        _TIKTOKEN_ENCODERS[encoding_name] = tiktoken.get_encoding(encoding_name)

    return _TIKTOKEN_ENCODERS[encoding_name]


def token_count_callback(model: str, content: Any) -> int:
    """
    Callback for New Relic LLM token counting.

    New Relic calls this function with message content (strings) to count tokens.
    We use tiktoken to count tokens from the text content.

    Args:
        model: Model name from the request
        content: Message content (string) or response dict

    Returns:
        Token count
    """
    try:
        # Handle string content (most common case from New Relic)
        if isinstance(content, str):
            if not content or len(content) == 0:
                return 0

            # Count tokens using tiktoken
            encoder = _get_tiktoken_encoder(model)
            token_count = len(encoder.encode(content))

            # Debug logging only
            logger.debug(
                f"[NR-TOKEN-CALLBACK] Counted {token_count} tokens "
                f"for {len(content)} chars (model={model})"
            )

            return token_count

        # Handle dict content (legacy/fallback for explicit token counts)
        if isinstance(content, dict):
            # OpenAI format: usage.total_tokens
            if 'usage' in content:
                usage = content['usage']
                if isinstance(usage, dict):
                    total = usage.get('total_tokens', 0)
                    if total > 0:
                        logger.info(f"[NR-TOKEN-CALLBACK] Extracted from usage: {total}")
                        return total

            # Ollama format: prompt_eval_count + eval_count
            if 'prompt_eval_count' in content or 'eval_count' in content:
                prompt_tokens = content.get('prompt_eval_count', 0)
                completion_tokens = content.get('eval_count', 0)
                total = prompt_tokens + completion_tokens
                if total > 0:
                    logger.info(f"[NR-TOKEN-CALLBACK] Extracted from Ollama format: {total}")
                    return total

        return 0

    except Exception as e:
        logger.warning(f"[NR-TOKEN-CALLBACK] Error counting tokens: {e}")
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
    - Custom attributes for model comparison
    - Agent execution metrics
    - LLM-level event tracking (on_llm_start, on_llm_end)
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

        Extracts token counts from the LangChain response and records custom attributes.
        Note: Token counts in New Relic events come from tiktoken via token_count_callback.
        """
        logger.debug(f"[NR-CALLBACK] on_llm_end called - model={self.model_name}")
        latency_ms = (time.time() - self.llm_start_time) * 1000 if self.llm_start_time else 0

        # Extract token usage from LLM response for custom attributes
        # Note: Ollama's OpenAI-compatible endpoint doesn't include usage data,
        # but we attempt extraction anyway in case the provider changes
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        # Try generation_info first (Ollama native format)
        if response.generations and response.generations[0]:
            try:
                gen_info = response.generations[0][0].generation_info or {}
                prompt_tokens = gen_info.get('prompt_eval_count', 0)
                completion_tokens = gen_info.get('eval_count', 0)
                total_tokens = prompt_tokens + completion_tokens
            except (IndexError, AttributeError, TypeError):
                pass

        # Fallback: llm_output.token_usage (OpenAI-style)
        if total_tokens == 0 and response.llm_output:
            token_usage = response.llm_output.get('token_usage', {})
            prompt_tokens = token_usage.get('prompt_tokens', 0)
            completion_tokens = token_usage.get('completion_tokens', 0)
            total_tokens = token_usage.get('total_tokens', prompt_tokens + completion_tokens)

        # Log LLM completion for monitoring
        logger.info(
            f"[NR-LLM] LLM completion: model={self.model_name}, "
            f"tokens={total_tokens} ({prompt_tokens}p + {completion_tokens}c), "
            f"latency={latency_ms:.0f}ms"
        )

        # Note: New Relic automatically creates LlmChatCompletionMessage events
        # from the httpx HTTP calls that ChatOpenAI makes to Ollama's OpenAI-compatible API.
        # We don't need to manually record them - the automatic instrumentation
        # handles event creation. We just enrich them with custom attributes below.

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
