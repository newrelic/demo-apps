"""
Chaos Engine - Main orchestrator for failure injection.

This service randomly injects failures into the target-app to demonstrate
autonomous AI-driven repair capabilities.
"""

import os
import json
import logging
import time
import signal
import sys
from pathlib import Path

from scheduler import ChaosScheduler
from scenarios.crash_scenarios import inject_crash
from scenarios.slowdown_scenarios import inject_slowdown
from scenarios.config_scenarios import inject_config_error

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment
CHAOS_INTERVAL = int(os.getenv("CHAOS_INTERVAL", "180"))  # 3 minutes default
CHAOS_ENABLED = os.getenv("CHAOS_ENABLED", "true").lower() == "true"
FAILURE_STATE_FILE = Path(os.getenv("FAILURE_STATE_FILE", "/tmp/failure_state.json"))
RECOVERY_PERIOD = 30  # Seconds to wait after injecting failure

# Global flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    running = False


def clear_failure_state():
    """Reset failure state to healthy."""
    logger.info("Clearing failure state to healthy")
    state = {
        "mode": "healthy",
        "delay": 0,
        "timestamp": time.time(),
        "cleared_by": "chaos-engine"
    }
    try:
        with open(FAILURE_STATE_FILE, 'w') as f:
            json.dump(state, f)
        logger.info("✓ Failure state cleared")
    except Exception as e:
        logger.error(f"Failed to clear failure state: {e}")


def run_chaos_loop():
    """
    Main chaos engineering loop.

    Continuously injects random failures into the target application
    at configured intervals.
    """
    logger.info("=" * 60)
    logger.info("🌪️  Chaos Engine Starting")
    logger.info("=" * 60)
    logger.info(f"Chaos enabled: {CHAOS_ENABLED}")
    logger.info(f"Chaos interval: {CHAOS_INTERVAL}s")
    logger.info(f"Recovery period: {RECOVERY_PERIOD}s")
    logger.info(f"Failure state file: {FAILURE_STATE_FILE}")
    logger.info("=" * 60)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize scheduler
    scheduler = ChaosScheduler(interval=CHAOS_INTERVAL)

    # Wait for target app to stabilize
    logger.info("Waiting 60s for target-app to stabilize...")
    time.sleep(60)

    # Clear any existing failure state
    clear_failure_state()

    # Define scenarios with weights (crash: 30%, slow: 40%, config: 30%)
    scenarios = [
        ("CRASH", 0.30, lambda: inject_crash(FAILURE_STATE_FILE)),
        ("SLOWDOWN", 0.40, lambda: inject_slowdown(FAILURE_STATE_FILE)),
        ("CONFIG_ERROR", 0.30, lambda: inject_config_error(FAILURE_STATE_FILE)),
    ]

    global running
    while running:
        try:
            if not CHAOS_ENABLED:
                logger.info("Chaos is disabled, waiting...")
                time.sleep(60)
                continue

            if scheduler.should_inject_chaos():
                # Select and execute a random scenario
                scenario_name, scenario_func = scheduler.select_scenario(scenarios)

                logger.info("=" * 60)
                logger.info(f"💥 Injecting {scenario_name} failure")
                logger.info("=" * 60)

                scenario_func()
                scheduler.mark_injection()

                # Wait for recovery period to let failure manifest
                logger.info(f"Waiting {RECOVERY_PERIOD}s for failure to manifest...")
                time.sleep(RECOVERY_PERIOD)

                # Clear failure state to allow recovery
                clear_failure_state()

                # Wait for interval before next injection
                scheduler.wait_for_next_cycle()
            else:
                # Not time yet, wait a bit
                time.sleep(10)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            break
        except Exception as e:
            logger.error(f"Error in chaos loop: {e}", exc_info=True)
            time.sleep(10)

    logger.info("Chaos Engine shutting down...")
    clear_failure_state()
    logger.info("Goodbye! 👋")


if __name__ == "__main__":
    try:
        run_chaos_loop()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
