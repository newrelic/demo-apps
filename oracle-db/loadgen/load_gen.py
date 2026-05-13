#!/usr/bin/env python3
"""
ReliPeople Selenium Load Generator

Drives continuous traffic against the frontend UI with three weighted journeys:

    browse_employees (50%) - dashboard + employee directory + profile lookup
    run_report       (30%) - payroll / departments / performance reports
    check_leaves     (20%) - leave-request listing

One Chromium session per iteration, recycled after each journey (matches the
busy-beavers pattern - keeps iterations isolated and avoids state drift).
Defaults: 2 concurrent users, ~8s per iteration.
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

from journeys import JOURNEY_WEIGHTS, pick_journey, run_journey

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("relipeople.loadgen")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://frontend:8080")
USERS = int(os.getenv("LOADGEN_USERS", "2"))
INTERVAL = float(os.getenv("LOADGEN_INTERVAL", "8"))
APP_NAME = os.getenv("NEW_RELIC_APP_NAME", "ReliPeople")


def create_driver() -> webdriver.Chrome:
    """Create a headless Chromium driver using the apt-installed binaries."""
    options = Options()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    options.add_experimental_option(
        "prefs",
        {"profile.default_content_setting_values": {"images": 2}},
    )
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    # Reports can take 30s+, so give pages a wide page-load budget.
    driver.set_page_load_timeout(90)
    return driver


def wait_for_frontend() -> bool:
    """Block until the frontend /health endpoint responds 200."""
    logger.info("Waiting for frontend at %s ...", FRONTEND_URL)
    for attempt in range(80):
        try:
            resp = requests.get(f"{FRONTEND_URL}/health", timeout=5)
            if resp.status_code == 200:
                logger.info("Frontend is ready (attempt %d)", attempt + 1)
                return True
        except Exception:
            pass
        time.sleep(5)
    logger.error("Frontend did not become available after 80 attempts")
    return False


def run_user(user_id: int) -> None:
    """Continuously generate load for one simulated user."""
    logger.info("User %d starting", user_id)

    while True:
        driver = None
        journey = pick_journey()
        start = time.time()
        try:
            driver = create_driver()
            logger.info("User %d: starting journey=%s", user_id, journey)
            run_journey(journey, driver, FRONTEND_URL)
            elapsed = round(time.time() - start, 2)
            logger.info(
                "User %d: completed journey=%s elapsed_s=%s",
                user_id, journey, elapsed,
            )
        except Exception as exc:
            elapsed = round(time.time() - start, 2)
            logger.error(
                "User %d: journey=%s failed elapsed_s=%s error=%s",
                user_id, journey, elapsed, exc,
            )
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        sleep_s = INTERVAL + random.uniform(-1.5, 1.5)
        time.sleep(max(2, sleep_s))


def main() -> None:
    logger.info("=" * 60)
    logger.info("%s Load Generator", APP_NAME)
    logger.info("Frontend : %s", FRONTEND_URL)
    logger.info("Users    : %d", USERS)
    logger.info("Interval : %.1fs (+/- 1.5s jitter)", INTERVAL)
    logger.info("Journeys : %s", JOURNEY_WEIGHTS)
    logger.info("=" * 60)

    if not wait_for_frontend():
        sys.exit(1)

    logger.info("Stabilisation pause: 10s")
    time.sleep(10)

    threads = []
    for uid in range(1, USERS + 1):
        t = Thread(target=run_user, args=(uid,), daemon=True)
        t.start()
        threads.append(t)
        logger.info("Started user thread %d", uid)
        time.sleep(2)  # stagger starts

    logger.info("All %d users active - generating continuous load", USERS)
    try:
        while True:
            time.sleep(60)
            logger.info("Load generator heartbeat: %d users active", USERS)
    except KeyboardInterrupt:
        logger.info("Shutting down load generator")
        sys.exit(0)


if __name__ == "__main__":
    main()
