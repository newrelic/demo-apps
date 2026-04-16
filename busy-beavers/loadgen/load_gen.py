#!/usr/bin/env python3
"""
Busy Beavers Selenium Load Generator

Drives continuous traffic against the frontend UI:
- 97% normal transactions (click the Busy Beaver button)
- 2%  null rage-clicks  (rapid clicks on the no-op button)
- 1%  intentional error (click the Error button)

Targets ~20 transactions/minute with 2 concurrent user threads
and a 6-second base interval (± jitter).
"""

import logging
import os
import random
import sys
import time
from threading import Thread

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://frontend:5000')
USERS = int(os.getenv('LOADGEN_USERS', '2'))
INTERVAL = float(os.getenv('LOADGEN_INTERVAL', '6'))

# Journey weights (must sum to 100)
WEIGHTS = [
    ('transaction', 97),
    ('null',        2),
    ('error',       1),
]


def create_driver() -> webdriver.Chrome:
    """Create a headless Chromium driver using the apt-installed binaries."""
    options = Options()
    options.binary_location = '/usr/bin/chromium'
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1280,800')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument(
        '--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    # Disable images for speed
    options.add_experimental_option('prefs', {
        'profile.default_content_setting_values': {'images': 2}
    })
    service = Service('/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver


def pick_action() -> str:
    """Pick a button action based on configured weights."""
    total = sum(w for _, w in WEIGHTS)
    r = random.uniform(0, total)
    cumulative = 0
    for action, weight in WEIGHTS:
        cumulative += weight
        if r <= cumulative:
            return action
    return WEIGHTS[0][0]


def do_transaction(driver: webdriver.Chrome, action: str) -> None:
    """
    Load the frontend, wait for the target button, and click it.
    For the 'null' action, simulate rage-clicking (5-8 rapid clicks).
    """
    driver.get(FRONTEND_URL)

    # Wait for the page to render the action buttons
    button_id = {
        'transaction': 'btn-transaction',
        'error':       'btn-error',
        'null':        'btn-null',
    }[action]

    try:
        btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, button_id))
        )
    except TimeoutException:
        logger.error("Timed out waiting for button: id=%s", button_id)
        return

    if action == 'null':
        # Rage-click: 5-8 rapid clicks with no UI feedback expected
        clicks = random.randint(5, 8)
        logger.info("Rage-clicking null button: clicks=%d", clicks)
        for i in range(clicks):
            try:
                btn.click()
                time.sleep(random.uniform(0.08, 0.18))
            except WebDriverException:
                break
    else:
        btn.click()
        logger.info("Clicked button: action=%s", action)

    # Brief pause to let the fetch response settle
    time.sleep(random.uniform(0.5, 1.5))


def run_user(user_id: int) -> None:
    """Continuously generate load for one simulated user."""
    logger.info("User %d starting", user_id)

    while True:
        driver = None
        try:
            driver = create_driver()
            action = pick_action()
            logger.info("User %d: starting action=%s", user_id, action)
            start = time.time()
            do_transaction(driver, action)
            elapsed = round(time.time() - start, 2)
            logger.info("User %d: completed action=%s elapsed_s=%s", user_id, action, elapsed)
        except Exception as exc:
            logger.error("User %d: journey failed error=%s", user_id, exc)
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        sleep = INTERVAL + random.uniform(-1.5, 1.5)
        logger.debug("User %d: sleeping %.1fs before next action", user_id, sleep)
        time.sleep(max(2, sleep))


def wait_for_frontend() -> bool:
    """Block until the frontend /health endpoint responds 200."""
    logger.info("Waiting for frontend at %s ...", FRONTEND_URL)
    for attempt in range(60):
        try:
            resp = requests.get(f"{FRONTEND_URL}/health", timeout=5)
            if resp.status_code == 200:
                logger.info("Frontend is ready")
                return True
        except Exception:
            pass
        time.sleep(3)
    logger.error("Frontend did not become available after 60 attempts")
    return False


def main() -> None:
    logger.info("=" * 60)
    logger.info("Busy Beavers Load Generator")
    logger.info("Frontend : %s", FRONTEND_URL)
    logger.info("Users    : %d", USERS)
    logger.info("Interval : %.1fs (± 1.5s jitter)", INTERVAL)
    logger.info("Weights  : %s", WEIGHTS)
    logger.info("=" * 60)

    if not wait_for_frontend():
        sys.exit(1)

    logger.info("Stabilisation pause: 5s")
    time.sleep(5)

    threads = []
    for uid in range(1, USERS + 1):
        t = Thread(target=run_user, args=(uid,), daemon=True)
        t.start()
        threads.append(t)
        logger.info("Started user thread %d", uid)
        time.sleep(2)  # stagger starts

    logger.info("All %d users active — generating continuous load", USERS)
    try:
        while True:
            time.sleep(60)
            logger.info("Load generator heartbeat: %d users active", USERS)
    except KeyboardInterrupt:
        logger.info("Shutting down load generator")
        sys.exit(0)


if __name__ == '__main__':
    main()
