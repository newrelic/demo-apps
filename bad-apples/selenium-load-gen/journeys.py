from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from faker import Faker
import time
import random
import logging

logger = logging.getLogger(__name__)
fake = Faker()


def journey_browse_and_order(driver, frontend_url):
    """
    Journey 1: Browse catalog and place an order (70% of traffic)

    Flow:
    1. Visit homepage
    2. Browse catalog
    3. Add 2-3 items to cart
    4. Proceed to checkout
    5. Fill form and submit order

    This triggers all three problems:
    - Problem 1 (N+1): Homepage fetches recent orders
    - Problem 2 (Silent errors): Stock validation logs errors but doesn't fail
    - Problem 3 (Rage clicks): Multiple rapid clicks on unresponsive submit button
    """
    try:
        logger.info("Starting journey: Browse and Order")

        # Step 1: Visit homepage
        driver.get(frontend_url)
        logger.info(f"Loaded homepage: {frontend_url}")
        time.sleep(random.uniform(1, 3))

        # Step 2: Navigate to catalog
        try:
            catalog_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "view-catalog"))
            )
            catalog_button.click()
            logger.info("Navigated to catalog page")
            time.sleep(random.uniform(2, 4))
        except TimeoutException:
            # Try direct navigation if button not found
            driver.get(f"{frontend_url}/catalog")
            time.sleep(3)  # Extra wait for direct navigation

        # Extra wait to ensure JavaScript and all buttons are fully loaded
        time.sleep(1)

        # Step 3: Add 2-3 items to cart
        num_items = random.randint(2, 3)
        logger.info(f"Attempting to add {num_items} items to cart")

        try:
            # Wait longer and ensure elements are visible, not just present
            add_to_cart_buttons = WebDriverWait(driver, 15).until(
                EC.visibility_of_all_elements_located((By.CLASS_NAME, "add-to-cart-btn"))
            )

            # Select random items
            selected_buttons = random.sample(
                add_to_cart_buttons,
                min(num_items, len(add_to_cart_buttons))
            )

            for button in selected_buttons:
                try:
                    # Set random quantity (0.5 to 5.0 lbs)
                    variety_id = button.get_attribute('data-variety-id')
                    variety_name = button.get_attribute('data-variety-name')

                    quantity_input = driver.find_element(By.ID, f"qty-{variety_id}")
                    quantity = round(random.uniform(0.5, 5.0), 1)
                    quantity_input.clear()
                    quantity_input.send_keys(str(quantity))

                    # Click add to cart
                    button.click()
                    logger.info(f"Added {quantity}lbs of {variety_name} to cart")
                    time.sleep(random.uniform(0.5, 1.5))
                except Exception as e:
                    logger.warning(f"Failed to add item to cart: {e}")
                    continue

        except TimeoutException:
            logger.error("Could not find add to cart buttons")
            return

        # Step 4: Navigate to checkout
        try:
            driver.get(f"{frontend_url}/checkout")
            logger.info("Navigated to checkout page")
            time.sleep(random.uniform(1, 2))
        except Exception as e:
            logger.error(f"Failed to navigate to checkout: {e}")
            return

        # Step 5: Fill out checkout form and submit
        try:
            # Fill customer information
            name_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "customer_name"))
            )
            name_field.send_keys(fake.name())

            email_field = driver.find_element(By.ID, "customer_email")
            email_field.send_keys(fake.email())

            phone_field = driver.find_element(By.ID, "customer_phone")
            phone_field.send_keys(fake.phone_number())

            address_field = driver.find_element(By.ID, "delivery_address")
            address_field.send_keys(fake.address())

            logger.info("Filled checkout form")
            time.sleep(random.uniform(1, 2))

            # ================================================================
            # PROBLEM 3: RAGE CLICKS
            # ================================================================
            # The submit button has no feedback and a 4-second delay
            # Simulating a frustrated user who clicks multiple times rapidly
            # because they think their first click didn't register
            # Target: >10 clicks in 2-3 seconds to trigger New Relic threshold
            # ================================================================
            submit_button = driver.find_element(By.ID, "submit-order")

            # First click (intentional)
            submit_button.click()
            logger.info("Clicked submit button (attempt 1)")

            # User waits a brief moment, sees no feedback, starts rage clicking
            time.sleep(random.uniform(0.2, 0.3))

            # Rage clicks: 10-15 rapid clicks in 2-3 seconds
            rage_clicks = random.randint(10, 15)
            for i in range(rage_clicks):
                try:
                    submit_button.click()
                    logger.info(f"Rage click {i+1}/{rage_clicks} - no feedback from button!")
                    # Very short delay between clicks (0.1-0.2s)
                    time.sleep(random.uniform(0.1, 0.2))
                except Exception as e:
                    # Button might become stale or page might transition
                    logger.debug(f"Rage click failed (page may have transitioned): {e}")
                    break

            logger.info(f"Total clicks on submit button: {rage_clicks + 1} (simulating user frustration)")

            # Wait for the 4-second delay to complete and order to process
            time.sleep(random.uniform(4, 6))

            logger.info("Journey completed: Browse and Order")

        except Exception as e:
            logger.error(f"Failed to complete checkout: {e}")
            return

    except Exception as e:
        logger.error(f"Journey failed (Browse and Order): {e}")


def journey_quick_browse(driver, frontend_url):
    """
    Journey 2: Quick browse without ordering (30% of traffic)

    Flow:
    1. Visit homepage
    2. Browse catalog
    3. View 1-3 product details
    4. Exit

    This triggers:
    - Problem 1 (N+1): Homepage fetches recent orders
    """
    try:
        logger.info("Starting journey: Quick Browse")

        # Step 1: Visit homepage
        driver.get(frontend_url)
        logger.info(f"Loaded homepage: {frontend_url}")
        time.sleep(random.uniform(1, 2))

        # Step 2: Navigate to catalog
        try:
            driver.get(f"{frontend_url}/catalog")
            logger.info("Navigated to catalog page")
            time.sleep(random.uniform(3, 6))
        except Exception as e:
            logger.error(f"Failed to load catalog: {e}")
            return

        # Step 3: View random product details
        num_products = random.randint(1, 3)
        logger.info(f"Viewing {num_products} product details")

        try:
            variety_links = driver.find_elements(By.CLASS_NAME, "variety-link")

            if variety_links:
                selected_links = random.sample(
                    variety_links,
                    min(num_products, len(variety_links))
                )

                for link in selected_links:
                    try:
                        variety_name = link.get_attribute('data-variety-name')
                        link.click()
                        logger.info(f"Viewing product: {variety_name}")
                        time.sleep(random.uniform(2, 4))

                        # Go back to catalog
                        driver.back()
                        time.sleep(random.uniform(1, 2))
                    except Exception as e:
                        logger.warning(f"Failed to view product: {e}")
                        continue

        except Exception as e:
            logger.warning(f"Could not find variety links: {e}")

        logger.info("Journey completed: Quick Browse")

    except Exception as e:
        logger.error(f"Journey failed (Quick Browse): {e}")
