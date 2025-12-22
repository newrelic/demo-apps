"""
Configuration error failure handler.
Simulates missing or invalid configuration.
"""

import os
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def handle_config_error():
    """
    Handle configuration error failure mode.
    Checks for required environment variables and raises error if missing.

    Raises:
        HTTPException: 500 error indicating configuration is invalid
    """
    required_env_var = "DATABASE_URL"
    db_url = os.getenv(required_env_var)

    # In config_error mode, pretend DATABASE_URL is missing or invalid
    logger.error(f"CONFIG ERROR MODE ACTIVATED - {required_env_var} validation failed")
    logger.error("This simulates missing or incorrect configuration")

    raise HTTPException(
        status_code=500,
        detail=f"Configuration error: {required_env_var} is not properly configured. "
               f"Please check environment variables and restart the service."
    )
