import { By, until } from 'selenium-webdriver';

const WAIT_TIMEOUT = 10000;
const VALID_CODES = ['RELIGAMES2026', 'LEVELUP', 'MVPWEEK'];

async function run(driver, url) {
  await driver.get(url);
  await driver.wait(until.elementLocated(By.id('profile-toggle-btn')), WAIT_TIMEOUT);

  await driver.findElement(By.id('profile-toggle-btn')).click();
  await driver.wait(until.elementLocated(By.id('redeem-form')), WAIT_TIMEOUT);

  const matchRows = await driver.findElements(By.css('.match-row'));
  if (matchRows.length) {
    await matchRows[0].click().catch(() => {});
  }

  const email = `${Math.random().toString(36).slice(2, 8)}@example.com`;
  await driver.findElement(By.id('notify-email')).sendKeys(email).catch(() => {});

  const code = VALID_CODES[Math.floor(Math.random() * VALID_CODES.length)];
  await driver.findElement(By.id('redeem-code')).sendKeys(code);
  await driver.findElement(By.css('#redeem-form button[type="submit"]')).click();
  await driver.sleep(400);

  // Close the drawer -- deregisters the Player Profile MFE.
  await driver.findElement(By.id('profile-toggle-btn')).click();
  await driver.sleep(300);
}

export default { name: 'view-profile-redeem', weight: 3, minDurationMs: 45000, run };
