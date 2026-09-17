async function run(driver, url) {
  await driver.get(url);
  await driver.sleep(300 + Math.random() * 700);
}

export default { name: 'quick-bounce', weight: 1, run };
