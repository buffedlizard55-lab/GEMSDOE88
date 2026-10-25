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
      if (!response.ok || !currentResponse.ok || !cardResponse.ok || !tdklResponse.ok) {
        throw new Error('latest run validation unavailable');
      }
      const data = await response.json();
      const current = await currentResponse.json();
      const card = await cardResponse.json();
      const tdkl = await tdklResponse.json();
      // Fail closed. The literal audit proves the universal dense-witness stop;
      // the current TDKL feed and archived MVRD card independently bind displayed bytes.
      const consistent = data.ok_to_download_for_research === true && data.ok_to_submit === false &&
          data.decision === 'DUPLICATE_STOP' && data.validator_output?.ok === true &&
          current.candidate === 'H88-TDKL' && current.ok_to_download === true &&
          current.ok_to_submit === false && current.literal_duplicate === true &&
          current.file_sha256 === tdkl.raster_sha256 && tdkl.ok_to_submit === false &&
          card.ok_to_submit === false;
      banner.textContent = consistent
        ? 'RECORDED GATE SNAPSHOT (2026-10-24): NO CANDIDATE CLEARED · ARCHIVED TIFFS ARE RESEARCH ONLY · SUBMIT: NO — DO NOT SUBMIT'
        : 'RECORDED GATE SNAPSHOT UNVERIFIED · DO NOT SUBMIT';
    } catch (_) {
      banner.textContent = 'RECORDED GATE SNAPSHOT UNAVAILABLE · DO NOT SUBMIT';
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
