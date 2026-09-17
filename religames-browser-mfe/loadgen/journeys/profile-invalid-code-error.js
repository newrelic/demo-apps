import { By, until } from 'selenium-webdriver';

const WAIT_TIMEOUT = 10000;

async function run(driver, url) {
  await driver.get(url);
  await driver.wait(until.elementLocated(By.id('profile-toggle-btn')), WAIT_TIMEOUT);

  await driver.findElement(By.id('profile-toggle-btn')).click();
  await driver.wait(until.elementLocated(By.id('redeem-form')), WAIT_TIMEOUT);

  await driver.findElement(By.id('redeem-code')).sendKeys('BOGUSCODE');
  await driver.findElement(By.css('#redeem-form button[type="submit"]')).click();
  await driver.sleep(400);

  await driver.findElement(By.id('profile-toggle-btn')).click();
  await driver.sleep(300);
}

export default { name: 'profile-invalid-code-error', weight: 2, run };
