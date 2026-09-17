import { By, until } from 'selenium-webdriver';

const WAIT_TIMEOUT = 10000;
const SEARCH_TERMS = ['nova', 'storm', 'ace', ''];

async function run(driver, url) {
  await driver.get(url);
  await driver.wait(until.elementLocated(By.css('.leaderboard-row')), WAIT_TIMEOUT);

  const term = SEARCH_TERMS[Math.floor(Math.random() * SEARCH_TERMS.length)];
  if (term) {
    const search = await driver.findElement(By.id('leaderboard-search'));
    await search.sendKeys(term);
    await driver.sleep(300 + Math.random() * 500);
  }

  const rows = await driver.findElements(By.css('.leaderboard-row'));
  for (let i = 0; i < Math.min(2, rows.length); i++) {
    try {
      const target = rows[Math.floor(Math.random() * rows.length)];
      await target.click();
    } catch {
      // the row list may have re-rendered after filtering -- skip a stale click
    }
    await driver.sleep(200 + Math.random() * 400);
  }

  if (Math.random() < 0.4) {
    try {
      const refreshBtn = await driver.findElement(By.id('refresh-rankings-btn'));
      await refreshBtn.click();
    } catch {
      // the click may trigger the purposeful uncaught error -- that's expected
    }
  }

  await driver.sleep(400);
}

export default { name: 'browse-leaderboard', weight: 3, run };
