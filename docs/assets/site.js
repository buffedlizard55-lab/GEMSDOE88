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
      const [releaseResponse, auditResponse] = await Promise.all([
        fetch('data/current_release.json', { cache: 'no-store' }),
        fetch('data/kth88_validation.json', { cache: 'no-store' }),
      ]);
      if (!releaseResponse.ok || !auditResponse.ok) throw new Error('current release audit unavailable');
      const [release, audit] = await Promise.all([releaseResponse.json(), auditResponse.json()]);
      // Fail closed: both the dated current feed and byte-bound local audit must
      // agree. Format validity is never organizer acceptance or slot approval.
      const consistent = release.candidate_id === 'KTH-88' &&
        release.ok_to_download === true && release.ok_to_submit === false &&
        release.duplicate === true && release.organizer_confirmed === null &&
        release.file_sha256 === audit.tif_sha256 &&
        release.zip_sha256 === audit.zip_sha256 &&
        audit.ok_to_download === true && audit.ok_to_submit === false &&
        audit.local_format_audit?.ok === true &&
        audit.tif_and_single_member_zip_validated === true;
      banner.textContent = consistent
        ? 'KTH-88 · OK TO DOWNLOAD FOR RESEARCH: YES · OK TO SUBMIT: NO · DO NOT SUBMIT · DUPLICATE · NO SLOT APPROVED'
        : 'DO NOT SUBMIT · current release feed and byte audit are inconsistent or unverified';
    } catch (_) {
      banner.textContent = 'DO NOT SUBMIT · current release status unavailable';
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
