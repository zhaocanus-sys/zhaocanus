const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1200, height: 1200, deviceScaleFactor: 1 });

  const htmlPath = path.resolve(__dirname, '..', 'generate_icon.html');
  await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 500));

  const canvas = await page.$('canvas');
  if (canvas) {
    await canvas.screenshot({
      path: path.resolve(__dirname, '..', 'AquaMark', 'Resources', 'Assets.xcassets', 'AppIcon.appiconset', 'AppIcon.png'),
    });
    // Also save to artifacts
    await canvas.screenshot({
      path: '/opt/cursor/artifacts/screenshots/app_icon.png',
    });
    console.log('App icon generated!');
  }

  await browser.close();
})();
