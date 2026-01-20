/**
 * Happy Path Scenario
 *
 * User successfully completes a purchase:
 * 1. Select a backend variant
 * 2. Add products to cart
 * 3. Proceed to checkout
 * 4. Complete order
 *
 * Expected: Successful order with distributed trace through all services
 */
import { By, until } from 'selenium-webdriver';

const WAIT_TIMEOUT = 15000;

async function happyPathScenario(driver, storefrontUrl) {
  console.log('  → Loading storefront');
  await driver.get(storefrontUrl);

  // Wait for page to load
  await driver.wait(until.elementLocated(By.css('.app')), WAIT_TIMEOUT);

  // Select a backend variant (rotate through variants)
  const variants = ['apm', 'otel', 'hybrid'];
  const variant = variants[Math.floor(Math.random() * variants.length)];

  console.log(`  → Selecting variant: ${variant}`);
  const variantSelect = await driver.findElement(By.id('variant-select'));
  await variantSelect.sendKeys(variant);

  // Add laptop to cart
  console.log('  → Adding Gaming Laptop to cart');
  const laptopButton = await driver.wait(
    until.elementLocated(By.id('add-to-cart-LAPTOP-001')),
    WAIT_TIMEOUT
  );
  await laptopButton.click();

  // Wait a moment
  await driver.sleep(500);

  // Add mouse to cart
  console.log('  → Adding Wireless Mouse to cart');
  const mouseButton = await driver.findElement(By.id('add-to-cart-MOUSE-001'));
  await mouseButton.click();

  // Wait a moment
  await driver.sleep(500);

  // Proceed to checkout
  console.log('  → Proceeding to checkout');
  const checkoutButton = await driver.wait(
    until.elementLocated(By.id('proceed-to-checkout')),
    WAIT_TIMEOUT
  );
  await checkoutButton.click();

  // Fill in customer ID
  console.log('  → Filling checkout form');
  const customerIdInput = await driver.wait(
    until.elementLocated(By.id('customer-id')),
    WAIT_TIMEOUT
  );
  await customerIdInput.sendKeys(`CUST-${Date.now()}`);

  // Select payment method
  const paymentMethodSelect = await driver.findElement(By.id('payment-method'));
  await paymentMethodSelect.sendKeys('credit-card');

  // Complete order
  console.log('  → Completing order (this will take ~2s due to payment delay)');
  const completeButton = await driver.findElement(By.id('complete-order'));
  await completeButton.click();

  // Wait for order to complete (payment has 2s delay)
  await driver.wait(
    until.elementLocated(By.css('.notification-success')),
    10000
  );

  console.log('  → Order completed successfully!');

  // Wait a moment to see the success message
  await driver.sleep(2000);
}

export default happyPathScenario;
