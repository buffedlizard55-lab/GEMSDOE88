/* Optional real-browser audit. Dependencies belong in .cache, not the release.
 * npm install --prefix .cache/browser playwright-core@1.64.1 @sparticuz/chromium@153.0.0
 * Run against a local/preview static server using BROWSER_BASE_URL if necessary.
 * This is test automation; the application itself never calls localhost.
 */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const ROOT = path.resolve(__dirname, '..');
const modules = path.join(ROOT, '.cache/browser/node_modules');
const {chromium: playwright} = require(path.join(modules, 'playwright-core'));
const chromium = require(path.join(modules, '@sparticuz/chromium/build/index.js')).default;
const base = process.env.BROWSER_BASE_URL || 'http://127.0.0.1:8000/';
const expected = JSON.parse(fs.readFileSync(path.join(ROOT, 'docs/data/current_release.json'), 'utf8'));
const expectedTiff = expected.file.replace(/^docs\//, '');
const requiredBanner = 'NO FILE APPROVED · ARCHIVED RESEARCH DOWNLOAD: YES · SUBMIT: NO — DO NOT SUBMIT';

(async () => {
  const browser = await playwright.launch({
    executablePath: await chromium.executablePath(),
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
    headless: true,
  });
  const cases = [
    ['index.html', 1440, 1100], ['index.html', 390, 844],
    ['executive-summary.html', 390, 844], ['research.html', 390, 844],
    ['sources.html', 390, 844],
  ];
  const report = {schema: 'gems88.browser-review.v1', checked_at_utc: new Date().toISOString(),
    browser: browser.version(), pages: [], failed_fetch_stays_negative: false,
    source_sha256: {}, ok_to_submit: false};
  let failed = false;
  for (const [name, width, height] of cases) {
    const page = await browser.newPage({viewport: {width, height}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(new URL(name, base).toString(), {waitUntil: 'networkidle'});
    const banners = await page.locator('[data-card-status]').allTextContents();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    const h1 = await page.locator('h1:visible').count();
    const openArchives = await page.locator('details.archive-lanes[open]').count();
    const primary = ['index.html', 'executive-summary.html'].includes(name);
    const firstTiff = primary ? await page.locator('a[download][href$=".tif"]').first().getAttribute('href') : null;
    const pass = !overflow && !errors.length && h1 === 1 && openArchives === 0
      && (!primary || (banners.length === 1 && banners[0] === requiredBanner && firstTiff === expectedTiff));
    report.pages.push({page: name, width, height, banners, overflow, h1, openArchives,
      first_tiff: firstTiff, errors, pass});
    failed ||= !pass;
    await page.screenshot({path: path.join(ROOT, '.cache', `${name.replace('.html', '')}-${width}.png`), fullPage: true});
    await page.close();
  }
  const unavailable = await browser.newPage();
  await unavailable.route('**/data/download_audit.json', route => route.abort());
  await unavailable.goto(new URL('index.html', base).toString(), {waitUntil: 'networkidle'});
  const denied = await unavailable.locator('[data-card-status]').innerText();
  report.failed_fetch_stays_negative = denied === 'PRE-FLIGHT AUDIT UNAVAILABLE — DO NOT SUBMIT';
  failed ||= !report.failed_fetch_stays_negative;
  await unavailable.close();
  await browser.close();
  for (const relative of ['docs/index.html', 'docs/executive-summary.html', 'docs/research.html',
    'docs/sources.html', 'docs/assets/site.css', 'docs/assets/site.js', 'docs/data/current_release.json',
    'docs/data/download_audit.json', 'docs/data/mtas88_run_card.json', 'docs/status.json']) {
    report.source_sha256[relative] = crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT, relative))).digest('hex');
  }
  report.status = failed ? 'FAIL' : 'PASS';
  fs.writeFileSync(path.join(ROOT, '.cache/browser-check.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
  if (failed) process.exitCode = 1;
})().catch(error => { console.error(error); process.exitCode = 1; });
