"""
Crash failure handler.
Causes the application to exit with an error code when activated.
"""

import os
import logging

logger = logging.getLogger(__name__)


def handle_crash():
    """
    Handle crash failure mode.
    This will cause the container to exit, simulating a critical failure.
    """
    logger.critical("CRASH FAILURE MODE ACTIVATED - Application exiting with error code 1")
    logger.critical("This simulates a catastrophic failure requiring container restart")

    # Force exit with error code
    os._exit(1)
