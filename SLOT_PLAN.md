# SLOT_PLAN — one entity; <=3 scored uploads per rolling week

**2026-10-23, AXIS=TRACKB (Phase 2 readiness, 0 weekly slots):** All 15 pins passed;
`R0` (`c55bafc4…`/`baeae321…`, 37,654 dots) and gate-clean `R1 = PRUNEp3px-6f7ae705`
(`min d_cat = 3.1623 px`) rebuilt byte-exactly. Extracted **1,259 strike-consistent
`>=1.0 km` fault traces** (`1,753.2 km` total) into `evidence/trackb_traces_geologist.geojson`
(`4a1d0541…`, WGS84 + UTM `EPSG:32611` + 1 geologist paragraph/trace; top-25 dossier in
`evidence/trackb_geologist_dossier.md`) and built 3 controlled `10.00%` (`3,765`-dot)
`TRACKB` rasters on `R1` (`registry/trackb_variant_validation.json` all PASS; ledger now
**38 BUILT / 0 RECEIPT**):
- `...TRACKBtraceext10-20261023-05256d87` (`N=37,654`, `added_min_nn=2.8284 px` in `<=950 m`, `±25°` `>=1 km` tip/relay cones): prereg `MODEL:+0.004`; blind `SGMC=0.09462 PROXY` (**`+0.00763` above `tracespine10`**, preferred Phase 2 raster architecture; IR-88-48).
- `...TRACKBspeckle10minus-20261023-3360100c` (`N=33,889`, `-10%` isolated `<450 m` non-trace speckles): prereg `MODEL:+0.003`; `SGMC=0.08666 PROXY` (shows isolated singletons average `0.0600` credit `> 0.0556` break-even).
- `...TRACKBtracespine10-20261023-a3a183d1` (`N=37,654`, `100 m` spine infill): prereg `MODEL:-0.003`; `SGMC=0.08700 PROXY` (confirms `+3,765` spine dots add only `+0.00034` DTI due to kernel saturation).

**Prior 2026-10-23 findings preserved:** Pure R0 SNAP is impossible under literal 3 px
clearance (`30` of `1,611` `<3 px` dots lack any `<=2 px` legal destination; IR-88-47).
Earlier R0 non-PRUNE arms retaining `<3 px` mass stay **HOLD**. Spacing-locked PRUNE
(`p3space35`/`p4space35`) and four-line field disagree on sign (`evidence/refill_spacing_comparison.json`).

**Before any slot:** human supplies current TOP_PUBLIC/date, actual weekly/total
balance (unknown), R0 receipt (`0.2778` is CLAIM), data-use permission on public
mirrors/historical tracked TIFFs, and confirms provisional **2026-12-03** on the
[competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/)
and [rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf). Primary/zeros twin = **one**
slot; one blind final; `|live delta|<0.01` is no evidence; **never spend a weekly slot
on `TRACKB` unless the human explicitly decides** (Brief v2 §5).

## Next three *conditional* slots

| Order | Existing arm / live projection (MODEL vs R0) | What a RECEIPT changes |
|---|---|---|
| 1 | `PRUNEp3px-6f7ae705` / +0.005 | Gain >=0.01 supports 300 m collar+refill; loss <=-0.01 closes this family. Otherwise inconclusive. Freshly validated locally. |
| 2 | `PRUNEp3space35-49fff49b` / +0.007 | Only if slot 1 does not materially lose, human approves another test, and exact bytes validate. Gain >=0.01 **over p3px** favors spaced refill; loss <=-0.01 disfavors it. |
| 3 | Reserve `PRUNEp4space35-07bd8182` / +0.002 | Only if slot 2 materially wins (`>= +0.01` vs slot 2 favors widening with spaced refill; `<=-0.01` favors 300 m). Else conserve the slot. |

**Weeks:** Oct 23–Nov 5 (wk1–2): receipt/quota/legal checks, conditional PRUNE;
Nov 6–19 (wk3–4): combine axes only with independent >=0.01 receipt evidence on a
gate-clean parent; Nov 20–Dec 3 (wk5–6): validate final + fallback from disk, choose
one blind final paired with `evidence/trackb_traces_geologist.geojson`.

**Better unbuilt axes (proposals only):** **TRACE_ADD_ONLY** (`+4–6%` spaced `>=2.8 px`
`>=1 km` trace-tip adds on `R1` or `p3space35` *without* dropping `0.060`-credit singletons;
falsifier no `>=0.01` live gain over parent at matched collar); **SUPPORT** (new spaced
`H16-1`/`H19-4` strands; falsifier no `>=0.01` gain at matched count); **RANKFIELD**
(refill ranking swap at fixed `>=3.5 px` spacing); **STRIKE_ALIGN** (`<=2 px` snap on
gate-clean `R1`/`p3space35`, avoiding [GeoDAWN flight lines](https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7)).
