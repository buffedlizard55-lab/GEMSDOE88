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
      const response = await fetch('data/literal_protocol_audit.json', { cache: 'no-store' });
      const currentResponse = await fetch('data/current_release.json', { cache: 'no-store' });
      const cardResponse = await fetch('data/mvrd_run_card.json', { cache: 'no-store' });
      const tdklResponse = await fetch('data/tdkl88_run_card.json', { cache: 'no-store' });
      const mtasResponse = await fetch('data/mtas88_run_card.json', { cache: 'no-store' });
      const mtasExpResponse = await fetch('data/mtas88_experiment_run_card.json', { cache: 'no-store' });
      const gzzcResponse = await fetch('data/gzzc88_run_card.json', { cache: 'no-store' });
      if (!response.ok || !currentResponse.ok || !cardResponse.ok ||
          !tdklResponse.ok || !mtasResponse.ok || !mtasExpResponse.ok || !gzzcResponse.ok) {
        throw new Error('pre-flight audit unavailable');
      }
      const data = await response.json();
      const current = await currentResponse.json();
      const card = await cardResponse.json();
      const tdkl = await tdklResponse.json();
      const mtas = await mtasResponse.json();
      const mtasExp = await mtasExpResponse.json();
      const gzzc = await gzzcResponse.json();
      // All feeds must agree. GZZC is a research TIFF only. TDKL remains the
      // canonical archived current_release. MTAS generated no raster. Never
      // silently exempt the dense witness.
      const proof = mtas.preplacement_registry_proof;
      const archived = mtas.archived_research_download;
      const consistent = data.ok_to_download_for_research === true && data.ok_to_submit === false &&
          data.decision === 'DUPLICATE_STOP' && data.validator_output?.ok === true &&
          data.saturation_certificate?.witness_sha256 === proof?.witness_sha256 &&
          proof?.uncovered_allowed_pixels === 0 && proof?.directly_saturated === true &&
          proof?.universal_overlap_blocker === true && proof?.overlap_limit === 0.7 &&
          mtas.decision === 'DUPLICATE_STOP' && mtas.ok_to_submit === false &&
          mtas.new_rasters_generated === 0 && mtas.raster_sha256 === null &&
          mtas.holdout?.dti === null && mtas.validator_output?.status === 'NOT_RUN_NO_NEW_RASTER' &&
          current.candidate === 'H88-TDKL' && current.ok_to_download === true &&
          current.ok_to_submit === false && current.literal_duplicate === true &&
          current.file_sha256 === tdkl.raster_sha256 && tdkl.ok_to_submit === false &&
          archived?.sha256 === current.file_sha256 &&
          archived?.validator_output?.ok === true && archived.ok_to_submit === false &&
          card.ok_to_submit === false &&
          gzzc.ok_to_download === true && gzzc.ok_to_submit === false &&
          gzzc.verdict === 'negative' &&
          gzzc.uniqueness?.literal_dense_witness_overlap === 1.0 &&
          gzzc.uniqueness?.literal_dense_witness_pass === false &&
          mtasExp.lane === 'H88-MTAS' && mtasExp.verdict === 'negative' &&
          mtasExp.ok_to_submit === false && mtasExp.ok_to_download === true &&
          mtasExp.raster_sha256 === '2cb828939e11cf07e12be7917722f73816550ed4e297e2409b8674ac131479cc' &&
          mtasExp.validator_output?.all_checks_passed === true &&
          mtasExp.holdout?.evidence_class === 'HOLDOUT-DTI' &&
          mtasExp.organizer_confirmed_score === null;
      banner.textContent = consistent
        ? 'H88-MTAS · NEW RESEARCH TIFF: DOWNLOAD YES · SUBMIT: NO — DO NOT SUBMIT (HOLDOUT-DTI 0.0496 below bar; literal duplicate stop)'
        : 'PRE-FLIGHT AUDIT UNAVAILABLE OR INCONSISTENT — DO NOT SUBMIT';
    } catch (_) {
      banner.textContent = 'PRE-FLIGHT AUDIT UNAVAILABLE — DO NOT SUBMIT';
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
