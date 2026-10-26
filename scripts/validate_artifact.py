"""Independent format audit; never grants scientific promotion or writes predictions.

Strict all-finite policy deliberately rejects NaN even outside the footprint.
Only one full-resolution raster is allowed, with self-contained georeferencing:
external sidecars must not make a TIFF pass locally but fail in its one-TIFF ZIP.
Internal overviews are allowed. No clipping: a bad prediction must be fixed at
its origin, not hidden by this audit.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio


def validate(candidate, template):
    checks = {}
    with rasterio.open(template) as ref, rasterio.open(candidate) as src:
        # Band count describes only the selected raster, not every TIFF IFD.
        # A second full-resolution page can otherwise hide invalid predictions
        # while rasterio.read(1) and tifffile.imread both return the first page.
        # GDAL reports those pages as subdatasets, unlike internal overviews.
        checks.update(geotiff=src.driver == 'GTiff', single_band=src.count == 1,
                      single_raster_dataset=not src.subdatasets,
                      self_contained_dataset={Path(p).resolve() for p in src.files} == {Path(candidate).resolve()},
                      real_numeric_dtype=np.dtype(src.dtypes[0]).kind in 'uif',
                      # The organizer specifies float32, not merely numeric [0,1].
                      # The shared gems57 validator/writer already enforce this;
                      # the independent container audit must not be weaker.
                      dtype_float32=np.dtype(src.dtypes[0]) == np.dtype('float32'),
                      template_single_band=ref.count == 1,
                      template_single_raster_dataset=not ref.subdatasets,
                      template_self_contained_dataset={Path(p).resolve() for p in ref.files} == {Path(template).resolve()},
                      crs_match=src.crs is not None and src.crs == ref.crs,
                      shape_match=src.shape == ref.shape,
                      transform_match=src.transform == ref.transform,
                      no_nodata_sentinel=src.nodata is None)
        finite, bounded, unmasked = True, True, True
        minimum, maximum = None, None
        for _, window in src.block_windows(1):
            values = src.read(1, window=window)
            if np.iscomplexobj(values):
                finite, bounded = False, False
                continue
            finite &= bool(np.isfinite(values).all())
            bounded &= bool(((values >= 0) & (values <= 1)).all())
            unmasked &= bool((src.read_masks(1, window=window) == 255).all())
            valid = values[np.isfinite(values)]
            if valid.size:
                lo, hi = float(valid.min()), float(valid.max())
                minimum = lo if minimum is None else min(minimum, lo)
                maximum = hi if maximum is None else max(maximum, hi)
        checks.update(all_finite=finite, values_in_0_1=bounded, all_pixels_unmasked=unmasked)
    with Path(candidate).open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    return {'schema_version': 2, 'validator': 'gems88-format-audit-v3',
            'artifact': Path(candidate).name, 'sha256': digest,
            'checks': checks, 'minimum': minimum, 'maximum': maximum,
            'format_valid': all(checks.values()), 'submission_ready': False,
            'note': 'Format only. Holdout, leakage, registry and selector approval are separate.'}



def validate_artifact(path, sample):
    with rasterio.open(sample) as template, rasterio.open(path) as candidate:
        fp = np.isfinite(template.read(1)) & (template.read_masks(1) > 0)
        checks = {'crs_match': candidate.crs is not None and candidate.crs == template.crs,
                  'shape_match': candidate.shape == template.shape,
                  'transform_match': candidate.transform == template.transform,
                  'single_band': candidate.count == 1,
                  'geotiff': candidate.driver == 'GTiff'}
        # Do not use a masked read of predictions: nodata must not conceal invalid values.
        p = candidate.read(1)
        checks['real_numeric_dtype'] = not np.iscomplexobj(p)
        if np.iscomplexobj(p):
            p = np.full(p.shape, np.nan)
        checks['no_nan_inside'] = bool(checks['shape_match'] and np.isfinite(p[fp]).all())
        checks['range_0_1'] = bool(np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all())
        checks['footprint_nonempty'] = bool(fp.any())
        checks['no_mass_outside'] = bool(checks['shape_match'] and not (p[~fp] != 0).any())
        checks['footprint_not_masked'] = bool(checks['shape_match'] and (candidate.read_masks(1)[fp] > 0).all())
    from pathlib import Path
    checks['strict_audit'] = validate(path, sample)['format_valid']
    checks['ok'] = all(checks.values())
    checks['raster_sha256'] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    checks['sample_sha256'] = hashlib.sha256(Path(sample).read_bytes()).hexdigest()
    checks['approval'] = 'FORMAT_ONLY_NOT_SLOT_APPROVAL'
    return checks



if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('candidate', type=Path)
    p.add_argument('--template', type=Path, required=True)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    try:
        result = validate(args.candidate, args.template)
        footprint = validate_artifact(args.candidate, args.template)
        result['footprint_audit'] = footprint
        result['format_valid'] = result['format_valid'] and footprint['ok']
    except (OSError, rasterio.errors.RasterioError, ValueError) as exc:
        result = {'format_valid': False, 'submission_ready': False, 'error': str(exc)}
    text = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end='')
    raise SystemExit(0 if result['format_valid'] else 1)
