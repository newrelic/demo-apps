import http from 'node:http';
import { Builder } from 'selenium-webdriver';
import chrome from 'selenium-webdriver/chrome.js';
import users from './users.js';
import browseLeaderboard from './journeys/browse-leaderboard.js';
import viewProfileRedeem from './journeys/view-profile-redeem.js';
import profileInvalidCodeError from './journeys/profile-invalid-code-error.js';
import appError from './journeys/app-error.js';
import quickBounce from './journeys/quick-bounce.js';
// mfe-collision-demo.js is deliberately not imported/run here -- the id/name
// collision warnings it triggers are demo-only noise best driven by a human
// clicking "Simulate Misconfigured MFE" on purpose, not by unattended,
// continuous loadgen traffic. The journey file is kept for posterity/future
// use; see README.md > "id/name collision warnings".

const journeys = [
  browseLeaderboard,
  viewProfileRedeem,
  profileInvalidCodeError,
  appError,
  quickBounce,
];

// Session Replay recordings are more useful the longer a page stays open and
// active, so journeys hold the tab open for at least this long before
// quitting the driver (unless they declare a shorter minDurationMs, like
// quick-bounce's intentionally fast bounce).
const DEFAULT_MIN_JOURNEY_DURATION_MS = 45000;

const SHELL_URL = process.env.SHELL_URL || 'http://shell:80';
const LOADGEN_USERS = Math.min(parseInt(process.env.LOADGEN_USERS || '3', 10), users.length);
const INTERVAL_MS = parseInt(process.env.LOADGEN_INTERVAL_MS || '15000', 10);

let shuttingDown = false;
process.on('SIGTERM', () => {
  shuttingDown = true;
});
process.on('SIGINT', () => {
  shuttingDown = true;
});

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function pickJourney() {
  const total = journeys.reduce((sum, j) => sum + j.weight, 0);
  let r = Math.random() * total;
  for (const journey of journeys) {
    if (r < journey.weight) return journey;
    r -= journey.weight;
  }
  return journeys[journeys.length - 1];
}

async function createDriver() {
  const options = new chrome.Options();
  options.addArguments('--headless');
  options.addArguments('--no-sandbox');
  options.addArguments('--disable-dev-shm-usage');
  options.addArguments('--disable-gpu');
  options.addArguments('--window-size=1280,800');

  return new Builder().forBrowser('chrome').setChromeOptions(options).build();
}

function waitForShell(url, retriesRemaining) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, (res) => {
      res.resume();
      resolve();
    });
    req.on('error', () => {
      if (retriesRemaining <= 0) {
        reject(new Error(`shell at ${url} never became reachable`));
        return;
      }
      setTimeout(() => waitForShell(url, retriesRemaining - 1).then(resolve, reject), 2000);
    });
  });
}

async function runVirtualUser(profile, index) {
  while (!shuttingDown) {
    const journey = pickJourney();
    const url = `${SHELL_URL}/?uid=${encodeURIComponent(profile.userId)}&ver=${encodeURIComponent(
      profile.appVersion
    )}`;
    let driver;

    try {
      console.log(`[loadgen ${index}] ${profile.userId} (${profile.appVersion}) -> ${journey.name}`);
      driver = await createDriver();
      const journeyStart = Date.now();
      await journey.run(driver, url);

      const minDurationMs = journey.minDurationMs ?? DEFAULT_MIN_JOURNEY_DURATION_MS;
      const remaining = minDurationMs - (Date.now() - journeyStart);
      if (remaining > 0) await sleep(remaining);
    } catch (err) {
      console.error(`[loadgen ${index}] journey "${journey.name}" failed:`, err.message);
    } finally {
      if (driver) await driver.quit().catch(() => {});
    }

    const jitter = Math.floor(Math.random() * 0.4 * INTERVAL_MS);
    await sleep(INTERVAL_MS + jitter);
  }
}

async function main() {
  console.log(`Waiting for shell at ${SHELL_URL} ...`);
  await waitForShell(SHELL_URL, 30);
  console.log('Shell is reachable. Starting virtual users...');

  const activeProfiles = [...users].sort(() => Math.random() - 0.5).slice(0, LOADGEN_USERS);

  await Promise.all(activeProfiles.map((profile, i) => runVirtualUser(profile, i)));
}

main().catch((err) => {
  console.error('Fatal load generator error:', err);
  process.exit(1);
});
