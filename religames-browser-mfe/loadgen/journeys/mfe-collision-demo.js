import { By, until } from 'selenium-webdriver';

const WAIT_TIMEOUT = 10000;

async function run(driver, url) {
  await driver.get(url);
  await driver.wait(until.elementLocated(By.id('simulate-mfe-collision-btn')), WAIT_TIMEOUT);

  await driver.findElement(By.id('simulate-mfe-collision-btn')).click();
  // Give the agent a moment to print the id/name collision warnings.
  await driver.sleep(500);
}

export default { name: 'mfe-collision-demo', weight: 1, minDurationMs: 45000, run };
