'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {assess, SITES} = require('../docs/assets/focus-freshness.js');

const root = path.join(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'docs/assets/focus-freshness.js'), 'utf8');
const snapshot = JSON.parse(fs.readFileSync(path.join(root, 'docs/data/focus-freshness.json'), 'utf8'));
const audit = JSON.parse(fs.readFileSync(path.join(root, 'docs/data/focus_sites_20261026.json'), 'utf8'));
const expected = audit.focus_sites.map(row => ({site: row.site, head: row.inspected_repo_head_sha}));
const copy = value => JSON.parse(JSON.stringify(value));
// Build a deterministic complete test-only report even when a later legitimate
// scheduled GitHub snapshot is PARTIAL or has different revision counts.
const stored = copy(snapshot);
for (let i = 0; i < stored.sites.length; i++) {
  const row = stored.sites[i];
  const candidate = String(i + 1).repeat(40);
  const syntheticHead = candidate === row.audited_head ? 'a'.repeat(40) : candidate;
  Object.assign(row, {state: 'CHANGED', current_head: syntheticHead,
    current_commit_utc: stored.checked_at_utc, error: null});
}
stored.counts = {changed: 9, unchanged: 0, unknown: 0};
stored.status = 'COMPLETE';
const checked = Date.parse(stored.checked_at_utc);

class FakeElement {
  constructor() { this.children = []; this.dataset = {}; this._text = ''; this.attributes = {}; }
  set textContent(value) { this.children = []; this._text = String(value); }
  get textContent() { return this._text + this.children.map(item => item.textContent).join(''); }
  replaceChildren(...children) { this._text = ''; this.children = children; }
  append(...children) { this.children.push(...children); }
  setAttribute(name, value) { this.attributes[name] = value; }
}

async function render(report, {now = checked + 60000, fail = false} = {}) {
  const banner = new FakeElement();
  const labels = expected.map(row => {
    const label = new FakeElement();
    label.dataset.focusFreshness = row.site;
    label.dataset.auditedHead = row.head;
    return label;
  });
  const document = {
    querySelector: () => banner,
    querySelectorAll: () => labels,
    createElement: () => new FakeElement(),
    createTextNode: text => ({textContent: text}),
  };
  class FixedDate extends Date { static now() { return now; } }
  const fetch = () => fail ? Promise.reject(new Error('network')) :
    Promise.resolve({ok: true, json: () => Promise.resolve(copy(report))});
  vm.runInNewContext(source, {document, fetch, Date: FixedDate}, {filename: 'focus-freshness.js'});
  await new Promise(resolve => setImmediate(resolve));
  return {banner, labels};
}

test('fresh snapshot displays nine changed revisions and safe GitHub links', async () => {
  const {banner, labels} = await render(stored);
  assert.match(banner.textContent, /9 of 9 repositories changed/);
  assert.match(banner.textContent, /not a score or approval/);
  labels.forEach((label, i) => {
    assert.match(label.textContent, /Changed since audit:/);
    const link = label.children[1];
    assert.equal(link.href, `https://github.com/buffedlizard55-lab/${SITES[i]}/commit/${stored.sites[i].current_head}`);
    assert.equal(link.textContent, stored.sites[i].current_head.slice(0, 8));
  });
});

test('unchanged HEAD is only an observation, not clearance', async () => {
  const report = copy(stored);
  report.sites[0].current_head = report.sites[0].audited_head;
  report.sites[0].state = 'UNCHANGED';
  report.counts.changed--;
  report.counts.unchanged++;
  const {banner, labels} = await render(report);
  assert.match(labels[0].textContent, /No change observed/);
  assert.match(banner.textContent, /8 of 9 repositories changed/);
  assert.match(banner.textContent, /not a score or approval/);
});

test('partial fetch fails closed and does not reuse an old HEAD', async () => {
  const report = copy(stored);
  report.sites[0].state = 'UNKNOWN';
  report.sites[0].current_head = null;
  report.sites[0].current_commit_utc = null;
  report.sites[0].error = 'GitHub HTTP 403';
  report.counts.changed--;
  report.counts.unknown++;
  report.status = 'PARTIAL';
  const {banner, labels} = await render(report);
  assert.match(banner.textContent, /Incomplete revision check/);
  assert.match(banner.textContent, /No submission approved/);
  assert.equal(labels[0].textContent, 'Revision unavailable');
  assert.equal(labels[0].children.length, 0);
});

test('overdue snapshot is visibly expired, including its row labels', async () => {
  const {banner, labels} = await render(stored, {now: checked + 12 * 3600 * 1000 + 1});
  assert.match(banner.textContent, /snapshot expired/);
  assert.match(banner.textContent, /current state unknown/);
  assert.ok(labels.every(label => label.textContent.startsWith('Last observed (expired):')));
});

test('fetch errors do not silently retain a green state', async () => {
  const {banner, labels} = await render(stored, {fail: true});
  assert.match(banner.textContent, /unavailable or inconsistent/);
  assert.ok(labels.every(label => label.textContent === 'Current revision unknown'));
});

test('unsafe, inconsistent, forged or future reports are rejected', async () => {
  const mutations = [
    r => { r.ok_to_submit = true; },
    r => { r.approved_for_weekly_slot = true; },
    r => { r.audited_snapshot_sha256 = 'not-a-sha'; },
    r => { r.checked_at_utc = '2026-02-31T00:00:00Z'; },
    r => { r.checked_at_utc = new Date(checked + 3600000).toISOString().replace('.000Z', 'Z'); },
    r => { r.sites[0].current_head = 'javascript:alert(1)'; },
    r => { r.sites[0].audited_head = 'f'.repeat(40); },
    r => { r.sites[0].source_url = 'https://example.com/'; },
    r => { r.counts.changed = 0; },
    r => { r.sites.pop(); },
    r => { r.sites[0].state = 'UNCHANGED'; },
    r => { r.sites[0].state = 'UNKNOWN'; },
  ];
  for (const mutate of mutations) {
    const report = copy(stored);
    mutate(report);
    assert.throws(() => assess(report, expected, checked + 60000));
    const {banner, labels} = await render(report);
    assert.match(banner.textContent, /unavailable or inconsistent/);
    assert.ok(labels.every(label => label.textContent === 'Current revision unknown'));
  }
});
