import { By, until } from 'selenium-webdriver';

const WAIT_TIMEOUT = 10000;

async function run(driver, url) {
  await driver.get(url);
  await driver.wait(until.elementLocated(By.id('simulate-app-error-btn')), WAIT_TIMEOUT);

  await driver.findElement(By.id('simulate-app-error-btn')).click();
  await driver.sleep(400);
}

export default { name: 'app-error', weight: 2, run };
