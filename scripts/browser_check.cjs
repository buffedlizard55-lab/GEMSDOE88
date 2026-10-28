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
const focusSnapshot = JSON.parse(fs.readFileSync(path.join(ROOT, 'docs/data/focus-freshness.json'), 'utf8'));
const sampleSnapshot = JSON.parse(fs.readFileSync(path.join(ROOT, 'docs/data/focus-current-samples.json'), 'utf8'));
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

    // The condensed comparison must retain accessible, expandable lineage and
    // later-sample details on a narrow screen without widening the page itself.
    const comparison = await browser.newPage({viewport: {width: 390, height: 844}});
    await comparison.goto(new URL('index.html', base).toString(), {waitUntil: 'networkidle'});
    const focusRows = comparison.locator('#focus-sites-executive-summary .table-scroll').first().locator('tbody tr');
    const details = comparison.locator('#focus-sites-executive-summary details.focus-row-details');
    const rowCount = await focusRows.count();
    const detailsCount = await details.count();
    const initiallyClosed = await comparison.locator('#focus-sites-executive-summary details.focus-row-details[open]').count() === 0;
    await details.first().locator('summary').click();
    const expands = await details.first().evaluate(el => el.open);
    const detailText = await details.first().innerText();
    const includesEvidence = detailText.includes('Historical file:') && detailText.includes('Later sampled file')
      && detailText.includes('DO NOT SUBMIT');
    const pageFits = await comparison.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
    const comparisonPass = rowCount === 9 && detailsCount === 9 && initiallyClosed && expands && includesEvidence && pageFits;
    report.focus_comparison = {row_count: rowCount, expandable_details: detailsCount,
      initially_closed: initiallyClosed, expands, includes_evidence: includesEvidence,
      page_fits_mobile: pageFits, pass: comparisonPass};
    failed ||= !comparisonPass;
    await comparison.close();

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

    // Exercise the HEAD-only feed in Chromium, with a deterministic clock so
    // a stored snapshot can be tested after its real-world 12-hour expiry.
    const observedTime = Date.parse(focusSnapshot.checked_at_utc);
    // A deployed snapshot may itself be PARTIAL. Complete a test-only fixture
    // rather than treating unknown repositories as a product failure or a real
    // GitHub observation; the partial scenario below remains separately tested.
    const freshReport = JSON.parse(JSON.stringify(focusSnapshot));
    let usedSimulatedHeads = false;
    for (const row of freshReport.sites) {
      if (row.state === 'UNKNOWN') {
        const syntheticHead = row.audited_head === 'f'.repeat(40) ? 'e'.repeat(40) : 'f'.repeat(40);
        Object.assign(row, {state: 'CHANGED', current_head: syntheticHead,
          current_commit_utc: freshReport.checked_at_utc, error: null});
        usedSimulatedHeads = true;
      }
    }
    freshReport.counts = {changed: freshReport.sites.filter(row => row.state === 'CHANGED').length,
      unchanged: freshReport.sites.filter(row => row.state === 'UNCHANGED').length, unknown: 0};
    freshReport.status = 'COMPLETE';
    const freshFocus = await browser.newPage();
    await freshFocus.addInitScript(time => { Date.now = () => time; }, observedTime + 60000);
    await freshFocus.route('**/data/focus-freshness.json', route => route.fulfill({
      status: 200, contentType: 'application/json', body: JSON.stringify(freshReport),
    }));
    await freshFocus.goto(new URL('index.html', base).toString(), {waitUntil: 'networkidle'});
    const freshText = await freshFocus.locator('[data-focus-feed-status]').innerText();
    const freshRows = await freshFocus.locator('[data-focus-freshness]').allTextContents();
    const freshPass = freshText.includes(`${freshReport.counts.changed} of 9 repositories changed`)
      && freshText.includes('not a score or approval') && freshRows.length === 9;
    await freshFocus.close();

    const missingFocus = await browser.newPage();
    await missingFocus.route('**/data/focus-freshness.json', route => route.abort());
    await missingFocus.goto(new URL('index.html', base).toString(), {waitUntil: 'networkidle'});
    const missingText = await missingFocus.locator('[data-focus-feed-status]').innerText();
    const missingRows = await missingFocus.locator('[data-focus-freshness]').allTextContents();
    const missingPass = missingText.includes('unavailable or inconsistent')
      && missingRows.length === 9 && missingRows.every(row => row === 'Current revision unknown');
    await missingFocus.close();

    const partialReport = JSON.parse(JSON.stringify(freshReport));
    const previousState = partialReport.sites[0].state.toLowerCase();
    partialReport.counts[previousState]--;
    partialReport.counts.unknown++;
    partialReport.status = 'PARTIAL';
    Object.assign(partialReport.sites[0], {state: 'UNKNOWN', current_head: null,
      current_commit_utc: null, error: 'GitHub HTTP 403'});
    const partialFocus = await browser.newPage();
    await partialFocus.addInitScript(time => { Date.now = () => time; }, observedTime + 60000);
    await partialFocus.route('**/data/focus-freshness.json', route => route.fulfill({
      status: 200, contentType: 'application/json', body: JSON.stringify(partialReport),
    }));
    await partialFocus.goto(new URL('index.html', base).toString(), {waitUntil: 'networkidle'});
    const partialText = await partialFocus.locator('[data-focus-feed-status]').innerText();
    const partialFirst = await partialFocus.locator('[data-focus-freshness]').first().innerText();
    const partialPass = partialText.includes('Incomplete revision check')
      && partialText.includes('No submission approved') && partialFirst === 'Revision unavailable';
    await partialFocus.close();

    const expiredFocus = await browser.newPage();
    await expiredFocus.addInitScript(time => { Date.now = () => time; }, observedTime + 12 * 3600 * 1000 + 1000);
    await expiredFocus.goto(new URL('index.html', base).toString(), {waitUntil: 'networkidle'});
    const expiredText = await expiredFocus.locator('[data-focus-feed-status]').innerText();
    const expiredRows = await expiredFocus.locator('[data-focus-freshness]').allTextContents();
    const expiredPass = expiredText.includes('snapshot expired') && expiredText.includes('DO NOT SUBMIT')
      && expiredRows.length === 9 && expiredRows.every(row => row.includes('expired'));
    await expiredFocus.close();
    report.focus_freshness = {fresh_snapshot_pass: freshPass, missing_feed_fail_closed: missingPass,
      partial_feed_fail_closed: partialPass, expired_feed_fail_closed: expiredPass,
      checked_snapshot: focusSnapshot.checked_at_utc, fresh_fixture_used_simulated_heads: usedSimulatedHeads,
      fresh_text: freshText, missing_text: missingText, partial_text: partialText, expired_text: expiredText};
    failed ||= !freshPass || !missingPass || !partialPass || !expiredPass;

    // Reopened README-cited samples must be tied to the same HEAD snapshot,
    // expire, and stay negative if the report is missing or inconsistent.
    const sampleTime = Date.parse(sampleSnapshot.checked_at_utc);
    const sampleFresh = await browser.newPage({viewport: {width: 390, height: 844}});
    await sampleFresh.addInitScript(time => { Date.now = () => time; }, sampleTime + 60000);
    await sampleFresh.goto(new URL('index.html', base).toString(), {waitUntil: 'networkidle'});
    const sampleText = await sampleFresh.locator('[data-current-samples-status]').innerText();
    const sampleRows = await sampleFresh.locator('[data-current-samples-body] tr').count();
    const sampleDecisionText = await sampleFresh.locator('[data-current-samples-body]').innerText();
    const samplePass = sampleRows === 9 && sampleText.includes(sampleSnapshot.checked_at_utc)
      && sampleText.includes('DO NOT SUBMIT') && sampleDecisionText.includes('DO NOT SUBMIT')
      && await sampleFresh.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
    await sampleFresh.close();

    const sampleMissing = await browser.newPage();
    await sampleMissing.route('**/data/focus-current-samples.json', route => route.abort());
    await sampleMissing.goto(new URL('index.html', base).toString(), {waitUntil: 'networkidle'});
    const sampleMissingText = await sampleMissing.locator('[data-current-samples-status]').innerText();
    const sampleMissingPass = sampleMissingText.includes('unavailable or inconsistent') && sampleMissingText.includes('DO NOT SUBMIT');
    await sampleMissing.close();

    const altered = JSON.parse(JSON.stringify(sampleSnapshot));
    altered.rows[0].head = altered.rows[0].head === 'a'.repeat(40) ? 'b'.repeat(40) : 'a'.repeat(40);
    const sampleMismatch = await browser.newPage();
    await sampleMismatch.addInitScript(time => { Date.now = () => time; }, sampleTime + 60000);
    await sampleMismatch.route('**/data/focus-current-samples.json', route => route.fulfill({
      status: 200, contentType: 'application/json', body: JSON.stringify(altered),
    }));
    await sampleMismatch.goto(new URL('index.html', base).toString(), {waitUntil: 'networkidle'});
    const sampleMismatchText = await sampleMismatch.locator('[data-current-samples-status]').innerText();
    const sampleMismatchPass = sampleMismatchText.includes('unavailable or inconsistent') && sampleMismatchText.includes('DO NOT SUBMIT');
    await sampleMismatch.close();

    const sampleExpired = await browser.newPage();
    await sampleExpired.addInitScript(time => { Date.now = () => time; }, sampleTime + 13 * 3600 * 1000);
    await sampleExpired.goto(new URL('index.html', base).toString(), {waitUntil: 'networkidle'});
    const sampleExpiredText = await sampleExpired.locator('[data-current-samples-status]').innerText();
    const sampleExpiredPass = sampleExpiredText.includes('snapshot expired') && sampleExpiredText.includes('DO NOT SUBMIT');
    await sampleExpired.close();
    report.focus_current_samples = {fresh_snapshot_pass: samplePass, row_count: sampleRows,
      missing_feed_fail_closed: sampleMissingPass, head_mismatch_fail_closed: sampleMismatchPass,
      expired_feed_fail_closed: sampleExpiredPass, checked_snapshot: sampleSnapshot.checked_at_utc,
      fresh_text: sampleText, missing_text: sampleMissingText, mismatch_text: sampleMismatchText,
      expired_text: sampleExpiredText};
    failed ||= !samplePass || !sampleMissingPass || !sampleMismatchPass || !sampleExpiredPass;

    const noScript = await browser.newPage({javaScriptEnabled: false});
    await noScript.goto(new URL('index.html', base).toString(), {waitUntil: 'networkidle'});
    report.no_javascript_banner = await noScript.locator('[data-card-status]').innerText();
    report.no_javascript_stays_negative = report.no_javascript_banner === 'NO NEW TIFF · RESEARCH DOWNLOAD ONLY · DO NOT SUBMIT';
    failed ||= !report.no_javascript_stays_negative;
    await noScript.close();

    for (const relative of ['docs/index.html', 'docs/executive-summary.html', 'docs/research.html',
      'docs/sources.html', 'docs/assets/site.css', 'docs/assets/site.js', 'docs/data/current_release.json',
      'docs/data/download_audit.json', 'docs/data/mtas88_run_card.json', 'docs/data/hypothesis_queue.json', 'docs/status.json',
      'docs/assets/focus-freshness.js', 'docs/data/focus-freshness.json',
      'docs/assets/focus-current-samples.js', 'docs/data/focus-current-samples.json',
      'docs/data/focus_sample_2b5a8383.json', 'docs/data/focus_sites_20261026.json',
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
