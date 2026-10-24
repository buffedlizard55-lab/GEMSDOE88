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
  // The literal audit describes the MDPS-88 file only. It writes its own line and never overwrites the current-release banner.
  const literal = document.querySelector('[data-literal-status]');
  if (literal) {
    try {
      const response = await fetch('data/literal_protocol_audit.json', { cache: 'no-store' });
      if (!response.ok) throw new Error('latest run validation unavailable');
      const data = await response.json();
      // Fail closed. A locally valid research artifact must never be presented
      // as slot-cleared or organizer-accepted, even if the old status.json is green.
      literal.textContent = (data.ok_to_download_for_research === true && data.ok_to_submit === false &&
          data.decision === 'DUPLICATE_STOP' && data.validator_output?.ok === true)
        ? 'MDPS-88 file (automated literal audit): DOWNLOAD FOR RESEARCH: YES · DO NOT SUBMIT · literal uniqueness FAILED'
        : 'Literal audit inconsistent or unverified · DO NOT SUBMIT';
    } catch (_) {
      literal.textContent = 'Literal audit unavailable · DO NOT SUBMIT';
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
