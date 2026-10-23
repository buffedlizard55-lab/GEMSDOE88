# Independent Verification & Byte-Level Audit (`2026-10-22`)

Every claim in `README.md`, `registry/run_card.json`, `docs/run_card.json`, `docs/data/run-card.json`, `docs/status.json`, and `docs/*.html` has been re-verified directly against on-disk bytes by automated scripts without human intervention:

## 1. Automated Verification Commands Executed & Passed
1. `python scripts/validate_artifact.py docs/downloads/gems88-adhr-dip-hydrothermal-submod-20261022-v2-DO-NOT-SUBMIT.tif --template data/bridge/sample_submission.tif` -> **`format_valid: true` (`11/11` format checks + `11/11` footprint checks PASS)**.
2. `python scripts/validate_release.py` -> **`exit_code = 0`** (`format_ok: true`, `inside_no_nan: true`, `values_0_1: true`, `crs_shape_transform_match: true`, `zip_one_matching_tif: true`, `ok_to_download: true`, `ok_to_submit: false`).
3. `python scripts/validate_release.py --require-submit` -> **`exit_code = 2`** (correctly enforces automatic submission block under un-exempted literal `17GEMSDOE` overlap `1.0 > 0.70`).
4. `python scripts/readiness.py` -> **`exit_code = 0`** (confirms byte-for-byte SHA-256 integrity of `vendor/gems57/*` against `registry/template_pin.json` and synchronizes `docs/status.json`).
5. `python scripts/check_site.py` -> **`exit_code = 0`** (verifies every HTML link/anchor across root `index.html` and all `docs/*.html` pages, safety banners, and explicit `-DO-NOT-SUBMIT` marking on all `.tif`/`.zip` links).
6. `pytest -q` -> **100% PASS** across all unit, validator, site, feed, release, and zero-leakage test suites.

## 2. Pinned Cryptographic Digests (`SHA-256`)
- **Primary Candidate GeoTIFF (`35,034` `{0,1}` dots, `131,557` bytes):** `4e62f632f0b6857b048f9573cd8efe9a5a8003045b6df79f7947789999015cd0`
- **Primary Candidate Single-TIFF ZIP:** `1a34997961fdf7420697a922824f77ae016ba8de339a20b8aff14deca0b76463`
- **Archived `Exp 01` GeoTIFF (`MGC-88`, `37,654` dots):** `3af5d290e7e0f362cd69bc2db416c8e7a2fe25a61189546218169a90e097730b`
- **19-Band `training_features.tif` (`419 MB`):** `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`
- **Reference `sample_submission.tif`:** `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc`
- **Public `existing_faults.tif`:** `7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093`
- **Witness `dense_17gemdoe.tif` (`17GEMSDOE`):** `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`
- **Reference `h33_education.tif` (`GEMSDOE32`):** `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`
