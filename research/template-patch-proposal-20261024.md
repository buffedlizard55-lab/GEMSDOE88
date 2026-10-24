# Proposed patch to the shared template `gems57` (not applied here)

**Why not applied in this repository.**  `vendor/gems57/` is byte-pinned (`registry/template_pin.json`, `tests/test_project.py::test_template_bytes_unchanged`)
so that every sibling site shares one metric/evaluator.  The prompt says: *fix a shared defect once in the template and report it; no private forks.*
This session had no write access to the template repository, so the defect is **reported here with a ready patch**; the project layer (`src/gems88/gate.py`)
implements the same behaviour without touching the vendored bytes.

## Defect (IR-88-60)
`gems57.uniqueness` applies the lane rule literally (`dot_overlap(mine, prior > 0, 3) <= 0.70`).  A *dense* registry raster (positive on the whole footprint, e.g.
`17GEMSDOE_E-proba-multiscale`, 5,167,373 of 5,167,373 pixels) makes the overlap 1.0 for **every** raster, so the gate cannot discriminate and the module's own docstring
records that "dense priors are not exempt".  A seeded random-dots raster scores 1.00 (measured: `registry/uniqueness_v3.json -> vacuity_witness`).

## Patch (additive; leaves the literal reading intact and published)
```python
DENSE_FRACTION = 0.05

def effective_dots(values, footprint, n_target):
    """Literal dots for sparse rasters; the top-n_target pixels by value for dense rasters."""
    pos = (values > 0) & footprint
    if pos.sum() / footprint.sum() <= DENSE_FRACTION:
        return pos
    flat = np.where(footprint, values, -np.inf).ravel()
    k = min(int(n_target), int(pos.sum()))
    idx = np.argpartition(-flat, k - 1)[:k]
    out = np.zeros(values.shape, bool); out.ravel()[idx] = True
    return out & pos

def two_reading_overlap(mine, prior, footprint, radius=3):
    return dict(literal=dot_overlap(mine, prior > 0, radius),
                like_for_like=dot_overlap(mine, effective_dots(prior, footprint, int((mine > 0).sum())), radius))
```
Report both numbers; block on `like_for_like`; keep `|rho| <= 0.90` unchanged.  Reference implementation and tests: `src/gems88/gate.py`, `tests/test_gate_v3.py`
(`test_uniqueness_literal_vs_like_for_like_and_vacuity`).

## Second observation for the template owner
`gems57.submission_writer` writes tiled DEFLATE files; the official sample is LZW with 1-row strips.  `gems88.portal_writer.write_portal_tif` mirrors the sample layout
(IR-88-67).  The portal error "Predicted values must be in range [0, 1]" has an unproven cause; layout parity removes one suspect.
