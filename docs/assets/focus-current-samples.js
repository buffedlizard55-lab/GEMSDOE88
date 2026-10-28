/* Dated GitHub-only byte samples; never a score, selector, or upload approval. */
(() => {
  'use strict';
  const SITES = ['GEMSDOE24', 'GEMSDOE25', 'GEMSDOE27', 'GEMSDOE28', 'GEMSDOE30',
    'GEMSDOE31', 'GEMSDOE32', 'GEMSDOE33', 'GEMSDOE36'];
  const STATES = ['DUPLICATE_STOP', 'NOT_CLEARED', 'INVALID_RASTER', 'NOT_DISCOVERED', 'UNKNOWN'];
  const FORMAT_CHECKS = new Set(['geotiff', 'single_band', 'single_raster_dataset', 'self_contained_dataset',
    'real_numeric_dtype', 'dtype_float32', 'template_single_band', 'template_single_raster_dataset',
    'template_self_contained_dataset', 'crs_match', 'shape_match', 'transform_match', 'no_nodata_sentinel',
    'all_finite', 'values_in_0_1', 'all_pixels_unmasked', 'no_nan_inside', 'range_0_1', 'footprint_nonempty',
    'no_mass_outside', 'footprint_not_masked', 'strict_audit', 'raster_decode_or_grid_error']);
  const SCOPE = 'First bare docs/downloads/ or docs/research/ TIFF path in the complete README (maximum 2000000 bytes) at each pinned HEAD; excludes other paths/URLs and is not a winner search or complete inventory.';
  const SCORE_STATUS = 'NOT MEASURED: no holdout rerun or organizer receipt; no leaderboard estimate.';
  const SHA40 = /^[a-f0-9]{40}$/;
  const SHA64 = /^[a-f0-9]{64}$/;
  const TIF = /^docs\/(?:downloads|research)\/(?:[A-Za-z0-9_.-]+\/)*[A-Za-z0-9_.-]+\.tiff?$/i;
  const utc = s => typeof s === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(s) &&
    Number.isFinite(Date.parse(s)) && new Date(s).toISOString() === s.replace('Z', '.000Z');

  // snapshotSha must be computed from the exact fetched bytes, not reserialized JSON.
  function assess(report, revisions, now, snapshotSha) {
    if (!report || report.schema !== 'gems88.focus-current-samples.v2' ||
        report.ok_to_submit !== false || report.approved_for_weekly_slot !== false ||
        report.new_tiffs_generated !== 0 || report.weekly_slots_used !== 0 ||
        report.scope !== SCOPE || report.score_status !== SCORE_STATUS ||
        !utc(report.checked_at_utc) || !SHA64.test(snapshotSha || '') ||
        report.head_snapshot_sha256 !== snapshotSha ||
        report.witness_sha256 !== 'ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be' ||
        !revisions || revisions.schema !== 'gems88.focus-freshness.v1' ||
        revisions.ok_to_submit !== false || revisions.approved_for_weekly_slot !== false ||
        revisions.stale_after_hours !== 12 ||
        report.head_snapshot_checked_at_utc !== revisions.checked_at_utc ||
        !utc(revisions.checked_at_utc) || !Number.isFinite(now) ||
        !Array.isArray(report.rows) || report.rows.length !== SITES.length ||
        !Array.isArray(revisions.sites) || revisions.sites.length !== SITES.length) throw new Error('invalid sample snapshot');
    const sampleTime = Date.parse(report.checked_at_utc);
    const headTime = Date.parse(revisions.checked_at_utc);
    if (sampleTime > now + 300000 || headTime > now + 300000 ||
        sampleTime < headTime - 300000 || sampleTime - headTime > 12 * 3600000) throw new Error('invalid time');
    const counts = Object.fromEntries(STATES.map(key => [key, 0]));
    report.rows.forEach((row, i) => {
      const rev = revisions.sites[i];
      if (!row || !rev || row.site !== SITES[i] || rev.site !== SITES[i] ||
          row.head !== rev.current_head || row.ok_to_submit !== false ||
          !STATES.includes(row.decision) || typeof row.reason !== 'string' || !row.reason ||
          (row.head !== null && !SHA40.test(row.head))) throw new Error('invalid identity');
      const readme = row.head ? `https://github.com/buffedlizard55-lab/${row.site}/blob/${row.head}/README.md` : null;
      if (row.readme_url !== readme) throw new Error('invalid README URL');
      if (row.readme_sha256 === null) {
        if (row.readme_bytes !== null || row.path !== null || row.decision !== 'UNKNOWN') throw new Error('unmeasured README');
      } else if (!SHA64.test(row.readme_sha256) || !Number.isSafeInteger(row.readme_bytes) ||
                 row.readme_bytes <= 0 || row.readme_bytes > 2000000 || !row.head) throw new Error('invalid README digest');
      if (row.path !== null) {
        if (typeof row.path !== 'string' || !TIF.test(row.path) || row.path.split('/').includes('..') ||
            row.source_url !== `https://github.com/buffedlizard55-lab/${row.site}/blob/${row.head}/${row.path}`) throw new Error('invalid source URL');
      } else if (row.source_url !== null) throw new Error('source without path');
      if (row.sha256 !== null && (!SHA64.test(row.sha256) || !row.path)) throw new Error('invalid SHA');
      if (row.format_pass !== null && typeof row.format_pass !== 'boolean') throw new Error('invalid format');
      if ((row.sha256 === null) !== (row.format_pass === null) ||
          (row.head === null && (row.decision !== 'UNKNOWN' || row.path !== null || row.sha256 !== null)) ||
          (row.decision === 'UNKNOWN' && row.sha256 !== null) ||
          (row.decision === 'INVALID_RASTER' && row.sha256 === null) ||
          (row.decision === 'NOT_DISCOVERED' && (row.path !== null || row.sha256 !== null))) throw new Error('unbound sample');
      if (row.format_pass === null) {
        if (row.format_failures !== null) throw new Error('unmeasured diagnostics');
      } else {
        if (!Array.isArray(row.format_failures) ||
            row.format_failures.some(f => typeof f !== 'string' || !FORMAT_CHECKS.has(f)) ||
            row.format_failures.some((f, j, a) => j > 0 && a[j - 1] >= f) ||
            ((row.format_pass === true) !== (row.format_failures.length === 0))) throw new Error('invalid diagnostics');
      }
      if (row.decision === 'DUPLICATE_STOP' || row.decision === 'NOT_CLEARED') {
        if (!row.path || !SHA64.test(row.sha256 || '') || typeof row.format_pass !== 'boolean' ||
            !Number.isSafeInteger(row.positive_inside_footprint) || row.positive_inside_footprint <= 0 ||
            typeof row.overlap_3px !== 'number' || !Number.isFinite(row.overlap_3px) ||
            row.overlap_3px < 0 || row.overlap_3px > 1 ||
            ((row.decision === 'DUPLICATE_STOP') !== (row.overlap_3px > 0.70))) throw new Error('invalid measurement');
      } else if (row.overlap_3px !== null || row.positive_inside_footprint !== null) throw new Error('unmeasured sample');
      counts[row.decision]++;
    });
    if (!report.counts || STATES.some(key => report.counts[key] !== counts[key])) throw new Error('invalid counts');
    return { rows: report.rows, counts, checkedAt: report.checked_at_utc,
      expired: now - headTime > 12 * 3600000 || now - sampleTime > 12 * 3600000 };
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = { assess, SITES };
  if (typeof document === 'undefined') return;
  const status = document.querySelector('[data-current-samples-status]');
  const body = document.querySelector('[data-current-samples-body]');
  if (!status || !body) return;
  const get = url => fetch(url, {cache: 'no-store'}).then(r => { if (!r.ok) throw new Error('unavailable'); return r.arrayBuffer(); });
  Promise.all([get('data/focus-current-samples.json'), get('data/focus-freshness.json')])
    .then(async ([sampleBytes, headBytes]) => {
      // Web Crypto is available on HTTPS GitHub Pages and loopback test servers.
      // If it is unavailable or hashing fails, the catch below fails closed.
      const digest = await crypto.subtle.digest('SHA-256', headBytes);
      const sha = Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
      const decoder = new TextDecoder('utf-8', {fatal: true});
      const report = JSON.parse(decoder.decode(sampleBytes));
      const revisions = JSON.parse(decoder.decode(headBytes));
      const view = assess(report, revisions, Date.now(), sha);
      const unavailable = view.counts.NOT_DISCOVERED + view.counts.UNKNOWN + view.counts.INVALID_RASTER;
      status.textContent = view.expired
        ? `Sample snapshot expired (last checked ${view.checkedAt}); current state unknown. DO NOT SUBMIT.`
        : `Checked ${view.checkedAt}: ${view.counts.DUPLICATE_STOP} sampled files fail the literal witness; ${unavailable} ${unavailable === 1 ? 'is' : 'are'} unavailable or unmeasured. DO NOT SUBMIT.`;
      body.replaceChildren();
      for (const row of view.rows) {
        const tr = document.createElement('tr');
        const cell = (tag, text) => { const el = document.createElement(tag); el.textContent = text; tr.append(el); return el; };
        cell('th', `${row.site} ${row.head ? row.head.slice(0, 8) : '(HEAD unavailable)'}`).setAttribute('scope', 'row');
        const file = cell('td', '');
        if (row.path) {
          const link = document.createElement('a');
          link.href = row.source_url;
          link.textContent = row.path.split('/').pop();
          file.append(link);
        } else file.textContent = row.decision === 'NOT_DISCOVERED' ? 'No matching path in bounded README' : 'README or TIFF unavailable';
        const format = row.format_pass === true ? 'PASS (local only)' : row.format_pass === false
          ? `FAIL: ${row.format_failures.join(', ')}` : 'Unknown';
        cell('td', view.expired ? `Expired observation: ${format}` : format);
        cell('td', typeof row.overlap_3px === 'number' ? row.overlap_3px.toFixed(4) : 'Not measured');
        cell('td', view.expired ? 'EXPIRED · CURRENT STATE UNKNOWN · DO NOT SUBMIT' :
          row.decision === 'DUPLICATE_STOP' ? 'DUPLICATE · DO NOT SUBMIT' : 'NOT CLEARED · DO NOT SUBMIT');
        body.append(tr);
      }
    })
    .catch(() => { status.textContent = 'Sample audit unavailable or inconsistent. DO NOT SUBMIT.'; body.replaceChildren(); });
})();
