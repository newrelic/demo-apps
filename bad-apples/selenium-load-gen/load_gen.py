#!/usr/bin/env python3
"""
Bad Apples Selenium Load Generator

Continuously generates traffic by simulating real user journeys:
- 70% Browse and Order journey (triggers all 3 problems)
  * Problem 1: N+1 SQL queries on homepage
  * Problem 2: Silent errors from insufficient stock
  * Problem 3: Rage clicks on unresponsive checkout button
- 30% Quick Browse journey (triggers Problem 1 only)

Runs multiple concurrent users to generate realistic load.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import logging
import time
import random
import os
import sys
from threading import Thread

from journeys import journey_browse_and_order, journey_quick_browse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration from environment
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://flask-frontend:5000')
USERS = int(os.getenv('USERS', 3))
REQUEST_INTERVAL = int(os.getenv('REQUEST_INTERVAL', 5))

# Journey weights (70% order, 30% browse)
JOURNEYS = [
    (journey_browse_and_order, 70),
    (journey_quick_browse, 30)
]


def create_driver():
    """Create a Chrome WebDriver with headless options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    # Disable images to speed up page loads
    prefs = {
        'profile.default_content_setting_values': {
            'images': 2
        }
    }
    chrome_options.add_experimental_option('prefs', prefs)

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        logger.error(f"Failed to create Chrome driver: {e}")
        raise


def select_journey():
    """Select a journey based on weights"""
    total_weight = sum(weight for _, weight in JOURNEYS)
    r = random.uniform(0, total_weight)

    cumulative_weight = 0
    for journey_func, weight in JOURNEYS:
        cumulative_weight += weight
        if r <= cumulative_weight:
            return journey_func

    return JOURNEYS[0][0]  # Fallback to first journey


def run_user_session(user_id):
    """
    Run continuous load generation for a single user.
    Each iteration selects a random journey and executes it.
    """
    logger.info(f"User {user_id} starting load generation")

    while True:
        driver = None
        try:
            # Create fresh driver for each iteration
            driver = create_driver()

            # Select and execute journey
            journey = select_journey()
            journey_name = journey.__name__

            logger.info(f"User {user_id}: Starting journey '{journey_name}'")
            start_time = time.time()

            journey(driver, FRONTEND_URL)

            duration = time.time() - start_time
            logger.info(
                f"User {user_id}: Completed journey '{journey_name}' "
                f"in {duration:.2f} seconds"
            )

        except Exception as e:
            logger.error(f"User {user_id}: Journey failed with error: {e}")

        finally:
            # Clean up driver
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    logger.warning(f"User {user_id}: Error closing driver: {e}")

        # Wait before next iteration
        sleep_time = REQUEST_INTERVAL + random.uniform(-1, 1)
        logger.info(f"User {user_id}: Waiting {sleep_time:.1f}s before next journey")
        time.sleep(max(1, sleep_time))


def wait_for_frontend():
    """Wait for frontend to become available before starting load generation"""
    import requests

    max_attempts = 30
    attempt = 0

    logger.info(f"Waiting for frontend at {FRONTEND_URL} to become available...")

    while attempt < max_attempts:
        try:
            response = requests.get(f"{FRONTEND_URL}/health", timeout=5)
            if response.status_code == 200:
                logger.info("Frontend is available, starting load generation")
                return True
        except Exception as e:
            logger.debug(f"Frontend not ready yet: {e}")

        attempt += 1
        time.sleep(2)

    logger.error("Frontend did not become available in time")
    return False


def main():
    """Main entry point for load generator"""
    logger.info("=" * 60)
    logger.info("Bad Apples Selenium Load Generator")
    logger.info("=" * 60)
    logger.info(f"Frontend URL: {FRONTEND_URL}")
    logger.info(f"Concurrent Users: {USERS}")
    logger.info(f"Request Interval: {REQUEST_INTERVAL}s")
    logger.info(f"Journey Distribution: 70% Browse+Order, 30% Quick Browse")
    logger.info("=" * 60)

    # Wait for frontend to be ready
    if not wait_for_frontend():
        logger.error("Exiting due to frontend unavailability")
        sys.exit(1)

    # Give services a bit more time to stabilize
    logger.info("Waiting 10s for services to stabilize...")
    time.sleep(10)

    # Start user threads
    threads = []
    for user_id in range(1, USERS + 1):
        thread = Thread(target=run_user_session, args=(user_id,), daemon=True)
        thread.start()
        threads.append(thread)
        logger.info(f"Started user thread {user_id}")

        # Stagger thread starts
        time.sleep(2)

    logger.info(f"All {USERS} users started, generating continuous load...")

    # Keep main thread alive
    try:
        while True:
            time.sleep(60)
            logger.info(f"Load generator running with {USERS} active users")
    except KeyboardInterrupt:
        logger.info("Shutting down load generator...")
        sys.exit(0)


if __name__ == '__main__':
    main()
