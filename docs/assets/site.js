// The primary decision is rendered at build time. Runtime evidence may only
// confirm the saved negative decision or fail closed; it never authorizes a slot.
(async () => {
  const banner = document.querySelector('[data-card-status]');
  if (banner) {
    try {
      const responses = await Promise.all([
        fetch('data/mtas88_run_card.json', { cache: 'no-store' }),
        fetch('data/current_release.json', { cache: 'no-store' }),
        fetch('data/download_audit.json', { cache: 'no-store' }),
        fetch('status.json', { cache: 'no-store' }),
        fetch('data/vcaz88_run_card.json', { cache: 'no-store' }),
      ]);
      if (responses.some(response => !response.ok)) throw new Error('audit unavailable');
      const [preflight, current, audit, status, vcaz] = await Promise.all(responses.map(r => r.json()));
      const proof = preflight.preplacement_registry_proof;
      const file = Array.isArray(audit.artifacts)
        ? audit.artifacts.find(row => `docs/downloads/${row.file}` === current.file) : null;
      const vcazFile = Array.isArray(audit.artifacts)
        ? audit.artifacts.find(row => `docs/downloads/${row.file}` === vcaz.download) : null;
      const at = new Date(audit.checked_at_utc);
      const consistent = preflight.decision === 'DUPLICATE_STOP' &&
        preflight.ok_to_submit === false && preflight.new_rasters_generated === 0 &&
        preflight.raster_sha256 === null && preflight.holdout?.dti === null &&
        proof?.universal_overlap_blocker === true && proof?.directly_saturated === true &&
        proof?.allowed_pixels > 0 && proof?.uncovered_allowed_pixels === 0 &&
        proof?.directly_covered_allowed_pixels === proof?.allowed_pixels && proof?.overlap_limit === 0.7 &&
        audit.preplacement_registry_proof?.witness_sha256 === proof?.witness_sha256 &&
        audit.canonical_sha256 === current.file_sha256 && audit.ok_to_submit === false &&
        audit.protocol_eligible_count === 0 && audit.tiff_count === audit.artifacts.length &&
        current.ok_to_download === true && current.ok_to_submit === false &&
        current.literal_duplicate === true && current.approved_for_weekly_slot === false &&
        status.status === 'BLOCKED' && status.ok_to_submit === false &&
        status.raster_sha256 === current.file_sha256 && status.approved_for_weekly_slot === false &&
        file?.sha256 === current.file_sha256 && file?.zip_sha256 === current.zip_sha256 &&
        file?.research_download_ok === true && file?.format_valid === true &&
        file?.independent_decoders_agree === true && file?.zip_one_byte_identical_tif === true &&
        file?.negative_filename_markers === true && file?.ok_to_submit === false &&
        file?.validator_output?.ok === true &&
        vcaz?.lane === 'H88-VCAZ' && vcaz?.verdict === 'negative' &&
        vcaz?.ok_to_download === true && vcaz?.ok_to_submit === false &&
        vcaz?.raster_sha256 === '34224a7c2163758196d0a6de8708f99943c77745172a278bdb11333ece6a6b12' &&
        vcaz?.organizer_confirmed_score === null &&
        vcazFile?.sha256 === vcaz.raster_sha256 && vcazFile?.zip_sha256 === vcaz.zip_sha256 &&
        vcazFile?.research_download_ok === true && vcazFile?.ok_to_submit === false &&
        !Number.isNaN(at.getTime()) && at.getTime() <= Date.now() + 3600_000;
      banner.textContent = consistent
        ? 'NO FILE APPROVED · ARCHIVED RESEARCH DOWNLOAD: YES · SUBMIT: NO — DO NOT SUBMIT'
        : 'PRE-FLIGHT AUDIT UNAVAILABLE OR INCONSISTENT — DO NOT SUBMIT';
    } catch (_) {
      banner.textContent = 'PRE-FLIGHT AUDIT UNAVAILABLE — DO NOT SUBMIT';
    }
  }
  const bpwdBanner = document.querySelector('[data-bpwd-status]');
  if (bpwdBanner) {
    try {
      const [r, g] = await Promise.all([
        fetch('data/bpwd88_run_card.json', { cache: 'no-store' }),
        fetch('data/bpwd88_gate_v3.json', { cache: 'no-store' }),
      ]);
      if (!r.ok || !g.ok) throw new Error('bpwd feed unavailable');
      const [bpwd, gv] = await Promise.all([r.json(), g.json()]);
      const ok = bpwd.ok_to_download === true && bpwd.ok_to_submit === false &&
        bpwd.all_5_discriminating_gates_pass === true && bpwd.beats_hgvc_holdout_best === true &&
        bpwd.verdict === 'negative' && gv.ok_to_submit === false &&
        bpwd.raster_sha256 === gv.sha256;
      bpwdBanner.textContent = ok
        ? `HISTORICAL RESEARCH RECORD · ${bpwd.lane} HOLDOUT-DTI ${Number(bpwd.holdout_dti.candidate_exp03.dti).toFixed(6)} RECORD · NOT A NEW SCORE · DOWNLOAD: YES · SUBMIT: NO — DO NOT SUBMIT`
        : 'BPWD GATE INCONSISTENT — DO NOT SUBMIT';
    } catch (_) {
      bpwdBanner.textContent = 'BPWD PRE-FLIGHT UNAVAILABLE — DO NOT SUBMIT';
    }
  }
  // Any inherited leaderboard widget is explicitly historical. No live request
  // to DrivenData, no guessed current rank, and no organizer receipt is implied.
  const score = document.querySelector('[data-feed-score]');
  const stamp = document.querySelector('[data-feed-stamp]');
  if (score && stamp) {
    score.textContent = 'Not verified';
    stamp.textContent = 'Archived public observations are not a live leaderboard or a submission receipt.';
  }
  for (const button of document.querySelectorAll('[data-copy]')) {
    const original = button.textContent;
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.copy);
        button.textContent = 'Copied';
        setTimeout(() => { button.textContent = original; }, 2000);
      } catch (_) {
        button.textContent = 'Copy unavailable';
      }
    });
  }
})();
