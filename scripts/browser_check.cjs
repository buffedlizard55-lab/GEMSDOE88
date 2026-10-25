/* Optional real-browser audit. Dependencies belong in .cache, not the release.
 * npm install --prefix .cache/browser playwright-core@1.64.1 @sparticuz/chromium@153.0.0
 * Automatically serves docs/ on an ephemeral 127.0.0.1 port when BROWSER_BASE_URL
 * is unset, and closes both browser and server inside try/finally.
 * This is test automation; the application itself never calls localhost.
 */
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const crypto = require('node:crypto');

const ROOT = path.resolve(__dirname, '..');
const DOCS_ROOT = path.join(ROOT, 'docs');
const modules = path.join(ROOT, '.cache/browser/node_modules');
const {chromium: playwright} = require(path.join(modules, 'playwright-core'));
const chromiumPackage = require(path.join(modules, '@sparticuz/chromium/build/index.js'));
const chromium = chromiumPackage.default;
const expected = JSON.parse(fs.readFileSync(path.join(ROOT, 'docs/data/current_release.json'), 'utf8'));
const expectedTiff = expected.file.replace(/^docs\//, '');
const requiredBanner = 'NO FILE APPROVED · ARCHIVED RESEARCH DOWNLOAD: YES · SUBMIT: NO — DO NOT SUBMIT';

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
  '.csv': 'text/csv; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.tif': 'image/tiff',
  '.tiff': 'image/tiff',
  '.zip': 'application/zip',
};

function startEphemeralDocsServer() {
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      try {
        const parsed = new URL(req.url || '/', 'http://127.0.0.1');
        let relPath = decodeURIComponent(parsed.pathname).replace(/^\/+/, '');
        if (!relPath || relPath.endsWith('/')) relPath += 'index.html';
        const resolved = path.resolve(DOCS_ROOT, relPath);
        if (resolved !== DOCS_ROOT && !resolved.startsWith(DOCS_ROOT + path.sep)) {
          res.writeHead(403).end('Forbidden');
          return;
        }
        let target = resolved;
        if (fs.existsSync(target) && fs.statSync(target).isDirectory()) {
          target = path.join(target, 'index.html');
        }
        if (!fs.existsSync(target) || !fs.statSync(target).isFile()) {
          res.writeHead(404).end('Not found');
          return;
        }
        const stat = fs.statSync(target);
        const ext = path.extname(target).toLowerCase();
        res.writeHead(200, {
          'Content-Type': MIME_TYPES[ext] || 'application/octet-stream',
          'Content-Length': stat.size,
          'Cache-Control': 'no-store',
          'Connection': 'close',
        });
        if (req.method === 'HEAD') {
          res.end();
          return;
        }
        if (stat.size <= 4 * 1024 * 1024) {
          res.end(fs.readFileSync(target));
          return;
        }
        const stream = fs.createReadStream(target);
        res.on('close', () => stream.destroy());
        stream.pipe(res);
      } catch (err) {
        res.writeHead(500).end(String(err));
      }
    });
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const addr = server.address();
      resolve({
        server,
        baseUrl: `http://127.0.0.1:${addr.port}/`,
        close: () => new Promise(done => {
          if (typeof server.closeAllConnections === 'function') server.closeAllConnections();
          server.close(() => done());
        }),
      });
    });
  });
}

(async () => {
  let ephemeral = null;
  let browser = null;
  try {
    let base = process.env.BROWSER_BASE_URL;
    if (!base) {
      ephemeral = await startEphemeralDocsServer();
      base = ephemeral.baseUrl;
    } else if (!base.endsWith('/')) {
      base += '/';
    }

    // The minimal sandbox lacks NSS/NSPR. Use the libraries shipped with this
    // exact npm browser package, not an unverified system download or apt bypass.
    await chromiumPackage.inflate(path.join(modules, '@sparticuz/chromium/bin/al2023.tar.br'));
    browser = await playwright.launch({
      executablePath: await chromium.executablePath(),
      env: {...process.env, LD_LIBRARY_PATH: [path.join(require('node:os').tmpdir(), 'al2023/lib'),
        process.env.LD_LIBRARY_PATH].filter(Boolean).join(':')},
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
      headless: true,
    });

    const cases = [
      ['index.html', 1440, 1100], ['index.html', 390, 844],
      ['executive-summary.html', 390, 844], ['research.html', 390, 844],
      ['sources.html', 390, 844], ['mdc88/index.html', 1440, 1100],
      ['mdc88/executive-summary.html', 390, 844],
    ];
    const report = {schema: 'gems88.browser-review.v1', checked_at_utc: new Date().toISOString(),
      browser: browser.version(), pages: [], failed_fetch_stays_negative: false,
      source_sha256: {}, ok_to_submit: false};
    let failed = false;

    for (const [name, width, height] of cases) {
      const page = await browser.newPage({viewport: {width, height}});
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('requestfailed', request => errors.push(`request failed: ${request.url()}`));
      page.on('response', response => {
        if (response.status() >= 400) errors.push(`HTTP ${response.status()}: ${response.url()}`);
      });
      const response = await page.goto(new URL(name, base).toString(), {waitUntil: 'networkidle'});
      if (!response || response.status() !== 200) errors.push('Page did not return HTTP 200');
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
      await page.screenshot({path: path.join(ROOT, '.cache', `${name.replaceAll('/', '-').replace('.html', '')}-${width}.png`), fullPage: true});
      await page.close();
    }

    const con88Page = await browser.newPage({viewport: {width: 1440, height: 1100}});
    const con88Errors = [];
    con88Page.on('pageerror', error => con88Errors.push(error.message));
    con88Page.on('requestfailed', request => con88Errors.push(`request failed: ${request.url()}`));
    con88Page.on('response', response => {
      if (response.status() >= 400) con88Errors.push(`HTTP ${response.status()}: ${response.url()}`);
    });
    const con88Resp = await con88Page.goto(new URL('con88.html', base).toString(), {waitUntil: 'networkidle'});
    if (!con88Resp || con88Resp.status() !== 200) con88Errors.push('con88.html did not return HTTP 200');
    const con88Banners = await con88Page.locator('.banner-stop, .status-pill, .alert-strip, [data-card-status]').allTextContents();
    const con88Overflow = await con88Page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    const con88TiffHref = await con88Page.locator('a[href$=".tif"]').first().getAttribute('href');
    const con88Pass = !con88Overflow && !con88Errors.length && con88Banners.length >= 1
      && con88Banners.every(b => b.includes('DO NOT SUBMIT')) && Boolean(con88TiffHref && con88TiffHref.includes('DO-NOT-SUBMIT'));
    report.con88_page = {
      page: 'con88.html',
      banners: con88Banners,
      overflow: con88Overflow,
      first_tiff: con88TiffHref,
      errors: con88Errors,
      sha256: crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT, 'docs/con88.html'))).digest('hex'),
      pass: con88Pass,
    };
    failed ||= !con88Pass;
    await con88Page.close();

    const unavailable = await browser.newPage();
    await unavailable.route('**/data/download_audit.json', route => route.abort());
    await unavailable.goto(new URL('index.html', base).toString(), {waitUntil: 'load'});
    await unavailable.waitForFunction(
      () => document.querySelector('[data-card-status]')?.textContent === 'PRE-FLIGHT AUDIT UNAVAILABLE — DO NOT SUBMIT',
      {timeout: 5000},
    );
    const denied = await unavailable.locator('[data-card-status]').innerText();
    report.failed_fetch_stays_negative = denied === 'PRE-FLIGHT AUDIT UNAVAILABLE — DO NOT SUBMIT';
    failed ||= !report.failed_fetch_stays_negative;
    await unavailable.close();

    const download = await browser.newPage();
    const response = await download.request.get(new URL(expectedTiff, base).toString());
    const digest = crypto.createHash('sha256').update(await response.body()).digest('hex');
    report.research_download = {file: expectedTiff, http_status: response.status(), sha256: digest,
      matches_canonical_bytes: response.status() === 200 && digest === expected.file_sha256,
      ok_to_submit: false};
    failed ||= !report.research_download.matches_canonical_bytes;
    await download.goto(new URL('index.html', base).toString(), {waitUntil: 'networkidle'});
    const [clicked] = await Promise.all([
      download.waitForEvent('download'),
      download.locator('a[download][href$=".tif"]').first().click(),
    ]);
    const clickedDigest = crypto.createHash('sha256').update(fs.readFileSync(await clicked.path())).digest('hex');
    report.research_download.click_sha256 = clickedDigest;
    report.research_download.suggested_filename = clicked.suggestedFilename();
    report.research_download.click_matches_canonical_bytes = clickedDigest === expected.file_sha256
      && clicked.suggestedFilename().includes('DO-NOT-SUBMIT');
    failed ||= !report.research_download.click_matches_canonical_bytes;
    await download.close();

    const noScript = await browser.newPage({javaScriptEnabled: false});
    await noScript.goto(new URL('index.html', base).toString(), {waitUntil: 'networkidle'});
    report.no_javascript_banner = await noScript.locator('[data-card-status]').innerText();
    report.no_javascript_stays_negative = report.no_javascript_banner === 'NO NEW TIFF · RESEARCH DOWNLOAD ONLY · DO NOT SUBMIT';
    failed ||= !report.no_javascript_stays_negative;
    await noScript.close();

    for (const relative of ['docs/index.html', 'docs/executive-summary.html', 'docs/research.html',
      'docs/sources.html', 'docs/assets/site.css', 'docs/assets/site.js', 'docs/data/current_release.json',
      'docs/data/download_audit.json', 'docs/data/mtas88_run_card.json', 'docs/data/hypothesis_queue.json', 'docs/status.json',
      'docs/mdc88/index.html', 'docs/mdc88/executive-summary.html', 'docs/mdc88/status.json']) {
      report.source_sha256[relative] = crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT, relative))).digest('hex');
    }
    report.status = failed ? 'FAIL' : 'PASS';
    const serialized = JSON.stringify(report, null, 2) + '\n';
    fs.writeFileSync(path.join(ROOT, '.cache/browser-check.json'), serialized);
    if (process.env.BROWSER_EVIDENCE_OUT) {
      const outPath = path.resolve(ROOT, process.env.BROWSER_EVIDENCE_OUT);
      fs.mkdirSync(path.dirname(outPath), {recursive: true});
      fs.writeFileSync(outPath, serialized);
      const docsMirror = path.join(DOCS_ROOT, 'data', path.basename(outPath));
      fs.mkdirSync(path.dirname(docsMirror), {recursive: true});
      fs.writeFileSync(docsMirror, serialized);
    }
    console.log(serialized);
    if (failed) process.exitCode = 1;
  } finally {
    if (browser) await browser.close().catch(() => {});
    if (ephemeral) await ephemeral.close().catch(() => {});
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
