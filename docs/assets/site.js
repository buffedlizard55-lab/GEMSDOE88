// Static, fail-closed display. Local machine evidence is never an organizer receipt.
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
      stamp.textContent = `Official public leaderboard · snapshot ${at.toLocaleDateString('en-US', { dateStyle: 'medium', timeZone: 'UTC' })} UTC${stale ? ' · STALE' : ' · snapshot only'}`;
    } catch (_) {
      score.textContent = '—';
      stamp.textContent = 'Snapshot unavailable; use the official page for live standings.';
    }
  }

  const banners = document.querySelectorAll('[data-card-status]');
  if (banners.length) {
    try {
      const [releaseResponse, statusResponse] = await Promise.all([
        fetch('data/current_release.json', { cache: 'no-store' }),
        fetch('status.json', { cache: 'no-store' }),
      ]);
      if (!releaseResponse.ok || !statusResponse.ok) throw new Error('status unavailable');
      const release = await releaseResponse.json();
      const status = await statusResponse.json();
      const safelyNegative = release.candidate_id === 'MRR-COH-88' &&
        release.research_download_ok === true && release.format_valid === true &&
        release.unique === true && release.ok_to_submit === false &&
        release.verdict === 'negative' && status.status === 'BLOCKED' &&
        status.ok_to_submit === false && status.raster_sha256 === release.raster_sha256;
      for (const banner of banners) {
        banner.textContent = safelyNegative
          ? 'MRR-COH-88 · DOWNLOAD FOR RESEARCH: YES · OK TO SUBMIT: NO · DO NOT SUBMIT'
          : 'DO NOT SUBMIT · machine release status unavailable or inconsistent';
      }
    } catch (_) {
      for (const banner of banners) {
        banner.textContent = 'DO NOT SUBMIT · machine release status unavailable';
      }
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
