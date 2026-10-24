// Dated, fail-closed read-only data display. Never auto-approves submission unless every gate clears.
(async () => {
  const score = document.querySelector('[data-feed-score]');
  const stamp = document.querySelector('[data-feed-stamp]');
  if (score && stamp) {
    try {
      const response = await fetch('data/leaderboard.json', { cache: 'no-store' });
      if (!response.ok) throw new Error('snapshot unavailable');
      const data = await response.json();
      const rows = data.observed_top10 || data.rows;
      if (!Array.isArray(rows) || rows[0]?.rank !== 1 || !(rows[0].public_dti > 0 && rows[0].public_dti <= 1)) {
        throw new Error('snapshot malformed');
      }
      score.textContent = Number(rows[0].public_dti).toFixed(4);
      const at = new Date(data.retrieved_at_utc || data.checked_utc);
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
      // Single authoritative gate (scripts/submission_gate.py) -> docs/data/submission_gate.json.
      const response = await fetch('data/submission_gate.json', { cache: 'no-store' });
      if (!response.ok) throw new Error('gate report not available');
      const gate = await response.json();
      const passed = gate.verdict === 'OK_TO_SUBMIT' && gate.ok_to_submit === true &&
        Array.isArray(gate.failures) && gate.failures.length === 0;
      cardStatus.textContent = passed
        ? `✅ OK TO DOWNLOAD AND SUBMIT · ${gate.candidate.file_name} · all ${gate.checks.length} automated gate checks pass · ORGANIZER-CONFIRMED score: none yet`
        : `⛔ DO NOT SUBMIT · automated gate failed: ${(gate.failures || ['unknown']).slice(0, 2).join(' | ')}`;
    } catch (_) {
      cardStatus.textContent = '⛔ DO NOT SUBMIT · gate report unavailable (fail closed)';
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
