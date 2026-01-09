"""
httpx instrumentation for capturing LLM token usage.

Monkey-patches httpx.AsyncClient.post to intercept all HTTP calls
and extract token usage from Ollama/OpenAI API responses.
"""

import httpx
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Store reference to original method
_original_async_post = httpx.AsyncClient.post

# Track whether patch is applied
_patch_applied = False


async def instrumented_async_post(self, url, **kwargs):
    """
    Instrumented version of httpx.AsyncClient.post that captures token usage.

    Intercepts all POST calls and extracts token counts from OpenAI-compatible
    API responses (Ollama). Records to New Relic and populates token cache.
    """
    start_time = time.time()

    # Call original method
    response = await _original_async_post(self, url, **kwargs)

    # Check if this is a chat completion request
    url_str = str(url)
    is_chat_completion = '/chat/completions' in url_str or '/v1/chat/completions' in url_str

    if is_chat_completion and response.status_code == 200:
        try:
            # Extract request details
            request_json = kwargs.get('json', {})
            model_name = request_json.get('model', 'unknown')
            messages = request_json.get('messages', [])

            # Get the user's prompt (last user message)
            prompt = ""
            for msg in reversed(messages):
                if msg.get('role') == 'user':
                    prompt = msg.get('content', '')
                    break

            # Parse response
            response_data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            # Import and call token recording function
            # This avoids circular imports by importing at runtime
            from agent import record_llm_tokens
            record_llm_tokens(model_name, prompt, response_data, latency_ms)

            logger.debug(f"[HTTPX-INTERCEPT] Captured tokens for {model_name} (via PydanticAI)")

        except Exception as e:
            # Don't break the application if token tracking fails
            logger.warning(f"[HTTPX-INTERCEPT] Failed to extract tokens: {e}")

    return response


def apply_httpx_patch():
    """
    Apply monkey-patch to httpx.AsyncClient.post.

    Safe to call multiple times - only applies once.
    """
    global _patch_applied

    if _patch_applied:
        logger.debug("[HTTPX-PATCH] Already applied, skipping")
        return

    logger.info("[HTTPX-PATCH] Applying httpx.AsyncClient.post monkey-patch for token tracking")
    httpx.AsyncClient.post = instrumented_async_post
    _patch_applied = True
    logger.info("[HTTPX-PATCH] ✅ Monkey-patch applied successfully")


def remove_httpx_patch():
    """
    Remove monkey-patch and restore original httpx.AsyncClient.post.

    Useful for testing or cleanup.
    """
    global _patch_applied

    if not _patch_applied:
        logger.debug("[HTTPX-PATCH] Not applied, nothing to remove")
        return

    logger.info("[HTTPX-PATCH] Removing httpx.AsyncClient.post monkey-patch")
    httpx.AsyncClient.post = _original_async_post
    _patch_applied = False
    logger.info("[HTTPX-PATCH] Monkey-patch removed")
