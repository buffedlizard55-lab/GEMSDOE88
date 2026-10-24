// Static, fail-closed display: a dated public snapshot is NOT an account receipt.
(async () => {
  const score = document.querySelector('[data-feed-score]');
  const stamp = document.querySelector('[data-feed-stamp]');
  if (score && stamp) {
    try {
      const response = await fetch('data/leaderboard.json', { cache: 'no-store' });
      if (!response.ok) throw new Error('snapshot unavailable');
      const data = await response.json();
      const rows = data.rows ?? data.observed_top10;
      const at = new Date(data.checked_utc ?? data.retrieved_at_utc);
      if (!Array.isArray(rows) || rows[0]?.rank !== 1 ||
          !(rows[0]?.public_dti > 0 && rows[0]?.public_dti <= 1) ||
          Number.isNaN(at.getTime()) || at.getTime() > Date.now() + 3600_000) {
        throw new Error('malformed or future-dated snapshot');
      }
      score.textContent = Number(rows[0].public_dti).toFixed(4);
      const staleAfter = Number(data.stale_after_hours ?? 24);
      const stale = (Date.now() - at.getTime()) / 3600_000 > staleAfter;
      stamp.textContent = `Official public leaderboard · snapshot ${at.toLocaleDateString('en-US', { dateStyle: 'medium', timeZone: 'UTC' })} UTC${stale ? ' · STALE SNAPSHOT — check official site' : ' · snapshot only'}`;
    } catch (_) {
      score.textContent = '—';
      stamp.textContent = 'Leaderboard snapshot unavailable; open the official page for live standings.';
    }
  }
  const banner = document.querySelector('[data-card-status]');
  if (banner) {
    try {
      const response = await fetch('status.json', { cache: 'no-store' });
      if (!response.ok) throw new Error('release status unavailable');
      const data = await response.json();
      // Never dynamically turn a default-red banner green on the strength of a
      // format-only receipt: a selector and an independent organizer sample
      // must also be verified. This site has NO cleared file right now.
      banner.textContent = data.status === 'BLOCKED' && data.ok_to_submit === false
        ? 'DO NOT SUBMIT · ' + (data.problems?.join('; ') || 'automatic gate blocked the current research file')
        : 'DO NOT SUBMIT · release status is inconsistent or unverified';
    } catch (_) {
      banner.textContent = 'DO NOT SUBMIT · machine release status unavailable';
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
