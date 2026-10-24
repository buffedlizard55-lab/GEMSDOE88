// Dated, fail-closed read-only data display. Never auto-approves submission unless every gate clears.
(async () => {
  const score = document.querySelector('[data-feed-score]');
  const stamp = document.querySelector('[data-feed-stamp]');
  if (score && stamp) {
    try {
      const response = await fetch('data/leaderboard.json', { cache: 'no-store' });
      if (!response.ok) throw new Error('snapshot unavailable');
      const data = await response.json();
      const rows = data.rows || data.observed_top10;
      if (!Array.isArray(rows) || rows[0]?.rank !== 1 || !(rows[0].public_dti > 0 && rows[0].public_dti <= 1)) {
        throw new Error('snapshot malformed');
      }
      score.textContent = Number(rows[0].public_dti).toFixed(4);
      const at = new Date(data.checked_utc || data.retrieved_at_utc);
      if (Number.isNaN(at.valueOf())) throw new Error('timestamp missing');
      const hours = (Date.now() - at.valueOf()) / 3600000;
      stamp.textContent = `Official public leaderboard · checked ${at.toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' })} UTC${hours > 12 ? ' · STALE SNAPSHOT' : ''}`;
    } catch (_) {
      stamp.textContent = 'Leaderboard snapshot unavailable. Use the official DrivenData page for live standings.';
    }
  }
  const cardStatus = document.querySelector('[data-card-status]');
  if (cardStatus) {
    try {
      const response = await fetch('data/gate-verdict.json', { cache: 'no-store' });
      if (!response.ok) throw new Error('verdict not available');
      const v = await response.json();
      if (v.policy !== 'gems88-gate-v3' || typeof v.ok_to_submit !== 'boolean' || typeof v.label !== 'string') throw new Error('verdict malformed');
      const why = (v.blocking_reasons || []).map((r) => String(r).split(':')[0]).join(' + ');
      cardStatus.textContent = v.ok_to_submit
        ? `${v.label} · GATE PASS (selector and the website slot limit still decide)`
        : `${v.label} · DO NOT SUBMIT · blocked by ${why || 'unknown gate'}`;
    } catch (_) {
      cardStatus.textContent = 'DO NOT SUBMIT · verification data unavailable (fail-closed)';
    }
  }
  for (const button of document.querySelectorAll('[data-copy]')) {
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.copy);
        button.textContent = 'Copied';
        setTimeout(() => { button.textContent = 'Copy'; }, 2000);
      } catch (_) {
        button.textContent = 'Copy unavailable';
      }
    });
  }
})();
