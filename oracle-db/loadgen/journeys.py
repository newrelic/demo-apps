"""
ReliPeople user journeys.

Three weighted journeys simulate typical HR-portal traffic:

    browse_employees (50%) - dashboard -> employee directory -> search
                             -> open 2-3 profiles
    run_report       (30%) - dashboard -> one of (payroll, departments,
                             performance), wait for table to render
    check_leaves     (20%) - navigate to the leave-requests page

Each journey drives the frontend UI via Selenium (no direct backend calls).
Journeys never raise out of the module - timeouts are logged and the journey
moves on so the user thread stays alive.
"""

from __future__ import annotations

import logging
import random
import time
from typing import List, Tuple

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

# Journey weights (must sum to 100)
JOURNEY_WEIGHTS: List[Tuple[str, int]] = [
    ("browse_employees", 50),
    ("run_report",       30),
    ("check_leaves",     20),
]

# Two-letter name fragments - match common first/last name prefixes in the
# seeded data so searches return meaningful result sets.
SEARCH_FRAGMENTS = [
    "Sm", "Jo", "Wi", "Br", "Da", "Ja", "Ma", "Mi", "Ro", "An",
    "Al", "Ch", "Ga", "He", "Ki", "Le", "Mo", "Pa", "Ri", "Th",
]

REPORT_PATHS = [
    "/reports/payroll",
    "/reports/departments",
    "/reports/performance",
    "/reports/leave-backlog",
    "/reports/salary-progression",
]

DEFAULT_WAIT_S = 15
REPORT_WAIT_S = 60  # payroll query can legitimately take 10-30s


def pick_journey() -> str:
    """Pick a journey name using weighted random selection (50/30/20)."""
    total = sum(w for _, w in JOURNEY_WEIGHTS)
    r = random.uniform(0, total)
    cumulative = 0
    for name, weight in JOURNEY_WEIGHTS:
        cumulative += weight
        if r <= cumulative:
            return name
    return JOURNEY_WEIGHTS[0][0]


def _wait_for_body(driver: WebDriver, timeout: int = DEFAULT_WAIT_S) -> None:
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
    except TimeoutException:
        logger.warning("Body tag never appeared within %ds", timeout)


def journey_browse_employees(driver: WebDriver, frontend_url: str) -> None:
    """Dashboard -> employee directory -> search -> open 2-3 profiles."""
    driver.get(frontend_url + "/")
    _wait_for_body(driver)
    time.sleep(random.uniform(0.6, 1.2))

    driver.get(frontend_url + "/employees")
    _wait_for_body(driver)

    term = random.choice(SEARCH_FRAGMENTS)
    try:
        search_input = WebDriverWait(driver, DEFAULT_WAIT_S).until(
            EC.presence_of_element_located((By.ID, "search-input"))
        )
        search_input.clear()
        search_input.send_keys(term)
        logger.info("browse_employees: searching term=%s", term)
    except TimeoutException:
        logger.info("browse_employees: search input not found, skipping search")
        term = None

    if term is not None:
        try:
            btn = WebDriverWait(driver, DEFAULT_WAIT_S).until(
                EC.element_to_be_clickable((By.ID, "search-btn"))
            )
            btn.click()
        except TimeoutException:
            logger.info("browse_employees: search button not clickable")

        _wait_for_body(driver)
        time.sleep(random.uniform(1.0, 2.0))

    # Collect profile links then visit 2-3 of them.
    profile_hrefs: List[str] = []
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "a.emp-link")
        for link in links:
            try:
                href = link.get_attribute("href")
                if href:
                    profile_hrefs.append(href)
            except StaleElementReferenceException:
                continue
    except WebDriverException as exc:
        logger.debug("browse_employees: error collecting links: %s", exc)

    if not profile_hrefs:
        logger.info("browse_employees: no profile links found on page")
        return

    sample_n = min(len(profile_hrefs), random.randint(2, 3))
    for href in random.sample(profile_hrefs, sample_n):
        try:
            driver.get(href)
            _wait_for_body(driver)
            time.sleep(random.uniform(0.8, 1.6))
            logger.info("browse_employees: viewed profile=%s", href)
        except WebDriverException as exc:
            logger.debug("browse_employees: failed to load profile %s: %s", href, exc)


def journey_run_report(driver: WebDriver, frontend_url: str) -> None:
    """Dashboard briefly -> one random report -> wait for table to render."""
    driver.get(frontend_url + "/")
    _wait_for_body(driver)
    time.sleep(random.uniform(0.5, 1.0))

    path = random.choice(REPORT_PATHS)
    logger.info("run_report: loading %s", path)
    driver.get(frontend_url + path)

    try:
        WebDriverWait(driver, REPORT_WAIT_S).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        logger.info("run_report: table rendered for %s", path)
    except TimeoutException:
        logger.warning("run_report: table never rendered for %s within %ds",
                       path, REPORT_WAIT_S)

    time.sleep(random.uniform(0.8, 1.6))


def journey_check_leaves(driver: WebDriver, frontend_url: str) -> None:
    """Navigate to the leave-requests page and wait for it to render."""
    driver.get(frontend_url + "/leaves")
    _wait_for_body(driver)

    try:
        WebDriverWait(driver, DEFAULT_WAIT_S).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
    except TimeoutException:
        logger.info("check_leaves: heading never appeared")

    time.sleep(random.uniform(0.8, 1.6))
    logger.info("check_leaves: completed")


JOURNEYS = {
    "browse_employees": journey_browse_employees,
    "run_report":       journey_run_report,
    "check_leaves":     journey_check_leaves,
}


def run_journey(name: str, driver: WebDriver, frontend_url: str) -> None:
    """Dispatch by journey name - raises KeyError on unknown journey."""
    JOURNEYS[name](driver, frontend_url)
