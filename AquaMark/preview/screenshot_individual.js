const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
  });

  const screens = [
    { name: 'onboarding', index: 0 },
    { name: 'home', index: 1 },
    { name: 'photo_editor', index: 2 },
    { name: 'video_editor', index: 3 },
    { name: 'pro_paywall', index: 4 },
    { name: 'settings', index: 5 },
  ];

  for (const screen of screens) {
    const page = await browser.newPage();
    await page.setViewport({ width: 380, height: 780, deviceScaleFactor: 2 });

    const htmlPath = path.resolve(__dirname, 'all_screens.html');
    await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise(r => setTimeout(r, 800));

    const phones = await page.$$('.iphone');
    if (phones[screen.index]) {
      await phones[screen.index].screenshot({
        path: path.resolve('/opt/cursor/artifacts/screenshots', `${screen.name}.png`),
      });
      console.log(`Saved: ${screen.name}.png`);
    }
    await page.close();
  }

  await browser.close();
  console.log('All individual screenshots done.');
})();
