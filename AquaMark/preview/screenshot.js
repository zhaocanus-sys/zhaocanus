const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--font-render-hinting=none'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 2000, height: 800, deviceScaleFactor: 2 });

  const htmlPath = path.resolve(__dirname, 'all_screens.html');
  await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0', timeout: 15000 });

  await new Promise(r => setTimeout(r, 1500));

  await page.screenshot({
    path: path.resolve(__dirname, 'aquamark_all_screens.png'),
    fullPage: true,
  });

  console.log('Screenshot saved: aquamark_all_screens.png');
  await browser.close();
})();
