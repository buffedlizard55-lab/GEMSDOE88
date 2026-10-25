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
      const [currentResponse, tdklResponse, literalResponse, reviewResponse, dhtcResponse] = await Promise.all([
        fetch('data/current_release.json', { cache: 'no-store' }),
        fetch('data/tdkl88_run_card.json', { cache: 'no-store' }),
        fetch('data/literal_protocol_audit.json', { cache: 'no-store' }),
        fetch('data/session_20261025_run_card.json', { cache: 'no-store' }),
        fetch('data/dhtc88_run_card.json', { cache: 'no-store' }),
      ]);
      if (![currentResponse, tdklResponse, literalResponse, reviewResponse, dhtcResponse].every(r => r.ok)) {
        throw new Error('current review validation unavailable');
      }
      const [current, tdkl, literal, review, dhtc] = await Promise.all([
        currentResponse.json(), tdklResponse.json(), literalResponse.json(),
        reviewResponse.json(), dhtcResponse.json(),
      ]);
      // The session card proves the fresh review's no-generation decision; the
      // current-release and TDKL cards bind the existing research-download bytes.
      const consistent = current.candidate === 'H88-TDKL' &&
          current.file === tdkl.raster?.file &&
          current.file_sha256 === tdkl.raster_sha256 &&
          current.ok_to_download === true && current.ok_to_submit === false &&
          current.literal_duplicate === true && current.duplicate === true &&
          tdkl.verdict === 'negative' && tdkl.ok_to_download === true &&
          tdkl.ok_to_submit === false &&
          literal.decision === 'DUPLICATE_STOP' &&
          literal.saturation_certificate?.universal_overlap_blocker === true &&
          literal.validator_output?.ok === true &&
          review.decision === 'DUPLICATE_STOP' &&
          review.ok_to_download_for_research === true && review.ok_to_submit === false &&
          review.experiment_budget?.new_rasters_generated === 0 &&
          review.experiment_budget?.experiments_run_this_session === 0 &&
          review.correlation_overlap_vs_registry?.universal_nonempty_candidate_blocker === true &&
          review.existing_research_artifact?.sha256 === dhtc.raster_sha256 &&
          dhtc.ok_to_download === true && dhtc.ok_to_submit === false &&
          dhtc.verdict === 'negative';
      banner.textContent = consistent
        ? 'NO CANDIDATE CLEARED · H88-TDKL DOWNLOAD FOR RESEARCH: YES · SUBMIT: NO — DO NOT SUBMIT (DUPLICATE_STOP)'
        : 'DO NOT SUBMIT · current review status is inconsistent or unverified';
    } catch (_) {
      banner.textContent = 'DO NOT SUBMIT · machine review status unavailable';
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
