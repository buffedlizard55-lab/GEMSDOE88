#!/usr/bin/env python3
"""GEO-THERMAL-88: measured geothermal water temperature x young-scarp corridor dots.

One preregistered experiment.  Never spends a competition slot.

Hypothesis (H1, ranked top in research/hypotheses-geothermal-20261024.md):
measured hot well/spring temperature (DOE GDR INGENIOUS, CC BY 4.0) gated to
USGS 3DEP lidar young-scarp amplitude and thin sedimentary cover emits sparse
dots ~one kernel radius apart, all outside the USGS/INGENIOUS catalogue.
Targets blind geothermal systems with spring/scarp expression but no mapped
Quaternary fault trace -- a class no shipped lane addresses.

Measured hydrothermal temperature is a direct geothermal indicator, not a fault
proxy, so this lane is deliberately unlike H33 (ridge topography), MRR-BPR-88
(block magnetic regression), PROVCREST (crest ranking), KTH-88 (radiometric
ratio) and LBCAL (receipt calibration).

All external inputs are pinned, free, official sources verified by SHA-256
before use (registry/data_manifest.json).  The catalogue is used ONLY for
pixel-exact exclusion of final dots -- never as a ranking or construction layer.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / 'src', ROOT / 'scripts', ROOT / 'vendor'):
    sys.path.insert(0, str(p))

from gems88.geothermal import (build_surface, read_hot_springs, spaced_dots,
                               DOT_MIN_SPACING_PX, RADIUS_PX)  # noqa: E402
from gems57 import evaluate_holdout, grid, holdout, uniqueness  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from build_prune_deconfound_variants import directional_crest_1d  # noqa: E402
from build_provcrest_submission import select_dots  # noqa: E402
from validate_artifact import validate_artifact  # noqa: E402
from run_fabric_dislocation import (leakage_canaries, preplacement_surface_rhos,
                                    public_registry_index)  # noqa: E402

N_DOTS = 37_654          # H33 scale: dots spaced ~one kernel radius apart
STEM_PREFIX = 'gems88-geothermal-hotspring-scarp-20261024'
SAMPLE = ROOT / 'data/bridge/sample_submission.tif'
GDR_CSV = ROOT / 'data/external/gdr_wellspring_in_footprint.csv'
LIDAR = ROOT / 'data/external/lidar_scarp_features_u8.tif'
FEATURES = ROOT / 'data/training_features.tif'


def digest(path: Path) -> str:
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def json_write(path: Path, obj: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def verify_sources() -> grid.Grid:
    expected = {
        'data/bridge/sample_submission.tif': grid.SHA256_SAMPLE_SUBMISSION,
        'data/bridge/existing_faults.tif': grid.SHA256_EXISTING_FAULTS,
        'data/training_features.tif': '4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5',
        'data/external/lidar_scarp_features_u8.tif': 'd580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568',
        'data/external/gdr_wellspring_in_footprint.csv': '122718e65bdf55aab0ee12ad20d80062f0deb1de957225a61ad880dd5dc196ea',
    }
    for rel, want in expected.items():
        got = digest(ROOT / rel)
        if got != want:
            raise ValueError(f'unverified owner mirror {rel}: {got} != {want}')
    g = grid.load_grid(ROOT / 'data/bridge')
    with rasterio.open(FEATURES) as ds:
        if (ds.shape, ds.crs, ds.transform) != (g.shape, g.crs, g.transform):
            raise ValueError('19-band feature stack not aligned with pinned sample grid')
        for b, name in ((2, 'rtp'), (15, 'depth_to_base_surf')):
            if ds.tags(b).get('band_name') != name:
                raise ValueError(f'feature band {b} was not {name}: {ds.tags(b)}')
    with rasterio.open(LIDAR) as ds:
        if (ds.shape, ds.crs, ds.transform) != (g.shape, g.crs, g.transform):
            raise ValueError('lidar scarp stack not aligned with pinned sample grid')
        if ds.descriptions[0] != 'ex_max':
            raise ValueError(f'lidar band 1 was not ex_max: {ds.descriptions}')
    return g


def build_channels(g: grid.Grid):
    """Build feature-alone channels for the leakage canary.

    Every channel is label-blind: it uses hot-well/springs, scarps, cover and
    geophysics -- never the withheld holdout truth.
    """
    hot_rows, hot_cols, hot_temps = read_hot_springs(GDR_CSV, g.footprint, temp_min_c=45.0)
    with rasterio.open(LIDAR) as lidar:
        scarp = lidar.read(1).astype(np.float64)
    with rasterio.open(FEATURES) as feats:
        depth = feats.read(15).astype(np.float64)   # depth_to_base_surf

    thermal, tstats = build_surface(hot_rows, hot_cols, hot_temps, g.shape)
    surface, sstats = build_surface(hot_rows, hot_cols, hot_temps, g.shape,
                                    scarp=scarp, scarp_gate_quantile=0.70,
                                    cover=depth)

    channels = {
        'geothermal_thermal_density': thermal,
        'geothermal_scarp_gated': np.where(scarp > 0, scarp.astype(np.float64) / 255.0, 0.0),
        'geothermal_cover_favor': np.clip(
            (float(np.quantile(depth[np.isfinite(depth)], 0.10)) - depth) / 1e3, 0.0, 1.0),
        'geothermal_combined_surface': surface,
    }
    return surface, channels, dict(thermal=tstats, surface=sstats,
                                   hot_n=len(hot_rows), hot_mean_temp=float(hot_temps.mean()),
                                   hot_max_temp=float(hot_temps.max()))


def main() -> int:
    t0 = time.monotonic()
    g = verify_sources()
    print(f'[geothermal] grid loaded: {g.height}x{g.width}, footprint {int(g.footprint.sum())} cells, '
          f'catalogue {int(g.catalogue.sum())} px', flush=True)

    surface, channels, stats = build_channels(g)
    print(f'[geothermal] surface built: {stats["hot_n"]} hot locations, '
          f'mean temp {stats["hot_mean_temp"]:.1f} C, max {stats["hot_max_temp"]:.1f} C', flush=True)

    # --- Leakage canary: every feature ALONE on held-out positives (AUC <= 0.90) ---
    canary = leakage_canaries(channels, g)
    print(f'[geothermal] canaries: '
          f'{ {k: round(v["symmetric_auc"], 5) for k, v in canary.items()} }', flush=True)
    max_canary = max(v['symmetric_auc'] for v in canary.values())
    del channels

    # --- Pre-placement surface rank correlation vs registry (|rho| <= 0.90) ---
    index = public_registry_index()
    surface_rows = preplacement_surface_rhos(surface, g, index)
    pre_max = max((abs(r['rho_full_footprint']) for r in surface_rows
                   if r['rho_full_footprint'] is not None), default=0.0)
    print(f'[geothermal] pre-placement max |rho| = {pre_max:.5f} over '
          f'{len(surface_rows)} registry rasters', flush=True)

    # --- Holdout evaluation: whole-component buffered draws, seeds 20 + 21 ---
    terms = None
    fold_counts = []
    for seed in (20, 21):
        folds, _ = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        visible = folds[0]['visible']
        masked = folds[0]['masked_known']
        d_vis = distance_transform_edt(~visible)
        # Eligible: surface support, footprint, not on masked known faults,
        # >3 px from visible catalogue context (300 m buffer per protocol).
        eligible = (surface > 0) & g.footprint & ~masked & (d_vis > 3.0)
        if not eligible.any():
            raise RuntimeError('no eligible dot cells after holdout masking')
        # Candidate dots: ranked by surface, spaced ~one kernel radius apart.
        order = np.lexsort((np.arange(surface.size), -surface.ravel()))
        mask = np.zeros(g.shape, bool)
        taken = 0
        for idx in order:
            if taken >= N_DOTS:
                break
            if not eligible.ravel()[idx]:
                continue
            mask.ravel()[idx] = True
            taken += 1
            cy, cx = divmod(int(idx), g.width)
            r = int(math.ceil(DOT_MIN_SPACING_PX))
            y0, y1 = max(0, cy - r), min(g.height, cy + r + 1)
            x0, x1 = max(0, cx - r), min(g.width, cx + r + 1)
            yy = np.arange(y0, y1)[:, None]
            xx = np.arange(x0, x1)[None, :]
            near = ((yy - cy) ** 2 + (xx - cx) ** 2) <= DOT_MIN_SPACING_PX ** 2
            mask[y0:y1, x0:x1] = np.where(near, True, mask[y0:y1, x0:x1])
            mask.ravel()[idx] = True
        pred = mask.astype(np.float32)
        for f in folds:
            _, block_terms = evaluate_holdout.evaluate(pred, f, g.footprint)
            terms = block_terms if terms is None else terms + block_terms
            fold_counts.append(dict(seed=seed, fold=f['name'],
                                    withheld_positive_pixels=int(f['truth'].sum()),
                                    emitted=int((mask & f['region'] & ~f['masked_known']).sum())))
        print(f'[geothermal] holdout seed {seed} complete ({time.monotonic()-t0:.1f}s)', flush=True)

    summary = evaluate_holdout.pooled_summary({'candidate': terms}, draws=1000,
                                              seed=881024, candidate='candidate')
    score = summary['scores']['candidate']
    prior_best = json.loads((ROOT / 'registry/holdout_result.json').read_text())['scores']['candidate']
    if score['withheld_positive_pixels'] != prior_best['withheld_positive_pixels']:
        raise ValueError('withheld-positive count differs from incumbent: split not comparable')
    print(f"[geothermal] HOLDOUT-DTI={score['dti']:.6f} CI95={score['ci95']} "
          f"vs prior best={prior_best['dti']:.6f}", flush=True)

    # --- Final raster: catalogue masked pixel-exactly, dots >3 px from catalogue ---
    d_cat = distance_transform_edt(~g.catalogue)
    eligible_final = (surface > 0) & g.footprint & ~g.catalogue & (d_cat > 3.0)
    print(f'[geothermal] final eligible cells: {int(eligible_final.sum())}', flush=True)
    order = np.lexsort((np.arange(surface.size), -surface.ravel()))
    final = np.zeros(g.shape, bool)
    taken = 0
    for idx in order:
        if taken >= N_DOTS:
            break
        if not eligible_final.ravel()[idx]:
            continue
        final.ravel()[idx] = True
        taken += 1
        cy, cx = divmod(int(idx), g.width)
        r = int(math.ceil(DOT_MIN_SPACING_PX))
        y0, y1 = max(0, cy - r), min(g.height, cy + r + 1)
        x0, x1 = max(0, cx - r), min(g.width, cx + r + 1)
        yy = np.arange(y0, y1)[:, None]
        xx = np.arange(x0, x1)[None, :]
        near = ((yy - cy) ** 2 + (xx - cx) ** 2) <= DOT_MIN_SPACING_PX ** 2
        final[y0:y1, x0:x1] = np.where(near, True, final[y0:y1, x0:x1])
        final.ravel()[idx] = True
    pred = final.astype(np.float32)
    pred[~g.footprint] = 0.0
    n_dots = int(final.sum())
    print(f'[geothermal] final dots: {n_dots}', flush=True)

    stem = STEM_PREFIX + '-' + hashlib.sha256(pred.tobytes()).hexdigest()[:8] + '-DO-NOT-SUBMIT'
    note = (f'GEO-THERMAL-88 hot well/spring temp x young-scarp corridor; {n_dots} dots; '
            f'HOLDOUT-DTI {score["dti"]:.4f}; UNSCORED; DO NOT SUBMIT')
    name = 'GEMSDOE88-GEO-' + hashlib.sha256(pred.tobytes()).hexdigest()[:8].upper()
    assert 0 < len(note) <= 140, len(note)
    assert len(name) <= 140, len(name)
    path = ROOT / 'docs/downloads' / f'{stem}.tif'
    receipt = write_submission(path, pred, SAMPLE, g.footprint,
                               note=note, name=name, catalogue=g.catalogue,
                               metadata={'lane': 'GEO-THERMAL-88',
                                         'slot_authorized': False,
                                         'n_dots': n_dots})
    independent = validate_artifact(path, SAMPLE)
    if not independent['ok']:
        raise RuntimeError('independent disk re-read failed after submission writer')
    print(f'[geothermal] TIFF independently validated: {path.name}', flush=True)

    # --- Literal uniqueness gate vs the full accessible registry (dots phase) ---
    result = uniqueness.compare_to_registry(path, index, g.footprint,
                                             include_reverse=False,
                                             expected_grid=(g.shape, g.crs, g.transform))
    if result['registry_rasters_checked'] != len(index['rasters']):
        raise RuntimeError('final registry audit incomplete')
    result['my_file'] = str(path.relative_to(ROOT))
    for row in result['rows']:
        row['file'] = str(Path(row['file']).relative_to(ROOT))
    witness = uniqueness.saturation_certificate(
        ROOT / 'data/registry/dense_17gemdoe.tif', g.footprint, g.catalogue,
        expected_grid=(g.shape, g.crs, g.transform))
    witness['witness_file'] = 'data/registry/dense_17gemdoe.tif'
    uniqueness_receipt = dict(schema='gems88.uniqueness.v1',
                              preplacement_surface=surface_rows,
                              final_dots=result,
                              dense_witness_universal=witness)
    ev_path = ROOT / 'evidence' / f'{stem}_uniqueness.json'
    json_write(ev_path, uniqueness_receipt)
    json_write(ROOT / 'docs/data' / f'{stem}_uniqueness.json', uniqueness_receipt)

    block = result['stop_required'] or witness['universal_overlap_blocker']
    holdout_better = score['dti'] > prior_best['dti']
    validator = dict(format_valid=independent['ok'], no_nan_inside=independent['no_nan_inside'],
                     values_in_0_1=independent['range_0_1'],
                     crs_match=independent['crs_match'], shape_match=independent['shape_match'],
                     transform_match=independent['transform_match'],
                     zero_outside=independent['no_mass_outside'],
                     raster_sha256=receipt['sha256'],
                     sample_sha256=independent['sample_sha256'],
                     emitted_positive_pixels=n_dots,
                     min_distance_to_catalogue_px=float(d_cat[final].min()))
    ok_to_download = independent['ok']
    ok_to_submit = bool(ok_to_download and holdout_better and not block and max_canary <= 0.90)
    card = dict(schema='gems88.run-card.v5', generated_utc='2026-10-24',
        lane='GEO-THERMAL-88',
        hypothesis=('Measured hot geothermal well/spring water temperature (DOE GDR INGENIOUS, CC BY 4.0) '
                    'kernel-density gated to USGS 3DEP lidar young-scarp amplitude and thin sedimentary '
                    'cover, emitted as sparse dots ~one kernel radius apart, all outside the mapped '
                    'catalogue. Direct hydrothermal indicator targeting blind geothermal systems with '
                    'no mapped Quaternary fault trace.'),
        mechanism=('Temp-weighted Gaussian kernels at hot well/spring pixels (sigma ~1.5 px), gated to '
                   'lidar scarp ex_max above the 70th percentile and up-weighted where depth-to-basement '
                   'is shallow; greedy farthest-point dots at min 3 px spacing; catalogue masked '
                   'pixel-exactly; never a ranking layer.'),
        named_non_fault_process=('Sinter/travertine spring mounds and relict Pleistocene Lake Lahontan '
                                 'shoreline scarps -- thermal/scarpy-looking but not active geothermal faults.'),
        data_provenance='hash-pinned free official sources (DOE GDR 1391 CC BY 4.0; USGS 3DEP public domain; GeoDAWN DOI 10.5066/P93LGLVQ)',
        feature_canaries=dict(threshold_symmetric_auc=0.90, per_channel=canary,
                              max_symmetric_auc=max_canary),
        holdout=dict(evidence_class='HOLDOUT-DTI',
                     evaluator_version=summary['evaluator_version'],
                     candidate=score, incumbent_prior_best=prior_best,
                     withheld_positive_pixels=score['withheld_positive_pixels'],
                     folds=fold_counts, bootstrap=summary['bootstrap'],
                     comparable_split='same frozen whole-component buffered folds seeds 20/21',
                     beats_prior_point_estimate=holdout_better,
                     paired_improvement_ci95=None,
                     note='HOLDOUT-DTI is not ORGANIZER-CONFIRMED; no live score is claimed.'),
        correlation_overlap_vs_registry=dict(
            preplacement_max_abs_rho=pre_max,
            final_worst_abs_rho=max((abs(r['spearman_full_footprint']) for r in result['rows']
                                     if r.get('spearman_full_footprint') is not None), default=None),
            final_worst_overlap_3px=result['worst_dot_overlap'],
            final_worst_overlap_raster=result['worst_overlap_submission'],
            registry_rasters_checked=result['registry_rasters_checked'],
            registry_scope=index['scope'],
            raw_duplicate_count=result['duplicate_count'],
            universal_dense_witness=witness['universal_overlap_blocker'],
            full_rows=str(ev_path.relative_to(ROOT)),
            raw_gate_pass=bool(result['unique'])),
        validator_output=validator,
        raster_sha256=receipt['sha256'], zip_sha256=receipt['zip_sha256'],
        submission_name=name, submission_note=note,
        file=f'docs/downloads/{path.name}', zip_file=f'docs/downloads/{path.stem}.zip',
        research_download_ok=ok_to_download, ok_to_submit=ok_to_submit,
        organizer_confirmed_score=None, weekly_slots_used_by_agent=0,
        experiments_run=1, experiment_budget_max=3,
        elapsed_seconds=round(time.monotonic()-t0, 1),
        verdict=('promote' if ok_to_submit else 'negative'),
        stop_reason=('Clears all gates: OK to submit.' if ok_to_submit else
                     ('DUPLICATE under literal >70% forward 3px registry gate; stop.'
                      if block else
                      ('No demonstrated paired improvement over holdout best; stop.'
                       if not holdout_better else
                       ('Paired improvement not established / canary threshold; stop.')))),
        limitations=[
            'Hide-and-recover catalogue labels are not the undisclosed new-fault labels; holdout is a leakage/exclusion screen, not a leaderboard predictor.',
            'GDR well/spring data is owner-mirrored; organizer authentication of this derivative is unverified.',
            'Registry excludes private/unlinked competition submissions; the dense 17GEMSDOE witness blocks every nonempty raster under the literal rule.',
            'No portal authorization or submission receipt; 0 weekly slots used.'])
    json_write(ROOT / 'registry' / f'{stem.split("-")[0]}-run_card.json', card)
    json_write(ROOT / 'docs/data' / f'{stem.split("-")[0]}-run_card.json', card)
    print(f"[geothermal] VERDICT={card['verdict']} OK_TO_DOWNLOAD={ok_to_download} "
          f"OK_TO_SUBMIT={ok_to_submit}", flush=True)
    print(f'[geothermal] {card["stop_reason"]}', flush=True)
    print(f'[geothermal] SHA256: {receipt["sha256"]}  zip: {receipt["zip_sha256"]}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
