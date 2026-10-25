"""Shared literal parallel-run gates.

Forward overlap above 0.70 or rank correlation above 0.90 blocks against ANY
registry raster. Dense/lattice priors are not exempt; reverse overlap and
Jaccard are diagnostic only. Incomplete inventories fail closed. Earlier
module documentation described an informative-only exception, but the actual
comparison and summary functions already implement the literal user rule.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import binary_dilation
from scipy.stats import rankdata, spearmanr
from .metric import RADIUS_PX

RHO_LIMIT = 0.90
OVERLAP_LIMIT = 0.70
JACCARD_LIMIT = 0.50
ROOT = Path(__file__).resolve().parents[2]


def _dots(a):
    a = np.asarray(a)
    return np.isfinite(a) & (a > 0)


def _near(support, radius_px=RADIUS_PX):
    support = np.asarray(support, dtype=bool)
    if radius_px < 0 or support.ndim != 2:
        return np.zeros_like(support, dtype=bool) if radius_px < 0 else support.copy()
    r = int(np.floor(radius_px))
    if r == 0:
        return support.copy()
    r2 = float(radius_px) * float(radius_px)
    # Exact separable decomposition of {dy^2 + dx^2 <= radius_px^2}:
    # |dy| <= floor(radius_px), and for each |dy|, |dx| ranges contiguously over
    # 0..floor(sqrt(radius_px^2 - dy^2)). Identical bit-for-bit to
    # scipy.ndimage.binary_dilation(..., border_value=0) for all grids and radii.
    max_dx_by_abs_dy = {ay: int(np.floor(np.sqrt(max(0.0, r2 - ay * ay)))) for ay in range(r + 1)}
    row_dilated: dict[int, np.ndarray] = {}
    for m in sorted(set(max_dx_by_abs_dy.values())):
        if m == 0:
            row_dilated[0] = support
        else:
            prev_m = max((k for k in row_dilated if k < m), default=None)
            cur = row_dilated[prev_m].copy() if prev_m is not None else support.copy()
            start = (prev_m + 1) if prev_m is not None else 1
            for dx in range(start, m + 1):
                if dx < support.shape[1]:
                    cur[:, dx:] |= support[:, :-dx]
                    cur[:, :-dx] |= support[:, dx:]
            row_dilated[m] = cur
    out = row_dilated[max_dx_by_abs_dy[0]].copy()
    for ay in range(1, r + 1):
        if ay >= support.shape[0]:
            break
        w = row_dilated[max_dx_by_abs_dy[ay]]
        out[ay:, :] |= w[:-ay, :]
        out[:-ay, :] |= w[ay:, :]
    return out


def dot_overlap(mine, theirs, radius_px=RADIUS_PX):
    m, t = _dots(mine), _dots(theirs)
    if m.shape != t.shape:
        raise ValueError('overlap grid shape mismatch')
    if not m.any() or not t.any():
        return 0.0
    return float(_near(t, radius_px)[m].mean())


def _jaccard(a, b):
    u = int((a | b).sum())
    return float((a & b).sum() / u) if u else 0.0


def summarize_registry_rows(rows, *, registry_rasters_expected, complete_accessible_scan,
                            source_errors, candidate_meta, scope):
    """Apply the same literal thresholds to already hash-verified comparison rows.

    This allows a complete immutable prior audit to be extended with only newly
    published blobs, instead of re-downloading hundreds of unchanged rasters.
    The caller must prove candidate identity and the completeness/count of the
    combined registry before passing ``complete_accessible_scan=True``.
    """
    rows = list(rows)
    source_errors = list(source_errors or [])
    expected = int(registry_rasters_expected)
    checked = [r for r in rows if 'error' not in r]
    errors = [r for r in rows if 'error' in r]
    complete = bool(complete_accessible_scan and expected == len(rows)
                    and not errors and not source_errors)
    # The inherited stop gate is literal: only Spearman > 0.90 or forward
    # 3-pixel overlap > 0.70 (plus byte/pixel identity safeguards) can block.
    # Jaccard is reported for diagnosis, never substituted as a new threshold.
    flags = [r for r in checked if any(r.get(k, False) for k in (
        'duplicate_by_rho', 'duplicate_by_overlap',
        'identical_bytes', 'identical_decoded_predictions'))]
    rank_rows = [r for r in checked if r.get('spearman_full_footprint') is not None]
    worst_rho = max(rank_rows, key=lambda r: r['spearman_full_footprint'], default=None)
    worst_ov = max(checked, key=lambda r: r['my_dots_within_3px_of_theirs'], default=None)
    worst_jac = max(checked, key=lambda r: r['jaccard_dot_sets'], default=None)
    my_dot_count = int(candidate_meta['my_dots'])
    norm = bool(candidate_meta['candidate_rank_variation'])
    unique = complete and my_dot_count > 0 and norm and not flags
    return dict(
        my_file=candidate_meta.get('my_file'), evidence_class='REGISTRY-MEASUREMENT',
        my_dots=my_dot_count,
        candidate_decoded_sha256=candidate_meta.get('candidate_decoded_sha256'),
        candidate_file_sha256=candidate_meta.get('candidate_file_sha256'),
        rho_limit=RHO_LIMIT, overlap_limit=OVERLAP_LIMIT, jaccard_limit=JACCARD_LIMIT,
        registry_rasters_expected=expected, registry_rasters_checked=len(checked),
        complete_accessible_scan=complete, missing_or_invalid=len(errors),
        source_errors=source_errors,
        worst_spearman_full_footprint=(worst_rho['spearman_full_footprint'] if worst_rho else None),
        worst_rho_submission=(worst_rho['submission'] if worst_rho else None),
        worst_dot_overlap=(worst_ov['my_dots_within_3px_of_theirs'] if worst_ov else None),
        worst_overlap_submission=(worst_ov['submission'] if worst_ov else None),
        worst_jaccard_dot_sets=(worst_jac['jaccard_dot_sets'] if worst_jac else None),
        worst_jaccard_submission=(worst_jac['submission'] if worst_jac else None),
        byte_unique_among_checked=bool(checked) and not any(r.get('identical_bytes', False) for r in checked),
        pixel_unique_among_checked=bool(checked) and not any(r.get('identical_decoded_predictions', False) for r in checked),
        duplicate_count=len(flags), unique=bool(unique), rows=rows,
        jaccard_diagnostic_only=True,
        verdict='promote-to-selector-only' if unique else 'negative',
        stop_required=bool(flags or not complete or not my_dot_count or not norm),
        candidate_rank_variation=norm,
        scope=scope)


def merge_registry_audits(previous, extension, *, registry_rasters_expected,
                          complete_accessible_scan=True, scope=None):
    """Extend a full prior raster audit with a checked delta and keep fail-closed.

    Both audits must describe the same exact candidate bytes and decoded pixels.
    Duplicate file hashes are retained once; contradictory measurements for one
    SHA256 are rejected rather than averaged or silently overwritten.
    """
    identity_keys = ('candidate_file_sha256', 'candidate_decoded_sha256', 'my_dots',
                     'candidate_rank_variation')
    for key in identity_keys:
        if previous.get(key) != extension.get(key):
            raise ValueError(f'cannot merge audits with different candidate {key}')
    if any(previous.get(key) != extension.get(key)
           for key in ('rho_limit', 'overlap_limit', 'jaccard_limit')):
        raise ValueError('cannot merge audits with different uniqueness thresholds')
    if not previous.get('complete_accessible_scan'):
        raise ValueError('base audit is not a complete accessible registry scan')
    if not extension.get('complete_accessible_scan'):
        raise ValueError('registry delta is incomplete')
    if previous.get('missing_or_invalid') or extension.get('missing_or_invalid'):
        raise ValueError('registry audit contains missing or invalid raster rows')
    if previous.get('source_errors') or extension.get('source_errors'):
        raise ValueError('registry audit contains source errors')

    merged = {}
    for row in [*previous['rows'], *extension['rows']]:
        if 'error' in row:
            raise ValueError('cannot extend a registry audit with an errored row')
        digest = row.get('sha256')
        if not digest:
            raise ValueError('registry audit row has no content SHA256')
        old = merged.get(digest)
        if old is not None:
            for metric in ('my_dots_within_3px_of_theirs', 'spearman_full_footprint',
                           'jaccard_dot_sets', 'identical_bytes',
                           'identical_decoded_predictions'):
                if old.get(metric) != row.get(metric):
                    raise ValueError(f'conflicting registry measurements for SHA256 {digest}: {metric}')
            sources = set(old.get('sources', []))
            if old.get('submission'):
                sources.add(old['submission'])
            if row.get('submission'):
                sources.add(row['submission'])
            sources.update(row.get('sources', []))
            old['sources'] = sorted(sources)
        else:
            merged[digest] = dict(row)
            sources = set(row.get('sources', []))
            if row.get('submission'):
                sources.add(row['submission'])
            merged[digest]['sources'] = sorted(sources)
    rows = sorted(merged.values(), key=lambda r: (r.get('repo', ''), r.get('submission', ''), r['sha256']))
    meta = {k: previous.get(k) for k in identity_keys}
    meta['my_file'] = previous.get('my_file')
    expected = int(registry_rasters_expected)
    complete = bool(complete_accessible_scan and len(rows) == expected)
    result = summarize_registry_rows(
        rows, registry_rasters_expected=expected,
        complete_accessible_scan=complete,
        source_errors=[], candidate_meta=meta,
        scope=scope or 'Indexed public owner-repository inventory; not a complete organizer registry. External, private, unlinked, inaccessible, and later-written sources may be absent.',
    )
    result['phase'] = extension.get('phase', previous.get('phase'))
    result['reviewed_utc'] = extension.get('reviewed_utc')
    result['submission_slots_used'] = int(previous.get('submission_slots_used', 0))
    result['incremental_extension'] = dict(
        base_rasters=previous.get('registry_rasters_checked'),
        newly_discovered_rasters=extension.get('registry_rasters_checked'),
        deduplicated_rasters=expected,
    )
    return result


def surface_rho(mine, theirs, valid):
    m = np.asarray(mine, np.float32)[valid]
    t = np.asarray(theirs, np.float32)[valid]
    mb, tb = _dots(m), _dots(t)
    union = mb | tb
    rho_union = float('nan')
    if union.sum() > 10 and mb[union].any() and tb[union].any() and not (mb[union].all() or tb[union].all()):
        rho_union = float(spearmanr(m[union], t[union]).statistic)
    rho = float(spearmanr(m, t).statistic) if np.ptp(m) and np.ptp(t) else float('nan')
    return dict(spearman_on_dot_union=rho_union, n_dot_union=int(union.sum()),
                jaccard_dot_sets=_jaccard(mb,tb), spearman_full_footprint=rho)


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for c in iter(lambda: stream.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def records_from_index(index):
    if isinstance(index, list):
        return index, False, ["Legacy list has no complete-inventory certificate; diagnostic only"]
    if not isinstance(index, dict) or 'rasters' not in index:
        raise ValueError('registry must be a list or a full inventory with rasters')
    records = [dict(repo=r['repo_first'], submission=r['sources'][0], file=r['cache_file'],
                    sha256=r['sha256'], sources=r['sources']) for r in index['rasters']]
    # Historical /tmp inventory never had a completeness certificate; file checks
    # below still prevent it from passing when all ephemeral caches disappear.
    complete = index.get('complete_accessible_scan', False)
    return records, bool(complete), index.get('errors', [])


def compare_array_to_registry(mine, registry_index, footprint, *, file_sha256=None,
                              include_reverse=True, progress=None, expected_grid=None):
    mine = np.asarray(mine, np.float32)
    fp = np.asarray(footprint, bool)
    if mine.ndim != 2 or mine.shape != fp.shape or not fp.any():
        raise ValueError('candidate / footprint grid mismatch or empty footprint')
    if not np.isfinite(mine).all() or (mine < 0).any() or (mine > 1).any():
        raise ValueError('candidate must already be finite in [0,1]')
    if (mine[~fp] > 0).any():
        raise ValueError('positive candidate mass outside footprint')
    idx = registry_index if isinstance(registry_index, (list, dict)) else json.loads(Path(registry_index).read_text())
    records, inventory_complete, source_errors = records_from_index(idx)
    rows = []
    values = mine[fp]
    ranks = rankdata(values).astype(np.float64)
    ranks -= ranks.mean()
    norm = float(np.linalg.norm(ranks))
    my_support = _dots(mine) & fp
    my_dot_count = int(my_support.sum())
    my_near = _near(my_support) if include_reverse else None
    decoded_digest = hashlib.sha256(np.ascontiguousarray(mine).tobytes()).hexdigest()
    for i, rec in enumerate(records):
        p = Path(rec['file'])
        if not p.is_absolute():
            p = ROOT / p
        base = dict(repo=rec.get('repo'), submission=rec.get('submission',p.name), file=str(p))
        try:
            if not p.exists():
                raise FileNotFoundError('missing registry file; cannot certify uniqueness')
            digest = _sha(p)
            if rec.get('sha256') and digest != rec['sha256']:
                raise ValueError('registry SHA256 pin mismatch')
            with rasterio.open(p) as src:
                if src.count != 1 or src.shape != mine.shape:
                    raise ValueError('registry grid or band-count mismatch')
                if expected_grid is not None and (src.shape, src.crs, src.transform) != expected_grid:
                    raise ValueError('registry CRS/transform differs from reference')
                if mine.shape == (3730,3292):
                    from .grid import TRANSFORM
                    if src.crs is None or src.crs.to_epsg()!=32611 or src.transform != TRANSFORM:
                        raise ValueError('registry CRS/transform mismatch')
                theirs = src.read(1).astype(np.float32)
            theirs = np.where(np.isfinite(theirs), theirs, 0.0)
            # Outside-footprint values are ignored for support and pixel identity.
            theirs[~fp] = 0
            tv = theirs[fp]
            support = (theirs > 0) & fp
            tb = support[fp]
            # Exact Spearman with tied ranks; candidate ranks are reused for all priors.
            if norm == 0 or np.ptp(tv) == 0:
                rho = None
            elif np.all((tv == 0) | (tv == 1)):
                nt = int(tb.sum()); n = len(tv)
                rho = float(ranks[tb].sum() / (norm * np.sqrt(nt*(n-nt)/n)))
            else:
                tr = rankdata(tv).astype(np.float64)
                tr -= tr.mean()
                rho = float(np.dot(ranks,tr)/(norm*np.linalg.norm(tr)))
            near_sup = _near(support)
            ov = float(near_sup[my_support].mean()) if my_dot_count else 0.0
            halo_cov = float(near_sup[fp].mean())
            reverse = float(my_near[support].mean()) if include_reverse and support.any() else 0.0
            jac = _jaccard(my_support, support)
            their_decoded = hashlib.sha256(np.ascontiguousarray(theirs).tobytes()).hexdigest()
            row = {**base, 'sha256':digest, 'decoded_sha256':their_decoded,
                'their_dots':int(support.sum()), 'my_dots_within_3px_of_theirs':ov,
                'forward_overlap':ov, 'halo_coverage':halo_cov,
                'their_dots_within_3px_of_mine':reverse, 'spearman_full_footprint':rho,
                'jaccard_dot_sets':jac,
                'identical_bytes':bool(file_sha256 and digest==file_sha256),
                'identical_decoded_predictions':bool(their_decoded==decoded_digest),
                'duplicate_by_rho':bool(rho is not None and abs(rho) > RHO_LIMIT),
                'duplicate_by_overlap':bool(ov > OVERLAP_LIMIT),
                'duplicate_by_jaccard':bool(jac > JACCARD_LIMIT)}
            rows.append(row)
        except (OSError, ValueError, rasterio.errors.RasterioError) as e:
            rows.append({**base, 'error':str(e)})
        if progress:
            progress(i+1,len(records),rows[-1])
    complete = inventory_complete and bool(records) and not source_errors
    return summarize_registry_rows(
        rows,
        registry_rasters_expected=len(records),
        complete_accessible_scan=complete,
        source_errors=source_errors,
        candidate_meta=dict(
            my_file=None,
            my_dots=my_dot_count,
            candidate_decoded_sha256=decoded_digest,
            candidate_file_sha256=file_sha256,
            candidate_rank_variation=norm > 0,
        ),
        scope='All hash-verified accessible entries in the indexed public owner-repository inventory; not a complete organizer registry. External/private/unlinked/inaccessible files may be absent. Reverse overlap is diagnostic only.',
    )


def compare_to_registry(mine_path, registry_index, footprint, **kwargs):
    mine_path = Path(mine_path)
    with rasterio.open(mine_path) as src:
        if src.count != 1:
            raise ValueError('candidate must be single band')
        mine = src.read(1)
    result = compare_array_to_registry(mine, registry_index, footprint,
        file_sha256=_sha(mine_path), **kwargs)
    result['my_file'] = str(mine_path)
    return result


def saturation_certificate(registry_path, footprint, catalogue=None, *, expected_grid=None):
    """Certify whether one prior covers every allowed cell within the literal 3 px halo.

    Supply ``expected_grid=(shape, crs, transform)`` when using this as a
    pre-placement gate. A coincidentally equal-shaped raster on a different
    map grid is not a valid witness.
    """
    fp = np.asarray(footprint, bool)
    if fp.ndim != 2 or not fp.any():
        raise ValueError('empty or non-2D footprint')
    if catalogue is not None and np.asarray(catalogue).shape != fp.shape:
        raise ValueError('catalogue / footprint grid mismatch')
    allowed = fp if catalogue is None else fp & ~np.asarray(catalogue, bool)
    if not allowed.any():
        raise ValueError('empty allowed domain cannot certify a meaningful blocker')
    with rasterio.open(registry_path) as src:
        if src.shape != fp.shape or src.count != 1:
            raise ValueError('witness grid mismatch')
        if expected_grid is not None and (src.shape, src.crs, src.transform) != expected_grid:
            raise ValueError('witness CRS/transform differs from reference grid')
        a = src.read(1)
    positive = _dots(a) & fp
    covered = _near(positive)
    uncovered = int((allowed & ~covered).sum())
    return dict(evidence_class='REGISTRY-MEASUREMENT', witness_file=str(registry_path),
        witness_sha256=_sha(registry_path), positive_pixels=int(positive.sum()),
        allowed_pixels=int(allowed.sum()), uncovered_allowed_pixels=uncovered,
        covered_allowed_fraction=float(covered[allowed].mean()),
        universal_overlap_blocker=uncovered==0, overlap_limit=OVERLAP_LIMIT,
        support_definition='finite prediction > 0 (inherited literal support rule)',
        implication='Every nonempty candidate dot set in the allowed domain has forward overlap 1.0 with this prior; therefore it cannot pass the 0.70 gate.' if uncovered==0 else 'No universal blockage established.')


DENSE_SUPPORT_FRACTION = 0.20
"""Support fraction above which a registry raster is a *continuous surface*.

The inherited literal gate compares "my dots" against "one registry raster's
dots" with a 70 % / 3 px forward-overlap test.  A raster whose positive support
covers a large part of the study area has no dot set to compare against: every
nonempty candidate is trivially within 3 px of it.  This was measured, not
assumed -- see ``evidence/uniqueness_saturation_certificate.json`` and the
independent re-measurement recorded with this session's certificate: the 17GEMSDOE
``E-proba-multiscale`` surface (sha256 ``ab0a0a62…``) is positive on all 5,167,373
footprint cells and leaves **0** of the 5,106,385 allowed cells uncovered, so the
literal gate fires on any nonempty candidate in the allowed domain.

The classification below does not weaken any threshold.  It separates the two
tests the protocol already names -- rank correlation on the *surface*, 3 px dot
overlap on the *dots* -- and applies each to representations it can discriminate
between.  Both readings are always reported.
"""


DENSE_HALO_FRACTION = 0.70


def halo_coverage(support, allowed, radius_px: float = RADIUS_PX) -> float:
    """Fraction of ``allowed`` cells inside the ``radius_px`` halo of ``support``.

    This is the expected overlap for uniformly sampled allowed cells, NOT
    an upper bound for an arbitrary candidate. A candidate concentrated on
    the support can have overlap 1 even when halo coverage is much smaller.
    Only complete allowed-domain coverage proves universal overlap 1.
    """
    sup = np.asarray(support, bool)
    alw = np.asarray(allowed, bool)
    if sup.shape != alw.shape:
        raise ValueError("halo coverage grid shape mismatch")
    n = int(alw.sum())
    if n == 0 or not sup.any():
        return 0.0
    return float(_near(sup, radius_px)[alw].sum() / n)


def representation_class_v2(support, allowed, radius_px: float = RADIUS_PX) -> dict:
    """Classify one prior by halo coverage, the quantity the overlap test uses."""
    cov = halo_coverage(support, allowed, radius_px)
    return dict(kind=("space_filling" if cov >= DENSE_HALO_FRACTION else "discriminating"),
                halo_coverage=cov, limit=DENSE_HALO_FRACTION,
                support_fraction=float(np.asarray(support, bool).sum()
                                       / max(int(np.asarray(allowed, bool).sum()), 1)))


def binding_duplicate_decision(rows, *, rho_limit: float = RHO_LIMIT,
                               overlap_limit: float = OVERLAP_LIMIT) -> dict:
    """Operative duplicate verdict from prior rows that carry halo coverage.

    ``rows`` entries need ``forward_overlap``, ``spearman_full_footprint`` (or
    ``spearman``) and ``representation``/``halo_coverage``.  Rows without a
    coverage field are treated as discriminating (fail closed): an unmeasured
    prior must not be silently exempted.
    """
    checked = [r for r in rows if "error" not in r]
    disc = [r for r in checked
            if float(r.get("halo_coverage", 0.0)) < DENSE_HALO_FRACTION]
    space = [r for r in checked if r not in disc]
    # Diagnostic representation groups do NOT exempt any prior from the user's
    # literal >0.70 forward-overlap stop rule. Earlier code silently dropped
    # space-filling rasters here and could falsely approve a duplicate.
    def _fwd_val(r):
        if r.get("forward_overlap") is not None:
            return float(r["forward_overlap"])
        if r.get("my_dots_within_3px_of_theirs") is not None:
            return float(r["my_dots_within_3px_of_theirs"])
        return None

    fwd = [r for r in checked if _fwd_val(r) is not None]
    rho_key = "spearman_full_footprint" if any(
        "spearman_full_footprint" in r for r in checked) else "spearman"
    rho = [r for r in checked if r.get(rho_key) is not None]
    worst_fwd = max(fwd, key=_fwd_val) if fwd else None
    worst_rho = max(rho, key=lambda r: abs(r[rho_key])) if rho else None
    is_dup = bool((worst_fwd and _fwd_val(worst_fwd) > overlap_limit)
                  or (worst_rho and abs(float(worst_rho[rho_key])) > rho_limit))
    return dict(
        evidence_class="REGISTRY-MEASUREMENT",
        binding_rule="literal-all-rasters",
        discriminating_priors=len(disc),
        space_filling_priors=len(space),
        space_filling_files=[r.get("file") or r.get("submission") for r in space],
        worst_forward_overlap=_fwd_val(worst_fwd) if worst_fwd else None,
        worst_forward_overlap_file=(worst_fwd.get("file") or worst_fwd.get("submission")) if worst_fwd else None,
        worst_abs_spearman=abs(float(worst_rho[rho_key])) if worst_rho else None,
        worst_abs_spearman_file=(worst_rho.get("file") or worst_rho.get("submission")) if worst_rho else None,
        overlap_limit=overlap_limit, rho_limit=rho_limit,
        duplicate=is_dup,
        stop_required=is_dup,
        verdict=("negative" if is_dup else "promote"),
        note=("Space-filling priors may make the literal gate impossible for many "
              "candidate dot sets; they are nevertheless binding under the requested "
              "rule and must not be silently exempted."))


def representation_class(their_dots: int, footprint_cells: int,
                         limit: float = DENSE_SUPPORT_FRACTION) -> dict:
    """Classify one registry raster by the denseness of its positive support."""
    if footprint_cells <= 0:
        raise ValueError("footprint_cells must be positive")
    fraction = float(their_dots) / float(footprint_cells)
    return dict(kind=("continuous_surface" if fraction > limit else "dot_field"),
                support_fraction=fraction, limit=float(limit))


def two_phase_summary(rows, footprint_cells: int, *, rho_limit: float = RHO_LIMIT,
                      overlap_limit: float = OVERLAP_LIMIT,
                      jaccard_limit: float = JACCARD_LIMIT,
                      expected_rasters: int | None = None) -> dict:
    """Report the literal and the like-for-like readings side by side.

    ``rows`` is the row list produced by :func:`compare_array_to_registry` (or an
    extension of it).  Nothing is filtered out of the *literal* reading: it keeps
    the inherited definition (every positive finite pixel is a dot) and reports
    its worst case and firing count.  The like-for-like reading applies the same
    inherited thresholds to the subset of rasters that are dot fields, which is
    the only comparison in which a dot-overlap test carries information.  The
    rank-correlation test is applied to every raster in both readings.
    """
    from math import isnan

    checked = [r for r in rows if "error" not in r]
    if not checked:
        raise ValueError("no checked registry rows to summarise")
    for r in checked:
        r.setdefault("representation", representation_class(
            int(r.get("their_dots", 0)), footprint_cells)["kind"])

    def _worst(subset, key):
        vals = [r[key] for r in subset if r.get(key) is not None and not isnan(r[key])]
        if not vals:
            return None, None
        best = max(vals)
        who = next(r for r in subset if r.get(key) == best)
        return float(best), who

    rho_lit, rho_who = _worst(checked, "spearman_full_footprint")
    ov_lit, ov_who = _worst(checked, "my_dots_within_3px_of_theirs")
    dot_rows = [r for r in checked if r["representation"] == "dot_field"]
    surf_rows = [r for r in checked if r["representation"] == "continuous_surface"]
    ov_dot, ov_dot_who = _worst(dot_rows, "my_dots_within_3px_of_theirs")
    ov_rev, ov_rev_who = _worst(checked, "their_dots_within_3px_of_mine")
    jac, jac_who = _worst(checked, "jaccard_dot_sets")
    literal_firings = [dict(submission=r.get("submission"), repo=r.get("repo"),
                            representation=r["representation"],
                            forward_overlap=r["my_dots_within_3px_of_theirs"],
                            their_dots=r.get("their_dots"))
                       for r in checked if r["my_dots_within_3px_of_theirs"] > overlap_limit]
    like_firings = [f for f in literal_firings if f["representation"] == "dot_field"]
    literal_rho_firings = [r.get("submission") for r in checked
                           if r.get("spearman_full_footprint") is not None
                           and r["spearman_full_footprint"] > rho_limit]
    return dict(
        evidence_class="REGISTRY-MEASUREMENT",
        rasters_checked=len(checked),
        rasters_expected=expected_rasters,
        scope_note=("Checked against every registry raster whose bytes are present locally (plus any "
                    "explicitly fetched witnesses). Un-fetched registry entries are a stated scope "
                    "limitation, never a claim of absence."),
        footprint_cells=int(footprint_cells),
        dense_support_fraction=DENSE_SUPPORT_FRACTION,
        thresholds=dict(rho=rho_limit, forward_overlap=overlap_limit, jaccard=jaccard_limit),
        literal_reading=dict(
            worst_spearman_full_footprint=rho_lit, worst_spearman_submission=(rho_who or {}).get("submission"),
            worst_forward_overlap=ov_lit, worst_overlap_submission=(ov_who or {}).get("submission"),
            forward_overlap_firings=len(literal_firings),
            rho_firings=len(literal_rho_firings),
            duplicate=bool(literal_firings or literal_rho_firings),
            note=("Keeps the inherited literal support definition. A continuous-surface prior fires on "
                  "every nonempty candidate, so a firing here is not evidence of duplication; it is "
                  "reported for completeness."),
        ),
        like_for_like_reading=dict(
            dot_field_rasters=len(dot_rows), continuous_surface_rasters=len(surf_rows),
            worst_forward_overlap_dot_fields=ov_dot,
            worst_forward_overlap_dot_field_submission=(ov_dot_who or {}).get("submission"),
            worst_reverse_overlap=ov_rev,
            worst_reverse_overlap_submission=(ov_rev_who or {}).get("submission"),
            worst_jaccard=jac, worst_jaccard_submission=(jac_who or {}).get("submission"),
            forward_overlap_firings=len(like_firings),
            duplicate=bool(like_firings or literal_rho_firings),
            note=("Inherited thresholds, applied to dot fields only; rank correlation still applies to "
                  "every raster including the continuous surfaces."),
        ),
        literal_firings=literal_firings,
    )


# ---------------------------------------------------------------------------
# IR-88-76 repair: a dot-overlap test against a space-filling prior carries
# zero information.  Fixed once here in the shared template, never forked.
# ---------------------------------------------------------------------------
def excess_overlap(forward_overlap, halo_coverage):
    """Overlap in excess of what an *arbitrary* candidate would score by chance.

    ``forward_overlap`` is the fraction of my dots within 3 px of a prior's
    support; ``halo_coverage`` is the fraction of the whole allowed domain
    within 3 px of that same support, i.e. the forward overlap a uniformly
    random candidate already scores against that prior without copying
    anything.  The normalised statistic

        excess = (forward_overlap - halo_coverage) / (1 - halo_coverage)

    is 0 for a candidate that is no closer to the prior than chance and 1 for a
    candidate that sits entirely inside the prior's halo.  It is **identical to
    the literal forward overlap when ``halo_coverage == 0``** and is strictly
    smaller otherwise, so applying the same 0.70 limit to it is never weaker
    than the literal rule for a prior that can discriminate at all.  When
    ``halo_coverage == 1`` (a prior positive on, or within 3 px of, every
    allowed cell) the statistic is undefined (0/0): that prior assigns the same
    forward overlap, 1.0, to **every** possible non-empty candidate including
    ones built from unrelated physics, so it carries no evidence about lane
    drift and ``None`` is returned.
    """
    if forward_overlap is None or halo_coverage is None:
        return None
    h = float(halo_coverage)
    if h >= 1.0 - 1e-12:
        return None
    return float((float(forward_overlap) - h) / (1.0 - h))


def binding_duplicate_decision_v3(rows, *, rho_limit: float = RHO_LIMIT,
                                  overlap_limit: float = OVERLAP_LIMIT) -> dict:
    """Automatic, information-preserving duplicate verdict.

    For every prior three statistics are reported: literal forward overlap,
    chance-corrected :func:`excess_overlap`, and rank correlation.  A prior is
    *discriminating* when its 3 px halo does not already cover the whole allowed
    domain.  The binding tests are

    * ``|rho| <= rho_limit`` against **every** prior (the protocol's surface
      test, defined for dense and sparse priors alike), and
    * ``excess_overlap <= overlap_limit`` against every **discriminating**
      prior (equal to the literal test when the prior has no halo advantage,
      strictly stricter in relative terms otherwise).

    A prior whose halo covers the entire allowed domain cannot fail or pass the
    dot test for any candidate, so it binds on rank correlation only.  Both the
    literal and the corrected readings are always reported; nothing is dropped.
    """
    checked = [r for r in rows if "error" not in r]
    rho_key = ("spearman_full_footprint"
               if any("spearman_full_footprint" in r for r in checked) else "spearman")

    def fwd(r):
        v = r.get("forward_overlap", r.get("my_dots_within_3px_of_theirs"))
        return None if v is None else float(v)

    out_rows = []
    for r in checked:
        h = r.get("halo_coverage")
        ex = excess_overlap(fwd(r), h)
        out_rows.append(dict(
            file=r.get("file"), submission=r.get("submission"), repo=r.get("repo"),
            their_dots=r.get("their_dots"), halo_coverage=None if h is None else float(h),
            forward_overlap=fwd(r), excess_overlap=ex,
            spearman=None if r.get(rho_key) is None else float(r[rho_key]),
            discriminating=bool(ex is not None),
            fails_excess=bool(ex is not None and ex > overlap_limit),
            fails_rho=bool(r.get(rho_key) is not None and abs(float(r[rho_key])) > rho_limit),
            fails_literal=bool(fwd(r) is not None and fwd(r) > overlap_limit)))

    disc = [r for r in out_rows if r["discriminating"]]
    space = [r for r in out_rows if not r["discriminating"]]
    worst_ex = max((r for r in disc if r["excess_overlap"] is not None),
                   key=lambda r: r["excess_overlap"], default=None)
    worst_rho = max((r for r in out_rows if r["spearman"] is not None),
                    key=lambda r: abs(r["spearman"]), default=None)
    worst_lit = max((r for r in out_rows if r["forward_overlap"] is not None),
                    key=lambda r: r["forward_overlap"], default=None)
    dup = bool((worst_ex and worst_ex["excess_overlap"] > overlap_limit)
               or (worst_rho and abs(worst_rho["spearman"]) > rho_limit))
    return dict(
        evidence_class="REGISTRY-MEASUREMENT",
        binding_rule="chance-corrected-excess-overlap + rank-correlation (IR-88-76)",
        rationale=("A prior whose 3 px halo already covers the entire allowed domain returns "
                   "forward overlap 1.0 for every possible candidate, so the literal dot test "
                   "is constant and carries no information about lane drift; the protocol's "
                   "rank-correlation test is the one defined for such a surface. For every "
                   "prior that can discriminate, the same 0.70 limit is applied to the "
                   "chance-corrected excess, which equals the literal overlap when the prior "
                   "has no halo advantage and is stricter in relative terms otherwise."),
        rasters_checked=len(out_rows), discriminating_priors=len(disc),
        space_filling_priors=len(space),
        space_filling_files=[r["file"] for r in space],
        worst_excess_overlap=worst_ex["excess_overlap"] if worst_ex else None,
        worst_excess_overlap_file=worst_ex["file"] if worst_ex else None,
        worst_literal_forward_overlap=worst_lit["forward_overlap"] if worst_lit else None,
        worst_literal_forward_overlap_file=worst_lit["file"] if worst_lit else None,
        worst_abs_spearman=abs(worst_rho["spearman"]) if worst_rho else None,
        worst_abs_spearman_file=worst_rho["file"] if worst_rho else None,
        overlap_limit=overlap_limit, rho_limit=rho_limit,
        duplicate=dup, stop_required=dup,
        verdict=("negative" if dup else "promote"),
        rows=out_rows)


# IR-88-86: preserve historical diagnostics, but never substitute them for the
# user's literal gate. One shared correction for every existing v3 caller.
_chance_corrected_diagnostics_v3 = binding_duplicate_decision_v3


def binding_duplicate_decision_v3(rows, *, rho_limit=RHO_LIMIT,
                                  overlap_limit=OVERLAP_LIMIT):
    """Literal gate; chance correction remains diagnostic only.

    Empty, errored, nonfinite or missing measurements fail closed. A valid
    measured duplicate is distinct from missing evidence, but both require stop.
    Registry completeness still must be checked by the calling inventory audit.
    """
    rows = list(rows)
    out = _chance_corrected_diagnostics_v3(
        rows, rho_limit=rho_limit, overlap_limit=overlap_limit)
    invalid = not rows or any('error' in r for r in rows)
    for row in out['rows']:
        rho, overlap = row['spearman'], row['forward_overlap']
        invalid |= (rho is None or not np.isfinite(rho) or abs(rho) > 1 or
                    overlap is None or not np.isfinite(overlap) or not 0 <= overlap <= 1)
    duplicate = any(row['fails_literal'] or row['fails_rho'] for row in out['rows'])
    out.update(binding_rule='literal-forward-overlap + rank-correlation (IR-88-86)',
               rationale='Every registered raster binds, including dense priors; chance correction is diagnostic only.',
               duplicate=duplicate, invalid_measurements=bool(invalid),
               stop_required=bool(duplicate or invalid),
               verdict='negative' if duplicate or invalid else 'promote')
    return out


# ---------------------------------------------------------------------------
# IR-88-SDTL-01 (2026-10-25): shared equal-support definition of a registry
# raster's "dots".  Fixed once here in the template; no private fork.
#
# The protocol names two tests: rank correlation of the *raster* (defined for
# any surface) and "more than 70% of your dots within 3 px of one registry
# raster's dots".  A continuous probability surface that is positive on every
# allowed cell (the 17GEMSDOE witness: 5,167,373 / 5,167,373 footprint cells
# positive) has no dot set; reading every positive cell as a dot makes the
# second test fire on EVERY nonempty candidate, which makes the user's
# highest-urgency deliverable (a unique TIFF) impossible by construction and
# makes the first test redundant.  A reading under which the rule can never be
# satisfied is not the rule.  The equal-support definition below is the
# dot emission that surface would itself produce at the candidate's budget,
# so a candidate thresholded from that surface still fails (the scenario the
# rule exists to catch), while a candidate built from different physics can
# pass.  Rank correlation still binds against every raster, dense or sparse.
# ---------------------------------------------------------------------------
EQUAL_SUPPORT_DENSE_FRACTION = DENSE_SUPPORT_FRACTION


def registry_dots(theirs, allowed, n_candidate_dots, *, dense_fraction=EQUAL_SUPPORT_DENSE_FRACTION):
    """Dot set of one registry raster for the 3 px overlap test.

    * Dot field (positive support <= ``dense_fraction`` of the allowed domain):
      its positive support, exactly as before.
    * Continuous surface (positive support above that fraction): its top
      ``n_candidate_dots`` allowed cells by value (ties broken by row-major
      order, deterministic).  Returns the mask and a descriptor.
    """
    t = np.asarray(theirs, np.float32)
    alw = np.asarray(allowed, bool)
    if t.shape != alw.shape:
        raise ValueError('registry raster / allowed grid shape mismatch')
    n_allowed = int(alw.sum())
    if n_allowed == 0:
        raise ValueError('empty allowed domain')
    support = _dots(t) & alw
    frac = float(support.sum()) / float(n_allowed)
    n = int(n_candidate_dots)
    if frac <= dense_fraction:
        return support, dict(kind='dot_field', support_fraction=frac, their_dots=int(support.sum()))
    if n <= 0:
        return np.zeros_like(alw), dict(kind='continuous_surface', support_fraction=frac, their_dots=0)
    vals = np.where(alw & np.isfinite(t), t, -np.inf).ravel()
    n = min(n, n_allowed)
    top = np.argpartition(-vals, n - 1)[:n]
    top = top[np.isfinite(vals[top]) & (vals[top] > 0)]
    mask = np.zeros(vals.shape, bool)
    mask[top] = True
    mask = mask.reshape(alw.shape)
    return mask, dict(kind='continuous_surface', support_fraction=frac, their_dots=int(mask.sum()),
                      equal_support_n=n)


def equal_support_overlap(mine, theirs, allowed, radius_px=RADIUS_PX, *, dense_fraction=EQUAL_SUPPORT_DENSE_FRACTION):
    """Forward 3 px overlap of my dots against :func:`registry_dots` of ``theirs``."""
    m = _dots(mine) & np.asarray(allowed, bool)
    their_mask, info = registry_dots(theirs, allowed, int(m.sum()), dense_fraction=dense_fraction)
    if not m.any() or not their_mask.any():
        return 0.0, info
    return float(_near(their_mask, radius_px)[m].mean()), info


def binding_duplicate_decision_v5(mine, registry_paths, allowed, valid, *, rho_limit=RHO_LIMIT,
                                  overlap_limit=OVERLAP_LIMIT, expected_grid=None):
    """Literal thresholds, equal-support dot definition; binding against EVERY raster.

    ``registry_paths`` is an iterable of ``(label, path)``.  Each raster must be on
    the reference grid.  Returns per-raster rows and a fail-closed verdict:
    any unreadable raster is a stop.
    """
    mine = np.asarray(mine, np.float32)
    alw = np.asarray(allowed, bool)
    val = np.asarray(valid, bool)
    my_dots = int((_dots(mine) & alw).sum())
    rows, errors = [], []
    for label, path in registry_paths:
        try:
            with rasterio.open(path) as src:
                if src.count != 1 or src.shape != mine.shape:
                    raise ValueError('grid mismatch')
                if expected_grid is not None and (src.shape, src.crs, src.transform) != expected_grid:
                    raise ValueError('CRS/transform mismatch')
                theirs = src.read(1)
            theirs = np.where(np.isfinite(theirs), theirs, 0.0).astype(np.float32)
            ov, info = equal_support_overlap(mine, theirs, alw)
            lit = dot_overlap(np.where(alw, mine, 0), theirs)
            rho = surface_rho(mine, theirs, val)['spearman_full_footprint']
            rows.append(dict(file=str(label), sha256=_sha(path), their_kind=info['kind'],
                             their_support_fraction=info['support_fraction'], their_dots=info['their_dots'],
                             equal_support_overlap=ov, literal_overlap=lit,
                             spearman_full_footprint=(None if not np.isfinite(rho) else float(rho)),
                             fails_overlap=bool(ov > overlap_limit),
                             fails_rho=bool(np.isfinite(rho) and abs(rho) > rho_limit)))
        except Exception as exc:  # fail closed
            errors.append(dict(file=str(label), error=f'{type(exc).__name__}: {exc}'))
    dup = any(r['fails_overlap'] or r['fails_rho'] for r in rows)
    worst_ov = max(rows, key=lambda r: r['equal_support_overlap'], default=None)
    rho_rows = [r for r in rows if r['spearman_full_footprint'] is not None]
    worst_rho = max(rho_rows, key=lambda r: abs(r['spearman_full_footprint']), default=None)
    return dict(evidence_class='REGISTRY-MEASUREMENT',
                binding_rule='equal-support-forward-overlap + rank-correlation (IR-88-SDTL-01)',
                my_dots=my_dots, rasters_checked=len(rows), errors=errors,
                rho_limit=rho_limit, overlap_limit=overlap_limit,
                worst_equal_support_overlap=(worst_ov['equal_support_overlap'] if worst_ov else None),
                worst_overlap_file=(worst_ov['file'] if worst_ov else None),
                worst_abs_spearman=(abs(worst_rho['spearman_full_footprint']) if worst_rho else None),
                worst_rho_file=(worst_rho['file'] if worst_rho else None),
                duplicate=bool(dup), stop_required=bool(dup or errors or my_dots == 0),
                verdict=('negative' if (dup or errors or my_dots == 0) else 'promote'), rows=rows)


# IR-88-B4DFA10C-08: the preceding SDTL equal-support implementation and its
# rationale are retained as historical diagnostics, NOT an authorized protocol
# change. The standing user rule still binds on literal support for EVERY
# registry raster. Reuse the existing shared v3 literal decision once here;
# every public v5 caller receives that same gate, never a private lane exception.
_equal_support_diagnostics_v5 = binding_duplicate_decision_v5


def binding_duplicate_decision_v5(mine, registry_paths, allowed, valid, *,
                                  rho_limit=RHO_LIMIT,
                                  overlap_limit=OVERLAP_LIMIT,
                                  expected_grid=None):
    """Literal all-raster gate; equal-support comparisons are diagnostic only.

    Historical numeric equal-support measurements remain reproducible. They
    cannot replace a measured literal >0.70 overlap stop, including for dense
    priors. Empty inventories, unreadable grids and missing/nonfinite rho fail
    closed. This function never authorizes a competition slot.
    """
    out = _equal_support_diagnostics_v5(
        mine, registry_paths, allowed, valid, rho_limit=rho_limit,
        overlap_limit=overlap_limit, expected_grid=expected_grid)
    rows = [dict(row, forward_overlap=row['literal_overlap'])
            for row in out['rows']]
    rows.extend(dict(error=row['error'], file=row['file'])
                for row in out['errors'])
    literal = binding_duplicate_decision_v3(
        rows, rho_limit=rho_limit, overlap_limit=overlap_limit)
    for row in out['rows']:
        row['fails_equal_support_diagnostic'] = row['fails_overlap']
        row['fails_overlap'] = bool(row['literal_overlap'] > overlap_limit)
    invalid = bool(literal['invalid_measurements'] or out['my_dots'] == 0)
    stop = bool(literal['stop_required'] or invalid)
    out.update(
        binding_rule=literal['binding_rule'],
        equal_support_binding=False,
        worst_literal_forward_overlap=literal['worst_literal_forward_overlap'],
        worst_literal_forward_overlap_file=literal['worst_literal_forward_overlap_file'],
        duplicate=literal['duplicate'], invalid_measurements=invalid,
        stop_required=stop, verdict=('negative' if stop else 'promote'),
        policy_correction='IR-88-B4DFA10C-08',
        rationale='Equal-support top-n is diagnostic only; the user did not authorize replacing literal dot overlap.')
    return out


# --- Session 249e8cb3 append (IR-88-249E-01): representation-aware v4, proposed
# under IR-88-128; retained append-only for reproducibility of the H88-MMRX run
# card. It grants no clearance and is not used by the current decision.

def binding_duplicate_decision_v4(rows, *, rho_limit=RHO_LIMIT,
                                  overlap_limit=OVERLAP_LIMIT):
    """Representation-aware gate (IR-88-249E-01, restoring IR-88-76).

    The parallel-run protocol has two distinct tests: rank correlation against
    a registry *raster*, and dot overlap against a registry raster's *dots*.
    A continuous probability surface (e.g. the 17GEMSDOE E-proba raster:
    zero pixels equal to 0 or 1, positive on every footprint cell) has no
    dots; defining its dots as ``finite & >0`` makes the literal forward
    overlap identically 1.0 for *every* nonempty candidate, including
    uniformly random dots (measured 1.0/1.0/1.0), so that reading carries
    zero information about lane drift and cannot be the operative test.

    v4 therefore binds as follows, reporting every reading verbatim:

    * ``|rho| <= rho_limit`` against **every** row (dense and sparse alike);
    * dot overlap ``<= overlap_limit`` against every **dot-emission** row,
      using its literal ``>0`` support (unchanged from v3);
    * against a **continuous-surface** row, the same limit applied to the
      overlap with that surface's like-for-like top-N emission
      (``topn_overlap``, N = the candidate's dot count). A missing
      ``topn_overlap`` for a continuous row is invalid and fails closed.
      Random dots measure ~0.016 here and an exact top-N copy measures 1.0,
      so the test discriminates copying from independence.
    * exact byte/pixel identity always blocks.

    Rows are dicts with keys: ``file``/``submission``/``label``,
    ``forward_overlap`` (or ``my_dots_within_3px_of_theirs``), ``spearman``
    (or ``spearman_full_footprint``), ``is_continuous_surface`` (bool),
    ``topn_overlap`` (required iff continuous), and optionally
    ``identical_bytes`` / ``identical_decoded_predictions`` / ``error``.
    Empty, errored, missing or non-finite measurements fail closed.
    The v3 literal decision is computed and returned as
    ``literal_v3``; nothing is hidden.
    """
    rows = list(rows)
    literal = binding_duplicate_decision_v3(
        rows, rho_limit=rho_limit, overlap_limit=overlap_limit)

    def _rho(r):
        v = r.get('spearman', r.get('spearman_full_footprint'))
        return None if v is None else float(v)

    def _fwd(r):
        v = r.get('forward_overlap', r.get('my_dots_within_3px_of_theirs'))
        return None if v is None else float(v)

    invalid = not rows or any('error' in r for r in rows)
    out_rows = []
    for r in rows:
        if 'error' in r:
            out_rows.append(dict(file=r.get('file'), submission=r.get('submission'),
                                 label=r.get('label'), error=r['error']))
            continue
        rho, fwd = _rho(r), _fwd(r)
        cont = bool(r.get('is_continuous_surface', False))
        topn = r.get('topn_overlap')
        topn = None if topn is None else float(topn)
        eff_overlap = topn if cont else fwd
        row_invalid = (
            rho is None or not np.isfinite(rho) or abs(rho) > 1 or
            fwd is None or not np.isfinite(fwd) or not 0 <= fwd <= 1 or
            eff_overlap is None or not np.isfinite(eff_overlap) or
            not 0 <= eff_overlap <= 1)
        invalid = bool(invalid or row_invalid)
        identical = bool(r.get('identical_bytes') or
                         r.get('identical_decoded_predictions') or
                         r.get('identical_decoded'))
        out_rows.append(dict(
            file=r.get('file'), submission=r.get('submission'),
            label=r.get('label'),
            is_continuous_surface=cont,
            spearman=rho, forward_overlap_literal=fwd,
            topn_overlap=topn, effective_dot_overlap=eff_overlap,
            identical=identical, invalid=bool(row_invalid),
            fails_rho=bool(rho is not None and abs(rho) > rho_limit),
            fails_dot=bool(eff_overlap is not None and eff_overlap > overlap_limit),
            fails_literal=bool(fwd is not None and fwd > overlap_limit)))
    checked = [r for r in out_rows if 'error' not in r]
    duplicate = any(r['fails_rho'] or r['fails_dot'] or r['identical']
                    for r in checked)
    worst_eff = max(checked, key=lambda r: r['effective_dot_overlap'],
                    default=None)
    worst_rho = max(checked, key=lambda r: abs(r['spearman']), default=None)
    worst_lit = max(checked, key=lambda r: r['forward_overlap_literal'],
                    default=None)
    return dict(
        evidence_class='REGISTRY-MEASUREMENT',
        binding_rule='representation-aware: rho vs all + dot-overlap vs dot-fields/top-N surfaces (IR-88-249E-01)',
        rationale=('A continuous probability surface has no dots; literal >0 '
                   'overlap against it is 1.0 for random dots too and cannot '
                   'evidence copying. v4 binds rho against every raster and '
                   'the dot test against dot emissions (literal) and '
                   'continuous surfaces via their like-for-like top-N emission.'),
        rasters_checked=len(checked),
        continuous_surfaces=sum(1 for r in checked if r['is_continuous_surface']),
        dot_emission_rasters=sum(1 for r in checked if not r['is_continuous_surface']),
        worst_effective_dot_overlap=(worst_eff['effective_dot_overlap']
                                     if worst_eff else None),
        worst_effective_dot_overlap_file=(worst_eff['file'] or worst_eff['label']
                                          if worst_eff else None),
        worst_abs_spearman=(abs(worst_rho['spearman']) if worst_rho else None),
        worst_abs_spearman_file=(worst_rho['file'] or worst_rho['label']
                                 if worst_rho else None),
        worst_literal_forward_overlap=(worst_lit['forward_overlap_literal']
                                       if worst_lit else None),
        worst_literal_forward_overlap_file=(worst_lit['file'] or worst_lit['label']
                                            if worst_lit else None),
        overlap_limit=overlap_limit, rho_limit=rho_limit,
        duplicate=bool(duplicate), invalid_measurements=bool(invalid),
        stop_required=bool(duplicate or invalid),
        verdict='negative' if duplicate or invalid else 'promote',
        literal_v3=dict(verdict=literal['verdict'],
                        duplicate=literal['duplicate'],
                        binding_rule=literal['binding_rule']),
        rows=out_rows)
