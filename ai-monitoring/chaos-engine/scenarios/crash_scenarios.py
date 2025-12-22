"""
Crash scenario - causes the target container to exit.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def inject_crash(state_file: Path):
    """
    Inject crash failure by writing crash mode to state file.

    Args:
        state_file: Path to the shared failure state file
    """
    logger.warning("🔥 CHAOS: Injecting CRASH scenario")
    logger.info("This will cause the target-app to exit with error code 1")

    import time
    state = {
        "mode": "crash",
        "delay": 0,
        "timestamp": time.time(),
        "injected_by": "chaos-engine"
    }

    try:
        with open(state_file, 'w') as f:
            json.dump(state, f)
        logger.info(f"✓ Crash scenario written to {state_file}")
    except Exception as e:
        logger.error(f"Failed to write crash scenario: {e}")
