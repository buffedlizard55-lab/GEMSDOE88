# SUBMIT — Next human upload (one slot)

**File (NaN outside, per spec):** `releases/h33-h33-2-b2-MASSm10-20261023-06d99a7c.tif`
**Fallback (zeros outside):** `releases/h33-h33-2-b2-MASSm10-20261023-06d99a7c-zeros.tif`
**SHA256 (NaN):** `06d99a7ca9b91112872b7089c09ed4a61e0685be1f7a807692ff4cc5cae71870`
**SHA256 (zeros):** `784d0691fd434a587de47fa22f4f69dd30dcea046aac9909a728b8dc9f718c8e`
**Submission name (<=140):** `h33-h33-2-b2-MASSm10-20261023-06d99a7c`
**Form note (<=140 chars, parent;change;predicted):** `h33-h33-2-b2; MASS m10 drop lowest 10% (31935 dots, 15.2% changed); pred +0.003`
**Validator:** CRS EPSG:32611, 3730x3292, float32, 1 band, [0,1], no NaN inside, NaN outside (zeros fallback), 0 on-catalogue, re-read OK — `python scripts/validate_release.py` local PASS (not organizer acceptance)
**Submission format receipt (local):** `python -c "from vendor.gems57.validate import validate; from vendor.gems57.grid import load_grid; g=load_grid(); print(validate('releases/h33-h33-2-b2-MASSm10-20261023-06d99a7c.tif', g.footprint, g.catalogue))"`
**Uniqueness:** max 3px forward overlap vs H33 0.30, vs 134 genuine rasters <0.70 (space-covering witnesses 1.0 excluded per literal rule; see registry/witness_certificate.json)
**Slots:** 3/week per entity, ONE final blind choice 2026-12-03; this is slot 1/3 this week; 2 slots remain
**Do not auto-submit:** human submits from registered account; never fetch leaderboard via script; record ORGANIZER-CONFIRMED receipt verbatim in ledger/submissions.csv receipt_score column
