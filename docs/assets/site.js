// The primary decision is rendered at build time. Runtime evidence may only
// confirm the saved negative decision or fail closed; it never authorizes a slot.
(async () => {
  const banner = document.querySelector('[data-card-status]');
  if (banner) {
    try {
      const responses = await Promise.all([
        fetch('data/sdtl88_run_card.json', { cache: 'no-store' }),
        fetch('data/current_release.json', { cache: 'no-store' }),
        fetch('data/download_audit.json', { cache: 'no-store' }),
        fetch('status.json', { cache: 'no-store' }),
      ]);
      if (responses.some(response => !response.ok)) throw new Error('audit unavailable');
      const [card, current, audit, status] = await Promise.all(responses.map(r => r.json()));
      const file = Array.isArray(audit.artifacts)
        ? audit.artifacts.find(row => `docs/downloads/${row.file}` === current.file) : null;
      const at = new Date(audit.checked_at_utc);
      const promote = card.verdict === 'promote' && card.ok_to_submit === true;
      const gates = card.holdout_dti?.success === true && card.leakage_canary?.passed === true &&
        card.correlation_overlap_vs_registry?.surface_ok === true &&
        card.correlation_overlap_vs_registry?.dots_ok === true && card.validator?.ok === true;
      const consistent = card.schema === 'gems88.run_card.v2' && card.lane === 'H88-SDTL' &&
        (promote ? gates : true) &&
        current.schema === 'gems88.current-release.v3' && current.file_sha256 === card.raster?.sha256 &&
        current.ok_to_download === true && current.ok_to_submit === promote &&
        current.approved_for_weekly_slot === false &&
        audit.canonical_sha256 === current.file_sha256 && audit.ok_to_submit === promote &&
        (audit.protocol_eligible_count > 0) === promote && audit.tiff_count === audit.artifacts.length &&
        status.ok_to_submit === promote && status.raster_sha256 === current.file_sha256 &&
        file?.sha256 === current.file_sha256 && file?.zip_sha256 === current.zip_sha256 &&
        file?.research_download_ok === true && file?.format_valid === true &&
        file?.independent_decoders_agree === true && file?.zip_one_byte_identical_tif === true &&
        file?.negative_filename_markers === !promote && (file?.ok_to_submit === true) === promote &&
        file?.validator_output?.ok === true &&
        !Number.isNaN(at.getTime()) && at.getTime() <= Date.now() + 3600_000;
      banner.textContent = !consistent
        ? 'PRE-FLIGHT AUDIT UNAVAILABLE OR INCONSISTENT — DO NOT SUBMIT'
        : (promote ? 'H88-SDTL · DOWNLOAD: YES · SUBMIT: YES — OK TO DOWNLOAD AND SUBMIT'
                   : 'H88-SDTL · DOWNLOAD: YES · SUBMIT: NO — DO NOT SUBMIT');
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
        ? `LIVE MACHINE GATE VERIFIED · ${bpwd.lane} HOLDOUT-DTI ${Number(bpwd.holdout_dti.candidate_exp03.dti).toFixed(6)} RECORD · 5/5 DISCRIMINATING GATES PASS · DOWNLOAD: YES · SUBMIT: NO — DO NOT SUBMIT`
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
