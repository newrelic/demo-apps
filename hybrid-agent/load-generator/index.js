/**
 * Load Generator for Hybrid Agent Demo
 *
 * Runs Selenium scenarios to generate traffic and distributed traces
 */
import { Builder } from 'selenium-webdriver';
import chrome from 'selenium-webdriver/chrome.js';
import happyPathScenario from './scenarios/happy-path.js';
import outOfStockScenario from './scenarios/out-of-stock.js';
import slowPaymentScenario from './scenarios/slow-payment.js';

const STOREFRONT_URL = process.env.STOREFRONT_URL || 'http://storefront:80';
const SCENARIO_INTERVAL_MS = parseInt(process.env.SCENARIO_INTERVAL_MS) || 30000; // 30 seconds
const SCENARIOS_TO_RUN = process.env.SCENARIOS || 'happy-path,out-of-stock,slow-payment';

const scenarios = {
  'happy-path': happyPathScenario,
  'out-of-stock': outOfStockScenario,
  'slow-payment': slowPaymentScenario
};

/**
 * Create a Selenium WebDriver instance
 */
async function createDriver() {
  const chromeOptions = new chrome.Options();
  chromeOptions.addArguments('--headless');
  chromeOptions.addArguments('--no-sandbox');
  chromeOptions.addArguments('--disable-dev-shm-usage');
  chromeOptions.addArguments('--disable-gpu');
  chromeOptions.addArguments('--window-size=1920,1080');

  const driver = await new Builder()
    .forBrowser('chrome')
    .setChromeOptions(chromeOptions)
    .build();

  return driver;
}

/**
 * Run a single scenario
 */
async function runScenario(scenarioName, scenarioFn) {
  let driver;

  try {
    console.log(`[Load Generator] Starting scenario: ${scenarioName}`);
    const startTime = Date.now();

    driver = await createDriver();
    await scenarioFn(driver, STOREFRONT_URL);

    const duration = Date.now() - startTime;
    console.log(`[Load Generator] ✓ Scenario completed: ${scenarioName} (${duration}ms)`);

  } catch (error) {
    console.error(`[Load Generator] ✗ Scenario failed: ${scenarioName}`, error.message);
  } finally {
    if (driver) {
      await driver.quit();
    }
  }
}

/**
 * Main orchestrator - runs scenarios in rotation
 */
async function main() {
  console.log('[Load Generator] Starting...');
  console.log(`[Load Generator] Storefront URL: ${STOREFRONT_URL}`);
  console.log(`[Load Generator] Scenario interval: ${SCENARIO_INTERVAL_MS}ms`);

  const enabledScenarios = SCENARIOS_TO_RUN.split(',')
    .map(s => s.trim())
    .filter(s => scenarios[s]);

  if (enabledScenarios.length === 0) {
    console.error('[Load Generator] No valid scenarios configured');
    process.exit(1);
  }

  console.log(`[Load Generator] Enabled scenarios: ${enabledScenarios.join(', ')}`);

  // Wait a bit for services to be ready
  console.log('[Load Generator] Waiting 10s for services to be ready...');
  await new Promise(resolve => setTimeout(resolve, 10000));

  let scenarioIndex = 0;

  while (true) {
    const scenarioName = enabledScenarios[scenarioIndex];
    const scenarioFn = scenarios[scenarioName];

    await runScenario(scenarioName, scenarioFn);

    // Move to next scenario
    scenarioIndex = (scenarioIndex + 1) % enabledScenarios.length;

    // Wait before next run
    console.log(`[Load Generator] Waiting ${SCENARIO_INTERVAL_MS}ms before next scenario...`);
    await new Promise(resolve => setTimeout(resolve, SCENARIO_INTERVAL_MS));
  }
}

// Handle shutdown gracefully
process.on('SIGTERM', () => {
  console.log('[Load Generator] Received SIGTERM, shutting down...');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('[Load Generator] Received SIGINT, shutting down...');
  process.exit(0);
});

// Start the load generator
main().catch(error => {
  console.error('[Load Generator] Fatal error:', error);
  process.exit(1);
});
