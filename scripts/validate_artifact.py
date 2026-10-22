"""Independent on-disk range/grid audit. This is not scientific or slot approval."""
from __future__ import annotations
import argparse
import hashlib
import json
import numpy as np
import rasterio


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
        checks['no_nan_inside'] = bool(checks['shape_match'] and np.isfinite(p[fp]).all())
        checks['range_0_1'] = bool(np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all())
        checks['footprint_nonempty'] = bool(fp.any())
        checks['no_mass_outside'] = bool(checks['shape_match'] and not (p[~fp] != 0).any())
        checks['footprint_not_masked'] = bool(checks['shape_match'] and (candidate.read_masks(1)[fp] > 0).all())
    from pathlib import Path
    checks['ok'] = all(checks.values())
    checks['raster_sha256'] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    checks['sample_sha256'] = hashlib.sha256(Path(sample).read_bytes()).hexdigest()
    checks['approval'] = 'FORMAT_ONLY_NOT_SLOT_APPROVAL'
    return checks


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tif')
    parser.add_argument('sample')
    args = parser.parse_args()
    report = validate_artifact(args.tif, args.sample)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['ok'] else 1)
