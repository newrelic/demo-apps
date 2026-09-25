async function run(driver, url) {
  await driver.get(url);
  await driver.sleep(300 + Math.random() * 700);
}

// Deliberately excluded from the 45s Session Replay padding other journeys
// get -- a fast bounce is realistic traffic-mix variety in its own right.
export default { name: 'quick-bounce', weight: 1, minDurationMs: 1000, run };
