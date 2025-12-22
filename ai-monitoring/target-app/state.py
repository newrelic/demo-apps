"""
Failure state management for the Target App.
Reads failure state from shared volume to coordinate with Chaos Engine.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

FAILURE_STATE_FILE = Path(os.getenv("FAILURE_STATE_FILE", "/tmp/failure_state.json"))


def get_failure_state() -> Dict[str, any]:
    """
    Read current failure state from shared state file.

    Returns:
        Dictionary with failure mode and parameters:
        {
            "mode": "healthy" | "crash" | "slow" | "config_error",
            "delay": int (seconds, for slow mode),
            "timestamp": float
        }
    """
    try:
        if FAILURE_STATE_FILE.exists():
            with open(FAILURE_STATE_FILE, 'r') as f:
                state = json.load(f)
                logger.debug(f"Failure state: {state}")
                return state
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to decode failure state file: {e}")
    except Exception as e:
        logger.warning(f"Error reading failure state: {e}")

    # Default to healthy state
    return {"mode": "healthy", "delay": 0}


def write_failure_state(mode: str, delay: int = 0) -> None:
    """
    Write failure state to shared state file.
    Used for testing purposes.

    Args:
        mode: Failure mode (healthy, crash, slow, config_error)
        delay: Delay in seconds for slow mode
    """
    try:
        import time
        state = {
            "mode": mode,
            "delay": delay,
            "timestamp": time.time()
        }
        with open(FAILURE_STATE_FILE, 'w') as f:
            json.dump(state, f)
        logger.info(f"Wrote failure state: {state}")
    except Exception as e:
        logger.error(f"Failed to write failure state: {e}")


def clear_failure_state() -> None:
    """Clear failure state back to healthy."""
    write_failure_state("healthy", 0)
