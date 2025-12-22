"""
Configuration error scenario - causes target to fail due to missing config.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def inject_config_error(state_file: Path):
    """
    Inject configuration error by writing config_error mode to state file.

    Args:
        state_file: Path to the shared failure state file
    """
    logger.warning("⚙️  CHAOS: Injecting CONFIG ERROR scenario")
    logger.info("This will cause the target-app to fail configuration validation")

    import time
    state = {
        "mode": "config_error",
        "delay": 0,
        "timestamp": time.time(),
        "injected_by": "chaos-engine"
    }

    try:
        with open(state_file, 'w') as f:
            json.dump(state, f)
        logger.info(f"✓ Config error scenario written to {state_file}")
    except Exception as e:
        logger.error(f"Failed to write config error scenario: {e}")
