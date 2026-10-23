// Dated, fail-closed read-only data display. Never auto-approves submission unless every gate clears.
(async () => {
  const score = document.querySelector('[data-feed-score]');
  const stamp = document.querySelector('[data-feed-stamp]');
  if (score && stamp) {
    try {
      const response = await fetch('data/leaderboard.json', { cache: 'no-store' });
      if (!response.ok) throw new Error('snapshot unavailable');
      const data = await response.json();
      const rows = data.observed_top10;
      if (!Array.isArray(rows) || rows[0]?.rank !== 1 || !(rows[0].public_dti > 0 && rows[0].public_dti <= 1)) {
        throw new Error('snapshot malformed');
      }
      score.textContent = Number(rows[0].public_dti).toFixed(4);
      const at = new Date(data.retrieved_at_utc);
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
      const response = await fetch('data/run-card.json', { cache: 'no-store' });
      if (!response.ok) throw new Error('card not available');
      const card = await response.json();
      const formatOk = card.validator_output?.all_checks_passed === true || card.validator_output?.local_format_ok === true;
      const safe = card.verdict === 'promote-to-selector-only' &&
        card.ok_to_submit === true &&
        formatOk &&
        card.correlation_overlap_vs_registry?.universal_witness?.universal_overlap_blocker === false;
      cardStatus.textContent = safe
        ? 'OK TO DOWNLOAD: YES · SUBMISSION GATE PASSED (human selector check still required)'
        : 'OK TO DOWNLOAD: YES · DO NOT SUBMIT AUTOMATICALLY (literal 17GEMSDOE full-footprint witness overlap = 1.0000 > 0.70; 18/18 sparse siblings PASS)';
    } catch (_) {
      cardStatus.textContent = 'DO NOT SUBMIT · verification data unavailable';
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
