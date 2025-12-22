"""
Chaos scheduler - determines when and what failures to inject.
"""

import random
import time
import logging
from pathlib import Path
from typing import Callable, List, Tuple

logger = logging.getLogger(__name__)


class ChaosScheduler:
    """
    Schedules chaos events with configurable intervals and probabilities.
    """

    def __init__(self, interval: int = 180):
        """
        Initialize the chaos scheduler.

        Args:
            interval: Seconds between chaos events (default: 180 = 3 minutes)
        """
        self.interval = interval
        self.last_injection_time = None

        logger.info(f"Chaos Scheduler initialized with {interval}s interval")

    def should_inject_chaos(self) -> bool:
        """
        Determine if it's time to inject chaos based on the interval.

        Returns:
            True if enough time has passed since last injection
        """
        current_time = time.time()

        if self.last_injection_time is None:
            return True

        elapsed = current_time - self.last_injection_time
        return elapsed >= self.interval

    def select_scenario(self, scenarios: List[Tuple[str, float, Callable]]) -> Tuple[str, Callable]:
        """
        Randomly select a chaos scenario based on weighted probabilities.

        Args:
            scenarios: List of (name, weight, function) tuples

        Returns:
            Tuple of (scenario_name, scenario_function)
        """
        names, weights, functions = zip(*scenarios)

        # Use random.choices for weighted selection
        selected_function = random.choices(functions, weights=weights, k=1)[0]
        selected_name = names[functions.index(selected_function)]

        logger.info(f"Selected scenario: {selected_name}")
        return selected_name, selected_function

    def mark_injection(self):
        """Mark that a chaos injection has occurred."""
        self.last_injection_time = time.time()
        logger.debug(f"Marked injection at {self.last_injection_time}")

    def wait_for_next_cycle(self):
        """Sleep until the next chaos cycle."""
        logger.info(f"Waiting {self.interval}s until next chaos cycle...")
        time.sleep(self.interval)
