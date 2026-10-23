# Ledger

`submissions.csv` reconciles three concurrent MASS variants and this branch's PRUNE3 variant. All are `BUILT`; no receipt fields are filled and no slots are recorded as used. The MASS rows are HOLD under the current 3 px non-PRUNE rule. `mechanism_cards.json` contains the concurrent MASS cards; the PRUNE3 card is beside its release receipt in `releases/`.

Before any future build, check every exact `(parent,axis,value)` pair and primary/zeros SHA-256. Never treat MODEL or PROXY values as receipt scores.
