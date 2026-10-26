/* GitHub revision drift only. This code cannot select or authorize a submission. */
(() => {
  'use strict';
  const SITES = ['GEMSDOE24', 'GEMSDOE25', 'GEMSDOE27', 'GEMSDOE28', 'GEMSDOE30',
    'GEMSDOE31', 'GEMSDOE32', 'GEMSDOE33', 'GEMSDOE36'];
  const SHA = /^[0-9a-f]{40}$/;
  const UTC = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
  const LIMIT_HOURS = 12;
  const validUtc = value => {
    if (typeof value !== 'string' || !UTC.test(value)) return false;
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) && new Date(parsed).toISOString() === value.replace('Z', '.000Z');
  };

  // Pure validator: callable by Node tests without a browser or network.
  function assess(report, expected, now) {
    if (!report || report.schema !== 'gems88.focus-freshness.v1' ||
        report.ok_to_submit !== false || report.approved_for_weekly_slot !== false ||
        report.audited_snapshot !== 'docs/data/focus_sites_20261026.json' ||
        !/^[0-9a-f]{64}$/.test(report.audited_snapshot_sha256) ||
        report.stale_after_hours !== LIMIT_HOURS || !validUtc(report.checked_at_utc) ||
        !Array.isArray(report.sites) || report.sites.length !== SITES.length ||
        !Array.isArray(expected) || expected.length !== SITES.length ||
        !Number.isFinite(now)) throw new Error('invalid snapshot');
    const time = Date.parse(report.checked_at_utc);
    if (!Number.isFinite(time) || time > now + 5 * 60 * 1000) throw new Error('invalid timestamp');
    const counts = { changed: 0, unchanged: 0, unknown: 0 };
    for (let i = 0; i < SITES.length; i++) {
      const row = report.sites[i];
      const pin = expected[i];
      if (!row || !pin || row.site !== SITES[i] || pin.site !== SITES[i] ||
          !SHA.test(pin.head) || row.audited_head !== pin.head ||
          row.source_url !== `https://api.github.com/repos/buffedlizard55-lab/${row.site}/commits/HEAD`) {
        throw new Error('inconsistent audited revision');
      }
      if (row.state === 'UNKNOWN') {
        if (row.current_head !== null || row.current_commit_utc !== null ||
            typeof row.error !== 'string' || !row.error) throw new Error('inconsistent unknown');
        counts.unknown++;
      } else if (row.state === 'CHANGED' || row.state === 'UNCHANGED') {
        if (typeof row.current_head !== 'string' || !SHA.test(row.current_head) ||
            !validUtc(row.current_commit_utc) ||
            row.error !== null || ((row.state === 'UNCHANGED') !== (row.current_head === pin.head))) {
          throw new Error('inconsistent revision state');
        }
        counts[row.state.toLowerCase()]++;
      } else throw new Error('invalid revision state');
    }
    if (!report.counts || Object.keys(counts).some(k => report.counts[k] !== counts[k]) ||
        report.status !== (counts.unknown ? 'PARTIAL' : 'COMPLETE')) throw new Error('invalid totals');
    return { rows: report.sites, counts, checkedAt: report.checked_at_utc,
      expired: now - time > LIMIT_HOURS * 60 * 60 * 1000 };
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = { assess, SITES };
  if (typeof document === 'undefined') return;
  const banner = document.querySelector('[data-focus-feed-status]');
  const labels = Array.from(document.querySelectorAll('[data-focus-freshness]'));
  if (!banner) return;
  const unknown = () => {
    banner.textContent = 'Revision check unavailable or inconsistent. The table is historical; DO NOT SUBMIT.';
    labels.forEach(label => { label.textContent = 'Current revision unknown'; });
  };
  const expected = labels.map(label => ({site: label.dataset.focusFreshness, head: label.dataset.auditedHead}));
  fetch('data/focus-freshness.json', {cache: 'no-store'})
    .then(response => { if (!response.ok) throw new Error('unavailable'); return response.json(); })
    .then(report => {
      const view = assess(report, expected, Date.now());
      if (view.expired) {
        banner.textContent = `Revision snapshot expired (last checked ${view.checkedAt}); current state unknown. DO NOT SUBMIT.`;
      } else if (view.counts.unknown) {
        banner.textContent = `Incomplete revision check at ${view.checkedAt}: ${view.counts.changed} changed, ${view.counts.unknown} unavailable. No submission approved.`;
      } else {
        banner.textContent = `Checked ${view.checkedAt}: ${view.counts.changed} of 9 repositories changed since the audited snapshot. This is not a score or approval.`;
      }
      for (let i = 0; i < labels.length; i++) {
        const label = labels[i];
        const row = view.rows[i];
        label.replaceChildren();
        if (row.state === 'UNKNOWN') {
          label.textContent = view.expired ? 'Last check unavailable; snapshot expired' : 'Revision unavailable';
          continue;
        }
        const prefix = view.expired ? 'Last observed (expired): ' :
          (row.state === 'CHANGED' ? 'Changed since audit: ' : 'No change observed: ');
        label.append(document.createTextNode(prefix));
        const link = document.createElement('a');
        link.href = `https://github.com/buffedlizard55-lab/${row.site}/commit/${row.current_head}`;
        link.textContent = row.current_head.slice(0, 8);
        link.setAttribute('aria-label', `${row.site} observed GitHub commit ${row.current_head}`);
        label.append(link);
      }
    })
    .catch(unknown);
})();
