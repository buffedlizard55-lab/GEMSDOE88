"""Independent format audit; never grants scientific promotion or writes predictions.

Strict all-finite policy deliberately rejects NaN even outside the footprint.
No clipping: a bad prediction must be fixed at its origin, not hidden by this audit.
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
        checks.update(geotiff=src.driver == 'GTiff', single_band=src.count == 1,
                      real_numeric_dtype=np.dtype(src.dtypes[0]).kind in 'uif',
                      template_single_band=ref.count == 1,
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
    return {'schema_version': 1, 'validator': 'gems88-format-audit-v1',
            'artifact': Path(candidate).name, 'sha256': digest,
            'checks': checks, 'minimum': minimum, 'maximum': maximum,
            'format_valid': all(checks.values()), 'submission_ready': False,
            'note': 'Format only. Holdout, leakage, registry and selector approval are separate.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('candidate', type=Path)
    p.add_argument('--template', type=Path, required=True)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    try:
        result = validate(args.candidate, args.template)
    except (OSError, rasterio.errors.RasterioError, ValueError) as exc:
        result = {'format_valid': False, 'submission_ready': False, 'error': str(exc)}
    text = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end='')
    raise SystemExit(0 if result['format_valid'] else 1)
