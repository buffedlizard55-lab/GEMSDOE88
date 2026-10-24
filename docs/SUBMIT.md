# Human Portal Submission Checklist (`2026-10-24` — Agent Brief v2)

> **Never automated.** No agent reads credentials, fetches `drivendata.org`, or uploads files. One entity has **at most 3 scored submissions per rolling 7-day window** and **only ONE blind final submission** across the competition. Treat any live public change with **`|delta| < 0.01` as no evidence**.

---

## 0. Mandatory Pre-Upload Human Check
1. Confirm on the DrivenData portal:
   - Current **rolling-week slot balance** (`<= 3` per rolling 7 days, one entity total),
   - Current **`TOP_PUBLIC`** score, and
   - Official **submission deadline** (`2026-12-03`).
2. Candidate GeoTIFFs (`releases/*.tif`, `releases/*.zip`) are gitignored so competition/candidate rasters never enter public Git history. On a fresh clone, restore pinned inputs and rebuild deterministically, then verify SHA-256 before uploading:
   ```bash
   python3 scripts/restore_r0_prune_inputs.py
   python3 scripts/build_prune_variants.py            # rebuilds Slot 1 (PRUNEp3px 6f7ae705)
   python3 scripts/build_prune_deconfound_variants.py # rebuilds Slot 2 (PRUNEp3space35fp 8d29a2f7), Slot 3 options, and p3space35/p4space35
   sha256sum releases/*.tif
   ```
3. **NaN vs Zeros rule:** Always upload the primary **`<id>.tif`** (`NaN` outside valid footprint, matching `sample_submission.tif`) — or `<id>.zip` if the portal requests a single-TIFF ZIP. Upload **`<id>-zeros.tif`** (`0.0` outside valid footprint) **only if** the portal validator rejects `NaN` nodata.

---

## 1. Rolling Slot 1 — Gate-Clean `3 px` Baseline (`R1`)
- **Candidate ID:** `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705`
- **Primary file (`NaN` outside):** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705.tif`
  - **SHA-256:** `6f7ae7056262ba3b58c8ab0448f31f82369c25b19b656cb83063cd5821c33185`
- **Fallback file (`0.0` outside, only if `NaN` rejected):** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-zeros.tif`
  - **SHA-256:** `dc6f090d7657b5b49b0363cfbb95163a724349e6b053636bd4524afdf2372c07`
- **Portal short note (`96 / 140` chars):**
  ```text
  h33-2-b2; PRUNE d_cat<=3px (-2171) +2171 physical refill d>3px, N=37654; pred +0.008 MODEL
  ```
- **Role:** Establishes the first verified live `RECEIPT` on a `100%` `> 3.0 px` gate-compliant baseline (`N = 37,654`), anchoring `R0`'s historical `0.2778 CLAIM`.

---

## 2. Rolling Slot 2 — Spaced Farthest-Point Null-Rank Refill (`IR-88-54` Upgrade)
- **Candidate ID:** `h33-h33-2-b2-PRUNEp3space35fp-20261024-8d29a2f7`
- **Primary file (`NaN` outside):** `releases/h33-h33-2-b2-PRUNEp3space35fp-20261024-8d29a2f7.tif`
  - **SHA-256:** `8d29a2f7a9d37b9795a5e14bb9ae9c406ed0f02d1a9100e70a0fec924a52c516`
- **Fallback file (`0.0` outside, only if `NaN` rejected):** `releases/h33-h33-2-b2-PRUNEp3space35fp-20261024-8d29a2f7-zeros.tif`
  - **SHA-256:** `261de02c10559feaecccc1c5e314cf3074909317e581be1a31c410fa1ac70f87`
- **Portal short note (`103 / 140` chars):**
  ```text
  h33-2-b2; PRUNE <=3px (-2171) +2171 >=3.5px farthest-point null-rank refill, N=37654; pred +0.008 MODEL
  ```
- **Role:** Pure single-factor test of `>= 3.5 px` non-overlapping ridge refill (`min_nn = 5.66 px`, `median_nn = 8.00 px`, `91.9% >= 6 px`) against Slot 1 (`R1`, unspaced `min_nn = 1.0 px`) at identical `d_cat <= 3.0 px` collar and `N = 37,654`. Upgrades `PRUNEp3space35` (`49fff49b`) after `IR-88-54` showed score-blind farthest-point ranking beats `w`-ranking on the blind off-catalogue SGMC control (`0.101947` vs `0.101042`) with zero external features.

---

## 3. Rolling Slot 3 — Conditional on Recorded Slot 1 & Slot 2 Receipts
Spend **only after** pasting verbatim Slot 1 and Slot 2 receipts into `ledger/submissions.csv`:

### Option 3A — If `Slot 2 > Slot 1` (widen collar to `4.0 px` under `>= 3.5 px` spacing)
- **Candidate ID:** `h33-h33-2-b2-PRUNEp4space35-20261023-07bd8182`
- **Primary `.tif` SHA-256:** `07bd8182ec4d542aa127601febb2eb37b1458885bce1941593bf846b85f4bb2a`
- **Fallback `-zeros.tif` SHA-256:** `fb7ee110c9ac96a32e53f7d9558bade00d6244f4b5622e35eab83264646e3766`
- **Portal short note (`85 / 140` chars):** `h33-2-b2; PRUNE <=4px (-3825) +3825 >=3.5px-spaced refill, N=37654; pred +0.010 MODEL`

### Option 3B — If `100%` competition-band-only provenance (zero `H19-4/H16-1`, zero external data) is desired
- **Candidate ID:** `h33-h33-2-b2-PRUNEp3space35prov-20261024-0237d5b9`
- **Primary `.tif` SHA-256:** `0237d5b991f4b2bd64ad1a5b9580b25add1b748a18ec3e6ffbe102670d894c3d`
- **Fallback `-zeros.tif` SHA-256:** `5c1e756400f412969cb28031d9b65aa032495f46a3f4750be2bf655c3e504d7b`
- **Portal short note (`110 / 140` chars):** `h33-2-b2; PRUNE <=3px (-2171) +2171 >=3.5px provided-band B19/3/18/15 crest refill, N=37654; pred +0.004 MODEL`

### Option 3C — If `Slot 1 <= R0 - 0.01` live (preserve all `560` zero-kernel `d_cat == 3.0 px` `R0` splay dots)
- **Candidate ID:** `h33-h33-2-b2-PRUNElt3space35-20261024-0b522c7f`
- **Primary `.tif` SHA-256:** `0b522c7fcdbf3343fa21dd5224466902166924b52e2467557ef9b52e8f37da5d`
- **Fallback `-zeros.tif` SHA-256:** `6fdbdcf1b5f4b5229ed623a04880f686fad5f81c354a63c574fd685c99b83aff`
- **Portal short note (`98 / 140` chars):** `h33-2-b2; PRUNE d_cat<3px (-1611, keep 560 d=3px) +1611 >=3.5px refill, N=37654; pred +0.006 MODEL`

*(Backup `w`-ranked pivot `h33-h33-2-b2-PRUNEp3space35-20261023-49fff49b`: `.tif` `49fff49b03c47d7ac3822df185f1efd55b0b30855133360689754ce85167a61a`, `-zeros.tif` `e0b9d59b765a198aa5327bb99bddf09fec52e2806410a403b63ccce2d204824e` — also rebuilt byte-identically on disk and hardened-validated in `registry/prune_spaced_revalidation.json`.)*

---

## 4. Recording a Verbatim Receipt After Any Upload
After the portal returns a score, update `status = SUBMITTED`, `receipt_score = <exact portal number>`, and `receipt_date = <YYYY-MM-DDTHH:MM:SSZ>` on that candidate's row in `ledger/submissions.csv` (and save the verbatim portal text/screenshot locally). Never back-fill estimated numbers.
