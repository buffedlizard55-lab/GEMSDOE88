# Session `d498c1ca` three-pass review (2026-10-26)

## Decision (obvious)

| Gate | Result |
|---|---|
| Download archived research GeoTIFF | **YES** (historical files only; all named `*-DO-NOT-SUBMIT*`) |
| Submit to DrivenData this session | **NO — DO NOT SUBMIT** |
| New unique competition TIFF generated | **NO** (`generation_allowed: false`) |
| Weekly slot | **0** |
| Organizer-confirmed score | **none** |

Canonical research download remains [H88-BPWD](../docs/downloads/gems88-bpwd88-baranov-worm-conduit-37654-20261025-b8543782-zeros-DO-NOT-SUBMIT.tif) (SHA-256 `b8543782dde52b42253d15b9d6db04b09a1351574ff54077581345c904d7d777`) or educational [H88-TDKL](../docs/downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif). **Do not upload any file whose name contains `DO-NOT-SUBMIT`.**

## Why H33 (`0.2778`) is not a target we can copy

- Claim **`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778`** is **USER-REPORTED**, not **ORGANIZER-CONFIRMED** (no submission-page receipt in this checkout).
- Mechanism (prior forensics): **sparser emission of an H19.5 / D2.8 dotted-ridge family**, not a new physics stack. Copying it would fail the lane uniqueness rule (ρ / 3-px overlap vs GEMSDOE24/25/28/32).
- Leaderboard figures in the prompt (`0.4413`, `0.3195`) are **historical unreceipted claims**, not live scores from this sandbox. [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) requires login; not fetched here.

## Why a higher unique TIFF was not written

Parallel-run protocol: if rank-correlation > 0.90 **or** >70% of dots within 3 px of a registry raster → **duplicate, stop**. The pinned dense witness `17GEMSDOE` (`ab0a0a62…`) is finite and >0 on **every** allowed cell (`5,106,385 / 5,106,385`). Literal forward overlap of any nonempty candidate is **1.00 > 0.70**. `scripts/generation_guard.py` therefore exits **2** *before* features. Bypassing that (CON88) was withdrawn. **Maximize P(Win):** do not spend a weekly slot on a file the project protocol already fails.

Local HOLDOUT-DTI record in-repo: **H88-BPWD `0.205991` [0.188105, 0.223344]** (`gems57-pooled-hide-v2`, n=22,893). That is **HOLDOUT-DTI**, not a portal score, and still **not unique** under the literal witness.

## Pass 1–3

1. Inventory: 48 audited `docs/downloads` pairs, all research-only; generation guard present; data gitignored.
2. Bugs: none introduced; no new TIFF; no `ok_to_submit` flip.
3. Request vs outcome: unique **submit-cleared** TIFF **unmet**; unique **research** files already exist; site already makes download vs submit obvious.

## Limitations / next session

- No DrivenData auth → cannot fetch `training_features` from the official data tab (owner-mirror restore exists when GitHub clone works).
- Sandbox egress: github.com / pypi / npm only.
- Need organizer or selector **revision of the dense-witness rule** (equal-support vs literal) before any nonempty TIFF can pass uniqueness.
- Do not copy H33/D2.8.
- Validate with `python scripts/generation_guard.py` (expect 2) and `python scripts/audit_downloads.py --check` — no human inspector.

Official links: [overview](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [about](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/) · [reference](https://github.com/drivendataorg/gems-prize-reference-solution) · [EPSG:32611](https://epsg.io/32611) · [Tversky](https://en.wikipedia.org/wiki/Tversky_index) · [GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [INGENIOUS](https://gbcge.org/current-projects/ingenious/) · [GDR 1391](https://gdr.openei.org/submissions/1391)
