"""
Slow response failure handler.
Injects artificial delays into request processing.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def handle_slow_response(delay: int):
    """
    Handle slow response failure mode.
    Introduces artificial latency to simulate performance degradation.

    Args:
        delay: Number of seconds to delay
    """
    logger.warning(f"SLOW RESPONSE MODE ACTIVATED - Delaying response by {delay} seconds")
    logger.warning("This simulates performance degradation or timeout issues")

    await asyncio.sleep(delay)

    logger.info(f"Delay of {delay} seconds completed")
