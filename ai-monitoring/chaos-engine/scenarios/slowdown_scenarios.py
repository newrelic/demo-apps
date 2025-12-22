"""
Slowdown scenario - causes target to respond slowly.
"""

import json
import logging
import random
from pathlib import Path

logger = logging.getLogger(__name__)


def inject_slowdown(state_file: Path, delay: int = None):
    """
    Inject slowdown failure by writing slow mode to state file.

    Args:
        state_file: Path to the shared failure state file
        delay: Delay in seconds (if None, random between 10-30)
    """
    if delay is None:
        delay = random.randint(10, 30)

    logger.warning(f"🐌 CHAOS: Injecting SLOWDOWN scenario ({delay}s delay)")
    logger.info("This will cause the target-app to respond slowly, potentially timing out")

    import time
    state = {
        "mode": "slow",
        "delay": delay,
        "timestamp": time.time(),
        "injected_by": "chaos-engine"
    }

    try:
        with open(state_file, 'w') as f:
            json.dump(state, f)
        logger.info(f"✓ Slowdown scenario written to {state_file}")
    except Exception as e:
        logger.error(f"Failed to write slowdown scenario: {e}")
