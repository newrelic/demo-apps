/**
 * Slow Payment Scenario
 *
 * Demonstrates the payment bottleneck:
 * 1. Add multiple expensive items
 * 2. Complete checkout
 * 3. Experience 2-second payment delay
 *
 * Expected: Distributed trace showing payment service as bottleneck
 */
import { By, until } from 'selenium-webdriver';

const WAIT_TIMEOUT = 15000;

async function slowPaymentScenario(driver, storefrontUrl) {
  console.log('  → Loading storefront');
  await driver.get(storefrontUrl);

  // Wait for page to load
  await driver.wait(until.elementLocated(By.css('.app')), WAIT_TIMEOUT);

  // Select OTel variant for this scenario
  console.log('  → Selecting OTel variant');
  const variantSelect = await driver.findElement(By.id('variant-select'));
  await variantSelect.sendKeys('otel');

  // Add expensive items to create a large order
  console.log('  → Adding Gaming Laptop to cart');
  const laptopButton = await driver.findElement(By.id('add-to-cart-LAPTOP-001'));
  await laptopButton.click();
  await driver.sleep(300);

  console.log('  → Adding 4K Monitor to cart');
  const monitorButton = await driver.findElement(By.id('add-to-cart-MONITOR-001'));
  await monitorButton.click();
  await driver.sleep(300);

  console.log('  → Adding Mechanical Keyboard to cart');
  const keyboardButton = await driver.findElement(By.id('add-to-cart-KEYBOARD-001'));
  await keyboardButton.click();
  await driver.sleep(300);

  // Proceed to checkout
  console.log('  → Proceeding to checkout with large order');
  const checkoutButton = await driver.wait(
    until.elementLocated(By.id('proceed-to-checkout')),
    WAIT_TIMEOUT
  );
  await checkoutButton.click();

  // Fill checkout form
  console.log('  → Filling checkout form');
  const customerIdInput = await driver.wait(
    until.elementLocated(By.id('customer-id')),
    WAIT_TIMEOUT
  );
  await customerIdInput.sendKeys(`CUST-SLOW-${Date.now()}`);

  const paymentMethodSelect = await driver.findElement(By.id('payment-method'));
  await paymentMethodSelect.sendKeys('credit-card');

  // Complete order - this will take time due to payment delay
  console.log('  → Completing order (experiencing 2s payment bottleneck)');
  const startTime = Date.now();

  const completeButton = await driver.findElement(By.id('complete-order'));
  await completeButton.click();

  // Wait for completion
  await driver.wait(
    until.elementLocated(By.css('.notification-success, .notification-error')),
    12000
  );

  const duration = Date.now() - startTime;
  console.log(`  → Order completed in ${duration}ms (includes 2s payment delay)`);

  // Wait to see the result
  await driver.sleep(2000);
}

export default slowPaymentScenario;
