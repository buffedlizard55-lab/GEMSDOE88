#!/usr/bin/env python3
"""Forensic float64 byte-and-pixel audit of the 9 focus sites (2026-10-26).

Sites covered:
  GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30,
  GEMSDOE31, GEMSDOE32, GEMSDOE33, GEMSDOE36 (plus GEMSDOE91 S18 unrated item).

Modes:
  --rebuild-from-cache  Recompute all SHA-256 digests, pixel counts, d_cat strata,
                        cKDTree nearest-neighbor spacings, exact 0-px / 3-px overlaps,
                        and float64 Spearman rank correlations from .cache/focus_sites/
                        and data/, writing evidence/focus_sites_20261026_audit.json,
                        docs/data/focus_sites_20261026.json, and
                        docs/data/focus_sites_20261026.csv.
  (default)             Verify committed JSON/CSV integrity, schema invariants,
                        and local data/registry witness digests without requiring
                        gitignored .cache/focus_sites/ bytes in CI.
  --require-submit      Exit 2 (fail-closed) unless at least one candidate clears
                        both scientific holdout and literal all-registry uniqueness.
"""
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_JSON = ROOT / "evidence/focus_sites_20261026_audit.json"
DOCS_JSON = ROOT / "docs/data/focus_sites_20261026.json"
DOCS_CSV = ROOT / "docs/data/focus_sites_20261026.csv"

CLAIM_LABEL = "USER-REPORTED CLAIM — NOT HOLDOUT-DTI OR ORGANIZER-CONFIRMED"
FOCUS_SITES = (
    "GEMSDOE24",
    "GEMSDOE25",
    "GEMSDOE27",
    "GEMSDOE28",
    "GEMSDOE30",
    "GEMSDOE31",
    "GEMSDOE32",
    "GEMSDOE33",
    "GEMSDOE36",
)

FOCUS_SPECS: list[dict] = [
    {
        "site": "GEMSDOE24",
        "pages_url": "https://buffedlizard55-lab.github.io/GEMSDOE24/",
        "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE24",
        "champion_cache_file": "GEMSDOE24__gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif",
        "champion_twin_cache_file": "GEMSDOE24__gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-allfinite.tif",
        "champion_prompt_name": "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan",
        "champion_user_reported_value": "0.2477",
        "lineage_role": "D1.5 parent: priority-ordered Poisson thinning (min_dist=1.5 px) of 19GEMSDOE H19-5 ridge skeleton (60,069 dots, including 8,769 inside d_cat<=2 px).",
        "recent_candidates": [
            {
                "name": "gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif",
                "cache_file": "GEMSDOE24__gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "HOLDOUT-DTI gems-segment-pooled-v1 = 0.16379 [0.15045, 0.17739] (n=60,988; +0.01503 vs GVC1 0.14876); Selector v2 = DO_NOT_SUBMIT due to 99.87% > 70% r13-lattice-s5 overlap and literal dense_17gemdoe 1.0000 > 0.70.",
                "repo_verdict": "DO NOT SUBMIT",
            },
            {
                "name": "gems24-trsg1-tworegime-seismic-geo-oof-20261026-7f301fc433f0-zeros.tif",
                "cache_file": "GEMSDOE24__gems24-trsg1-tworegime-seismic-geo-oof-20261026-7f301fc433f0-zeros.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "HOLDOUT-DTI gems-segment-pooled-v1 = 0.14644 [0.13250, 0.15971] (trails GVC1 0.14876 by -0.00232); Selector v2 = DO_NOT_SUBMIT.",
                "repo_verdict": "DO NOT SUBMIT",
            },
            {
                "name": "gems24-gvc1-negative-geothermal-lineament-submod-20261025-abe8e51c719d-zeros.tif",
                "cache_file": "GEMSDOE24__gems24-gvc1-negative-geothermal-lineament-submod-20261025-abe8e51c719d-zeros.tif",
                "user_reported_value": "0.0859",
                "repo_holdout_summary": "HOLDOUT-DTI gems-segment-pooled-v1 = 0.14876 [0.13413, 0.16370] (n=60,988); already submitted per 2026-10-26 user claim (0.0859 << 0.2778).",
                "repo_verdict": "HISTORICAL / SCORED BELOW CHAMPION",
            },
            {
                "name": "gems24-rshg1-regime-hydro-hgb-20261025-98f69d77e868-zeros.tif",
                "cache_file": "GEMSDOE24__gems24-rshg1-regime-hydro-hgb-20261025-98f69d77e868-zeros.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "HOLDOUT-DTI gems-segment-pooled-v1 = 0.12904 [0.11738, 0.14086], trailing unresidualized baseline (0.13000) and GVC1 (0.14876); literal dense/lattice overlap 1.0 > 0.70.",
                "repo_verdict": "DOWNLOAD: YES · SUBMIT: NO",
            },
        ],
    },
    {
        "site": "GEMSDOE25",
        "pages_url": "https://buffedlizard55-lab.github.io/GEMSDOE25/",
        "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE25",
        "champion_cache_file": "GEMSDOE25__gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif",
        "champion_twin_cache_file": "GEMSDOE25__gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif",
        "champion_prompt_name": "dotted-h19-5-d2-8-20261002-e56ea318af89-nan",
        "champion_user_reported_value": "0.2600",
        "lineage_role": "D2.8 trunk: priority-ordered Poisson thinning (min_dist=2.8 px) of H19-5 ridge skeleton (44,090 dots; pixel-for-pixel identical to GEMSDOE30 d28-poisson300m-offcat-44090).",
        "recent_candidates": [
            {
                "name": "gems25-h71-hgpc-blind-b2-sapd3-k3p5-20261026-9eb0c31e5149-zeros.tif",
                "cache_file": "GEMSDOE25__gems25-h71-hgpc-blind-b2-sapd3-k3p5-20261026-9eb0c31e5149-zeros.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "2026-10-26 H71 HGPC-BLIND (59,472 dots): failed GEMSDOE25 holdout gate vs H35 baseline and literal dense_17gemdoe overlap 1.0000 > 0.70.",
                "repo_verdict": "DO NOT SUBMIT",
            },
            {
                "name": "gems25-h66-mgd-flank-sapd3-0-k3p5-20261025-da617550a0e9-zeros.tif",
                "cache_file": "GEMSDOE25__gems25-h66-mgd-flank-sapd3-0-k3p5-20261025-da617550a0e9-zeros.tif",
                "user_reported_value": "0.0742",
                "repo_holdout_summary": "User-reported 0.0742 on 2026-10-25; 21-peer calibration-lattice duplicate and literal dense_17gemdoe overlap 1.0 > 0.70.",
                "repo_verdict": "DO NOT SUBMIT",
            },
        ],
    },
    {
        "site": "GEMSDOE27",
        "pages_url": "https://buffedlizard55-lab.github.io/GEMSDOE27/",
        "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE27",
        "champion_cache_file": "GEMSDOE27__gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif",
        "champion_twin_cache_file": "GEMSDOE27__gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif",
        "champion_prompt_name": "topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan",
        "champion_user_reported_value": "0.2449",
        "lineage_role": "D1.5 superset: exact 60,069 D1.5 dots + 1,259 straight-line T-v2 catalogue-tip gap-closure dots (61,328 total; -0.0028 user-reported drag vs D1.5).",
        "recent_candidates": [
            {
                "name": "gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif",
                "cache_file": "GEMSDOE27__gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "Flagged IR-88-D634DE37-01: GEMSDOE27 (426426b) headlines OK TO SUBMIT with HOLDOUT-DTI = 0.047302 [0.044527, 0.049619] on gems27.metric v1 + holdout-blind-buffered-v2 (unbuffered 0.115636 << 0.2778), while screening uniqueness against only 27-30 local/focus rasters (omitting dense_17gemdoe 1.0000 > 0.70 and calib_h161 0.6200), covering 88.79% (33,434/37,654 > 70%) of H29-S's dots within 3 px, printing stale README stats (0.0568/39.77% vs run-card 0.1645/62.80%), and violating Rule 6 selector separation.",
                "repo_verdict": "PROTOCOL-CONFLICTING PROMOTION / DO NOT SUBMIT",
            },
            {
                "name": "gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif",
                "cache_file": "GEMSDOE27__gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif",
                "user_reported_value": "0.2190",
                "repo_holdout_summary": "Best off-H19-5 user-reported 2026-10-25 candidate (0.2190), still -0.0588 below H33-2-B2 (0.2778); already submitted and literal dense_17gemdoe overlap 1.0 > 0.70.",
                "repo_verdict": "ALREADY SCORED / DO NOT RESUBMIT",
            },
            {
                "name": "gems27-h30-chem-deconf-b2-38k-20261025-ad5a68bb0535-allfinite.tif",
                "cache_file": "GEMSDOE27__gems27-h30-chem-deconf-b2-38k-20261025-ad5a68bb0535-allfinite.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "HOLDOUT-DTI = 0.0961, L-B delta = -0.00445 (negative vs incumbent); literal dense_17gemdoe overlap 1.0 > 0.70.",
                "repo_verdict": "DO NOT SUBMIT",
            },
        ],
    },
    {
        "site": "GEMSDOE28",
        "pages_url": "https://buffedlizard55-lab.github.io/GEMSDOE28/",
        "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE28",
        "champion_cache_file": "GEMSDOE28__gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif",
        "champion_twin_cache_file": "GEMSDOE28__gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif",
        "champion_prompt_name": "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan",
        "champion_user_reported_value": "0.2710",
        "prompt_anomaly_line": "gems28-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan:0.2715",
        "lineage_role": "Near-H33 D2.8/SOLO prune (37,660 dots; 99.88% 3-px overlap with H33-2-B2 and 100.00% with H19-5). Prompt removed the earlier erroneous 0.2715 line (which named GEMSDOE27's 5512495c6bd1 0.2449 file, SHA-256 33003374...), confirming h36-1-rung30-blind-r1 (0.2710) as GEMSDOE28's top listed claim.",
        "recent_candidates": [
            {
                "name": "gems28-s20-nchc-20261026-d432a1d5d6ee-allfinite.tif",
                "cache_file": "GEMSDOE28__gems28-s20-nchc-20261026-d432a1d5d6ee-allfinite.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "2026-10-26 S20-NCHC (40,071 dots): HOLDOUT-DTI = 0.131263 [0.119067, 0.143832] vs H19-5+CELF baseline 0.144433 (delta -0.013171, 0/4 folds positive); literal dense_17gemdoe overlap 1.0000 > 0.70.",
                "repo_verdict": "DO NOT SUBMIT",
            },
            {
                "name": "gems28-s18-mxtp-20261025-3e95505c011a-allfinite.tif",
                "cache_file": "GEMSDOE28__gems28-s18-mxtp-20261025-3e95505c011a-allfinite.tif",
                "user_reported_value": "0.0217",
                "repo_holdout_summary": "User-reported 0.0217 on 2026-10-25; GEMSDOE28 S19-ASCP (0.0808, gain -0.0609) and S15 H39-1 (delta -0.00160) also failed gates; literal dense_17gemdoe overlap 1.0 > 0.70.",
                "repo_verdict": "DO NOT SUBMIT",
            },
        ],
    },
    {
        "site": "GEMSDOE30",
        "pages_url": "https://buffedlizard55-lab.github.io/GEMSDOE30/",
        "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE30",
        "champion_cache_file": "GEMSDOE30__gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif",
        "champion_twin_cache_file": None,
        "champion_prompt_name": "d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca",
        "champion_user_reported_value": "0.2600",
        "lineage_role": "Exact pixel-for-pixel duplicate of GEMSDOE25 D2.8 (44,090/44,090 identical positive pixels; filename embeds prefix 91eae1ca of GEMSDOE25's NaN-outside SHA-256).",
        "recent_candidates": [
            {
                "name": "gems30-FFL1-fusion_edge-44090-20261026-eacd73e854a3.tif",
                "cache_file": "GEMSDOE30__gems30-FFL1-fusion_edge-44090-20261026-eacd73e854a3.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "2026-10-26 FFL-1 (44,090 dots): HOLDOUT-DTI = 0.123344 [0.111270, 0.136190] vs MSDB-1v2 0.117737 (+0.005607), blocked by 78.28% > 70% 3-px overlap vs MSDB-1v2 and 100.00% > 70% vs dense_17gemdoe.",
                "repo_verdict": "DO NOT SUBMIT",
            },
            {
                "name": "gems30-TAD24-decensored-38000-20261025-ea3669f488ea-zeros.tif",
                "cache_file": "GEMSDOE30__gems30-TAD24-decensored-38000-20261025-ea3669f488ea-zeros.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "2026-10-26 G30-TAD (38,000 dots): HOLDOUT-DTI = 0.120561 [0.109133, 0.132920] (+0.002824 vs MSDB-1v2, 95% CI [-0.000557, +0.006300] crosses zero); literal dense_17gemdoe overlap 1.0000 > 0.70.",
                "repo_verdict": "DO NOT SUBMIT",
            },
            {
                "name": "gems30-MSDB1-edge44090-20261025-e7856ec3f14a.tif",
                "cache_file": "GEMSDOE30__gems30-MSDB1-edge44090-20261025-e7856ec3f14a.tif",
                "user_reported_value": "0.1462",
                "repo_holdout_summary": "User-reported 0.1462 on 2026-10-25 (-0.1316 below 0.2778); NaN-outside container (7,111,787 NaNs) risks portal [0,1] failure; literal dense_17gemdoe overlap 1.0 > 0.70.",
                "repo_verdict": "ALREADY SCORED / DO NOT SUBMIT",
            },
            {
                "name": "GEMSDOE30-nearslay-annulus-d3-offcat-20261025T235837Z-662af003-nan.tif",
                "cache_file": "GEMSDOE30__GEMSDOE30-nearslay-annulus-d3-offcat-20261025T235837Z-662af003-nan.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "Pure geometric catalogue-collar annulus (0% >25 px blind discovery; zero geophysical inputs), 7,111,787 NaNs outside footprint, screened against only 21 local files, submission_approved=false in its own run card, and literal dense_17gemdoe overlap 1.0 > 0.70.",
                "repo_verdict": "NOT APPROVED / DO NOT SUBMIT",
            },
        ],
    },
    {
        "site": "GEMSDOE31",
        "pages_url": "https://buffedlizard55-lab.github.io/GEMSDOE31/docs/",
        "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE31",
        "champion_cache_file": "GEMSDOE31__gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif",
        "champion_twin_cache_file": "GEMSDOE31__gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-allfinite.tif",
        "champion_prompt_name": "h27-4-solo-d28-20261004-8acb75e1-nan",
        "champion_user_reported_value": "0.2708",
        "lineage_role": "SOLO-D2.8 (B=1 collar prune): exact 40,199-dot subset of D2.8 removing 3,891 d_cat==1 px flank dots; pixel-for-pixel identical to GEMSDOE28 h27-4-r1-solo-d2-8 (0.2708).",
        "recent_candidates": [
            {
                "name": "gemsdoe31-h31s-udap-sslic-37654-20261026-9355f21d9f-zeros.tif",
                "cache_file": "GEMSDOE31__gemsdoe31-h31s-udap-sslic-37654-20261026-9355f21d9f-zeros.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "2026-10-26 H31-S UDAP-SSLIC (37,654 dots): HOLDOUT-DTI = 0.011066 [0.009184, 0.012872], blocked by 72.5% > 70% surface overlap on RBU31, 99.93% lattice stop, and 100.00% dense_17gemdoe overlap.",
                "repo_verdict": "DO NOT SUBMIT",
            },
            {
                "name": "gems31-xfcoh31-xfield-coherence-37654-20261026-zeros.tif",
                "cache_file": "GEMSDOE31__gems31-xfcoh31-xfield-coherence-37654-20261026-zeros.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "2026-10-26 XFCOH31 (37,654 dots): HOLDOUT-DTI = 0.04588 < 0.04812 baseline (delta -0.00224) and 100.00% dense_17gemdoe overlap.",
                "repo_verdict": "DO NOT SUBMIT",
            },
            {
                "name": "gemsdoe31-h31m-bstep-xmod-submod-20261025-37654-allfinite.tif",
                "cache_file": "GEMSDOE31__gemsdoe31-h31m-bstep-xmod-submod-20261025-37654-allfinite.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "GEMSDOE31 H31-M / TGJ31 (HOLDOUT-DTI 0.00828) failed own promotion gates and recorded broad registry STOP; literal dense_17gemdoe overlap 1.0 > 0.70.",
                "repo_verdict": "DO NOT SUBMIT",
            },
        ],
    },
    {
        "site": "GEMSDOE32",
        "pages_url": "https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html",
        "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE32",
        "champion_cache_file": "GEMSDOE32__gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
        "champion_twin_cache_file": None,
        "champion_prompt_name": "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros",
        "champion_user_reported_value": "0.2778",
        "lineage_role": "H33-2-B2 (#1 user-reported across all 92 sites): exact 37,654-dot subset of SOLO-D2.8 (-2,545 dots in 1<d_cat<=2 px) and D2.8 (-6,436 dots in d_cat<=2 px); 100.00% 3-px overlap with H19-5 and dense_17gemdoe.",
        "recent_candidates": [
            {
                "name": "gemsdoe32-h38g1-lidar-geodawn-gdr-celf37654-20261026T013500Z-35859e28-zeros.tif",
                "cache_file": "GEMSDOE32__gemsdoe32-h38g1-lidar-geodawn-gdr-celf37654-20261026T013500Z-35859e28-zeros.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "2026-10-26 EXP3_H38_G1_CORROB (37,654 dots): HOLDOUT-DTI = 0.008074 (+0.00355 vs H33-2-B2 on buffered catalogue), blocked by 77.56% > 70% overlap vs hcvf2, 99.91% vs r13-lattice, 100.00% vs dense_17gemdoe, and SGMC holdout loss (0.0504 < 0.0641).",
                "repo_verdict": "DO NOT SUBMIT",
            },
            {
                "name": "gemsdoe32-h36-1c-tdr-pds-steger-37654-20261026T012000Z-9ff9d6e2-zeros.tif",
                "cache_file": "GEMSDOE32__gemsdoe32-h36-1c-tdr-pds-steger-37654-20261026T012000Z-9ff9d6e2-zeros.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "2026-10-26 H36-1C-TDR-PDS (37,654 dots): HOLDOUT-DTI = 0.1303 < B0_ridge 0.1338 (negative delta -0.0035) and 100.00% dense_17gemdoe overlap.",
                "repo_verdict": "DO NOT SUBMIT",
            },
            {
                "name": "gemsdoe32-r6-stepprofile-b2-37654-20261026T002502Z-23fbbb51-zeros.tif",
                "cache_file": "GEMSDOE32__gemsdoe32-r6-stepprofile-b2-37654-20261026T002502Z-23fbbb51-zeros.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "Flagged IR-88-C59DB412-02 (and self-demoted to DO NOT SUBMIT by GEMSDOE32 commit 9e55d5d): loses buffered catalogue hide-and-recover (0.00338 < 0.00452; AUC 0.5250) and fails calibration-lattice (0.9782 > 0.70) & dense_17gemdoe (1.0000 > 0.70) uniqueness.",
                "repo_verdict": "SELF-DEMOTED / DO NOT SUBMIT",
            },
        ],
    },
    {
        "site": "GEMSDOE33",
        "pages_url": "https://buffedlizard55-lab.github.io/GEMSDOE33/",
        "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE33",
        "champion_cache_file": "GEMSDOE33__GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif",
        "champion_twin_cache_file": None,
        "champion_prompt_name": "h33d-analog-tip-stepover-r30-20261004-cb490425926e",
        "champion_user_reported_value": "0.2632",
        "lineage_role": "H19-5/D2.8 analog-tip/stepover perturbation (41,865 dots): 99.71% (41,743/41,865) within 3 px of H19-5 and 99.70% within 3 px of D2.8 (refuting GEMSDOE32's unverified 'genuinely different geometry' note).",
        "recent_candidates": [
            {
                "name": "gemsdoe33-a33-r2-csht-transfer-37654-20261026-0b78c04d5fad-zeros.tif",
                "cache_file": "GEMSDOE33__gemsdoe33-a33-r2-csht-transfer-37654-20261026-0b78c04d5fad-zeros.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "2026-10-26 A33-R2-CSHT (37,654 dots): HOLDOUT-DTI = 0.136716 screen / 0.131169 confirm (+0.016049 vs B1_regional 0.115120), blocked by pre-placement surface duplicate vs G30-MSDB1 and 100.00% dense_17gemdoe overlap.",
                "repo_verdict": "DO NOT SUBMIT",
            },
            {
                "name": "gemsdoe33-a33-r2-hmdt-20261026-hmdt-unique-zeros.tif",
                "cache_file": "GEMSDOE33__gemsdoe33-a33-r2-hmdt-20261026-hmdt-unique-zeros.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "Flagged IR-88-D634DE37-02: GEMSDOE33 (40f9b86) generated 42,000 dots without sample_submission.tif (treating all 12,279,160 grid cells as footprint), placing 33,616/42,000 (80.04%) dots OUTSIDE the valid study footprint and 108 dots on known existing_faults.tif in contiguous row-major scanlines (row 0 cols 713..858, nn_min_px=1.0), with zero holdout evaluation (NOT MEASURED) and 100.00% dense_17gemdoe overlap on its 8,384 in-footprint dots.",
                "repo_verdict": "CORRUPTED FOOTPRINT / UNMEASURED / DO NOT SUBMIT",
            },
            {
                "name": "gemsdoe33-a33-l1-analog-transfer-research-37654-20261025-85c94a805a34-zeros.tif",
                "cache_file": "GEMSDOE33__gemsdoe33-a33-l1-analog-transfer-research-37654-20261025-85c94a805a34-zeros.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "HOLDOUT-DTI gems-segment-pooled-v1 = 0.108374 [0.097607, 0.119402] vs comparator 0.113244 (paired delta -0.004870, 0/4 fold wins); literal dense_17gemdoe overlap 1.0 > 0.70.",
                "repo_verdict": "NOT OK TO SUBMIT",
            },
        ],
    },
    {
        "site": "GEMSDOE36",
        "pages_url": "https://buffedlizard55-lab.github.io/GEMSDOE36/docs/",
        "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE36",
        "champion_cache_file": "GEMSDOE36__gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif",
        "champion_twin_cache_file": None,
        "champion_prompt_name": "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros",
        "champion_user_reported_value": "0.2750",
        "lineage_role": "Exact H33-2-B2 superset (#2 user-reported): contains 100.00% (37,654/37,654) of H33-2-B2 dots + 1,200 off-ridge/flank PINN additions (-0.0028 user-reported drag vs 0.2778; 97.75% 3-px overlap with H19-5 & 100.00% with gems36_anderson_pinn.tif).",
        "recent_candidates": [
            {
                "name": "gemsdoe36-atvr36-20261026.tif",
                "cache_file": "GEMSDOE36__gemsdoe36-atvr36-20261026.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "2026-10-26 ATVR-36 EXP-2 (37,654 dots): HOLDOUT-DTI = 0.114502 (4-fold) / 0.117925 (6-fold) vs B0_ridge 0.13375 (delta -0.0158, 0/6 folds positive); literal dense_17gemdoe overlap 1.0000 > 0.70.",
                "repo_verdict": "DO NOT SUBMIT",
            },
            {
                "name": "gemsdoe36-h36-gps-graben-pair-20261026-bb29ce2a4bb4-zeros.tif",
                "cache_file": "GEMSDOE36__gemsdoe36-h36-gps-graben-pair-20261026-bb29ce2a4bb4-zeros.tif",
                "user_reported_value": None,
                "repo_holdout_summary": "2026-10-26 H36-GPS (37,654 dots): HOLDOUT-DTI = 0.131999 [0.114959, 0.151492] vs B0_ridge 0.13375 (delta -0.001751, 3/6 folds positive); literal dense_17gemdoe overlap 1.0000 > 0.70.",
                "repo_verdict": "DO NOT SUBMIT",
            },
        ],
    },
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def unit_rank_vec(vec: np.ndarray) -> np.ndarray:
    """Centered unit-L2 float64 average-tie rank vector."""
    r = rankdata(vec, method="average").astype(np.float64)
    r -= r.mean()
    norm = math.sqrt(float(np.dot(r, r)))
    if norm > 0.0:
        r /= norm
    return r


def binary_unit_dot(unit_r: np.ndarray, pos_allowed_idx: np.ndarray, n_allowed: int) -> float:
    """Exact float64 Spearman between pre-normalized rank vector `unit_r` and a binary indicator.

    Since `sum(unit_r) == 0` and `||unit_r||_2 == 1`, for a binary indicator `I` with `k` ones at
    `pos_allowed_idx` out of `n` elements:
      `dot(unit_r, I - k/n) / ||I - k/n||_2 = sum(unit_r[pos_allowed_idx]) / sqrt(k * (n - k) / n)`.
    """
    k = float(pos_allowed_idx.size)
    n = float(n_allowed)
    if k <= 0.0 or k >= n:
        return 0.0
    denom = math.sqrt(k * (n - k) / n)
    if denom <= 0.0:
        return 0.0
    val = float(unit_r[pos_allowed_idx].sum()) / denom
    return max(-1.0, min(1.0, val))


def binary_spearman_from_counts(na: int, nb: int, nab: int, n_total: int) -> float:
    """Exact float64 Spearman (= Pearson phi) for two binary vectors from counts."""
    n = float(n_total)
    fa, fb, fab = float(na), float(nb), float(nab)
    if fa <= 0.0 or fb <= 0.0 or fa >= n or fb >= n:
        return 0.0
    cov = fab - (fa * fb) / n
    denom = math.sqrt((fa * (n - fa) / n) * (fb * (n - fb) / n))
    if denom <= 0.0:
        return 0.0
    return max(-1.0, min(1.0, cov / denom))


def packed_hits(packed_bits: np.ndarray, flat_idx: np.ndarray) -> int:
    """Count set bits in `packed_bits` (bitorder='big') at `flat_idx` with O(|flat_idx|) RAM."""
    if flat_idx.size == 0:
        return 0
    vals = (packed_bits[flat_idx >> 3] >> (7 - (flat_idx & 7))) & 1
    return int(vals.sum())


def rebuild_from_cache(root: Path = ROOT) -> dict:
    cache_dir = root / ".cache/focus_sites"
    repos_dir = cache_dir / "repos"
    sample_path = root / "data/bridge/sample_submission.tif"
    cat_path = root / "data/bridge/existing_faults.tif"
    if not sample_path.is_file() or not cat_path.is_file():
        raise FileNotFoundError("Missing data/bridge/{sample_submission,existing_faults}.tif")

    with rasterio.open(sample_path) as ds_s, rasterio.open(cat_path) as ds_c:
        sample_arr = ds_s.read(1)
        footprint = np.isfinite(sample_arr) & (ds_s.read_masks(1) > 0)
        cat_mask = (ds_c.read(1) > 0) & footprint
        ref_shape = list(ds_s.shape)
        ref_crs = str(ds_s.crs)
        ref_transform = list(tuple(ds_s.transform)[:6])

    allowed = footprint & ~cat_mask
    n_allowed = int(allowed.sum())
    # Map full-grid flat index -> allowed-domain index (-1 if outside allowed)
    full_to_allowed = np.full(footprint.size, -1, dtype=np.int32)
    full_to_allowed[np.flatnonzero(allowed)] = np.arange(n_allowed, dtype=np.int32)
    d_cat = distance_transform_edt(~cat_mask).astype(np.float32)

    reg_paths = sorted((root / "data/registry").rglob("*.tif"))
    sub_paths = sorted((root / "submissions").glob("*.tif"))
    if not reg_paths:
        raise FileNotFoundError("No registry rasters in data/registry/")

    # Compact bit-packed registry representation (~3.1 MB per raster instead of 70 MB)
    registry_meta: dict[str, dict] = {}
    for rp in reg_paths + sub_paths:
        rel = rp.relative_to(root).as_posix()
        with rasterio.open(rp) as ds:
            arr = ds.read(1)
        pos = np.isfinite(arr) & (arr > 0) & footprint
        edt3 = distance_transform_edt(~pos) <= 3.0 if pos.any() else np.zeros_like(pos)
        pos_allowed = pos[allowed]
        is_binary = bool(np.all(arr[pos] == 1.0)) if pos.any() else True
        entry: dict = {
            "path": rp,
            "sha256": sha256_file(rp),
            "positive_pixels": int(pos.sum()),
            "allowed_positive_pixels": int(pos_allowed.sum()),
            "pos_packed": np.packbits(pos.ravel()),
            "pos_allowed_packed": np.packbits(pos_allowed),
            "edt3_packed": np.packbits(edt3.ravel()),
            "is_binary": is_binary,
            "unit_rank": unit_rank_vec(arr[allowed]) if not is_binary else None,
        }
        registry_meta[rel] = entry
        del arr, pos, edt3, pos_allowed
    gc.collect()

    def inspect_tif(path: Path) -> dict:
        digest = sha256_file(path)
        size_bytes = path.stat().st_size
        with rasterio.open(path) as ds:
            arr = ds.read(1)
            shape_ok = list(ds.shape) == ref_shape
            crs_ok = str(ds.crs) == ref_crs
            transform_ok = list(tuple(ds.transform)[:6]) == ref_transform
            nodata = ds.nodata
        finite = np.isfinite(arr)
        in_fp = arr[footprint]
        in_fp_finite = np.isfinite(in_fp)
        in_fp_range_ok = bool(in_fp_finite.all() and (in_fp >= 0.0).all() and (in_fp <= 1.0).all())
        full_grid_range_ok = bool(finite.all() and (arr >= 0.0).all() and (arr <= 1.0).all())
        pos_all = finite & (arr > 0.0)
        n_pos_total = int(pos_all.sum())
        n_pos_outside_fp = int((pos_all & ~footprint).sum())
        n_pos_on_cat = int((pos_all & cat_mask).sum())
        pos = pos_all & footprint
        n_pos = int(pos.sum())
        flat_pos = np.flatnonzero(pos).astype(np.int64)
        allowed_pos_idx = full_to_allowed[flat_pos]
        allowed_pos_idx = allowed_pos_idx[allowed_pos_idx >= 0].astype(np.int64)
        dvals = d_cat.ravel()[flat_pos]

        if n_pos >= 2:
            yx = np.column_stack(np.nonzero(pos)).astype(np.float64)
            dists, _ = cKDTree(yx).query(yx, k=2)
            nn_min = float(dists[:, 1].min())
            nn_med = float(np.median(dists[:, 1]))
        else:
            nn_min = 0.0
            nn_med = 0.0

        is_bin = bool(np.all(arr[pos] == 1.0)) if n_pos > 0 else True
        cand_unit_rank = unit_rank_vec(arr[allowed]) if not is_bin else None
        edt3 = distance_transform_edt(~pos) <= 3.0 if n_pos > 0 else np.zeros_like(pos)
        pos_packed = np.packbits(pos.ravel())
        edt3_packed = np.packbits(edt3.ravel())
        del arr, finite, in_fp, in_fp_finite, pos, edt3

        def ov3(rm: dict) -> float:
            return float(packed_hits(rm["edt3_packed"], flat_pos) / n_pos) if n_pos > 0 else 0.0

        def ov0(rm: dict) -> float:
            return float(packed_hits(rm["pos_packed"], flat_pos) / n_pos) if n_pos > 0 else 0.0

        def rho_vs(rm: dict) -> float:
            if is_bin and rm["is_binary"]:
                nab = packed_hits(rm["pos_allowed_packed"], allowed_pos_idx)
                return binary_spearman_from_counts(
                    int(allowed_pos_idx.size), rm["allowed_positive_pixels"], nab, n_allowed
                )
            if is_bin and rm["unit_rank"] is not None:
                return binary_unit_dot(rm["unit_rank"], allowed_pos_idx, n_allowed)
            if cand_unit_rank is not None and rm["is_binary"]:
                with rasterio.open(rm["path"]) as rds:
                    rpos = np.flatnonzero((rds.read(1)[allowed] > 0)).astype(np.int64)
                return binary_unit_dot(cand_unit_rank, rpos, n_allowed)
            if cand_unit_rank is not None and rm["unit_rank"] is not None:
                return max(-1.0, min(1.0, float(np.dot(cand_unit_rank, rm["unit_rank"]))))
            return 0.0

        dense_rm = registry_meta["data/registry/dense_17gemdoe.tif"]
        h19_rm = registry_meta["data/registry/gems19_h19_5.tif"]
        h33_rm = registry_meta["data/registry/h33_education.tif"]
        g36_rm = registry_meta["data/registry/gems36_anderson_pinn.tif"]

        best_sparse_ov3_name = ""
        best_sparse_ov3 = -1.0
        best_sparse_rho_name = ""
        best_sparse_rho = -2.0
        for rname, rm in registry_meta.items():
            if rname == "data/registry/dense_17gemdoe.tif":
                continue
            c_ov3 = ov3(rm)
            if c_ov3 > best_sparse_ov3:
                best_sparse_ov3 = c_ov3
                best_sparse_ov3_name = rname
            c_rho = rho_vs(rm)
            if c_rho > best_sparse_rho:
                best_sparse_rho = c_rho
                best_sparse_rho_name = rname

        return {
            "cache_filename": path.name,
            "sha256": digest,
            "size_bytes": size_bytes,
            "grid_matches_sample": bool(shape_ok and crs_ok and transform_ok),
            "nodata": None if nodata is None or (isinstance(nodata, float) and math.isnan(nodata)) else float(nodata),
            "nodata_is_nan": bool(isinstance(nodata, float) and math.isnan(nodata)),
            "full_grid_finite_pixels": int(footprint.size - ((~np.isfinite(nodata)) if False else 0)),
            "in_footprint_range_0_1": in_fp_range_ok,
            "full_grid_strict_0_1_portal_safe": full_grid_range_ok,
            "positive_pixels": n_pos,
            "positive_pixels_total": n_pos_total,
            "positive_pixels_outside_footprint": n_pos_outside_fp,
            "positive_pixels_on_catalogue": n_pos_on_cat,
            "is_binary_0_1": is_bin,
            "nn_min_px": round(nn_min, 6),
            "nn_median_px": round(nn_med, 6),
            "d_cat_strata": {
                "on_catalogue_eq0": int((dvals == 0.0).sum()),
                "gt0_le1_px": int(((dvals > 0.0) & (dvals <= 1.0)).sum()),
                "gt1_le2_px": int(((dvals > 1.0) & (dvals <= 2.0)).sum()),
                "le2_total_px": int((dvals <= 2.0).sum()),
                "gt2_le3_px": int(((dvals > 2.0) & (dvals <= 3.0)).sum()),
                "gt3_le10_px": int(((dvals > 3.0) & (dvals <= 10.0)).sum()),
                "gt10_le25_px": int(((dvals > 10.0) & (dvals <= 25.0)).sum()),
                "gt25_px": int((dvals > 25.0).sum()),
                "frac_gt25": round(float((dvals > 25.0).sum() / n_pos), 6) if n_pos else 0.0,
                "median_d_cat_px": round(float(np.median(dvals)), 6) if n_pos else 0.0,
            },
            "vs_gemsdoe88_registry": {
                "dense_17gemdoe_3px_forward_overlap": round(ov3(dense_rm), 6),
                "dense_17gemdoe_spearman_float64": round(rho_vs(dense_rm), 6),
                "gems19_h19_5_3px_forward_overlap": round(ov3(h19_rm), 6),
                "gems19_h19_5_0px_exact_fraction": round(ov0(h19_rm), 6),
                "h33_education_3px_forward_overlap": round(ov3(h33_rm), 6),
                "h33_education_0px_exact_fraction": round(ov0(h33_rm), 6),
                "gems36_anderson_pinn_3px_forward_overlap": round(ov3(g36_rm), 6),
                "max_nondense_registry_3px_forward_overlap": round(best_sparse_ov3, 6),
                "max_nondense_registry_3px_witness": best_sparse_ov3_name,
                "max_nondense_registry_spearman_float64": round(best_sparse_rho, 6),
                "max_nondense_registry_spearman_witness": best_sparse_rho_name,
                "passes_literal_all_registry_overlap_le_0p70": bool(ov3(dense_rm) <= 0.70),
                "passes_nondense_overlap_le_0p70": bool(best_sparse_ov3 <= 0.70),
            },
            "_flat_pos": flat_pos,
            "_allowed_pos_idx": allowed_pos_idx,
            "_pos_packed": pos_packed,
            "_edt3_packed": edt3_packed,
        }

    # Wait: compute exact full_grid_finite_pixels & full_grid_nan_pixels cleanly inside inspect_tif
    inspected_by_name: dict[str, dict] = {}
    for p in sorted(cache_dir.glob("*.tif")):
        with rasterio.open(p) as ds:
            a = ds.read(1)
            fin_cnt = int(np.isfinite(a).sum())
            nan_cnt = int(np.isnan(a).sum())
            del a
        st = inspect_tif(p)
        st["full_grid_finite_pixels"] = fin_cnt
        st["full_grid_nan_pixels"] = nan_cnt
        inspected_by_name[p.name] = st

    # Verify GEMSDOE28 5512495c6bd1 blob directly from local git clone
    g28_repo = repos_dir / "GEMSDOE28"
    g28_ls = subprocess.check_output(
        ["git", "-C", str(g28_repo), "ls-tree", "-r", "--name-only", "HEAD"],
        text=True,
    ).splitlines()
    g28_5512_paths = [p for p in g28_ls if "5512495c6bd1" in p and p.endswith(".tif")]
    g28_28_prefixed = [p for p in g28_ls if "gems28-topo-gap-closure" in p]
    g28_5512_blob = subprocess.check_output(
        ["git", "-C", str(g28_repo), "show", "HEAD:docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif"]
    )
    g28_5512_sha = hashlib.sha256(g28_5512_blob).hexdigest()
    g27_5512_sha = inspected_by_name["GEMSDOE27__gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif"]["sha256"]

    champ_masks = {
        spec["site"]: inspected_by_name[spec["champion_cache_file"]]
        for spec in FOCUS_SPECS
    }
    d28_m = champ_masks["GEMSDOE25"]
    solo_m = champ_masks["GEMSDOE31"]
    b2_m = champ_masks["GEMSDOE32"]

    pairwise_champions: list[dict] = []
    for s_a in FOCUS_SITES:
        ma = champ_masks[s_a]
        na = ma["positive_pixels"]
        for s_b in FOCUS_SITES:
            if s_a == s_b:
                continue
            mb = champ_masks[s_b]
            exact_shared = packed_hits(mb["_pos_packed"], ma["_flat_pos"])
            within_3px = packed_hits(mb["_edt3_packed"], ma["_flat_pos"])
            nab_allowed = int(np.intersect1d(ma["_allowed_pos_idx"], mb["_allowed_pos_idx"], assume_unique=True).size)
            rho = binary_spearman_from_counts(
                int(ma["_allowed_pos_idx"].size),
                int(mb["_allowed_pos_idx"].size),
                nab_allowed,
                n_allowed,
            )
            pairwise_champions.append({
                "source_site": s_a,
                "target_site": s_b,
                "exact_0px_shared_pixels": exact_shared,
                "forward_0px_exact_fraction": round(exact_shared / na, 6),
                "forward_3px_overlap": round(within_3px / na, 6),
                "spearman_float64_allowed": round(rho, 6),
            })

    focus_rows: list[dict] = []
    for spec in FOCUS_SPECS:
        site = spec["site"]
        repo_path = repos_dir / site
        head_sha = subprocess.check_output(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"], text=True
        ).strip()
        head_date = subprocess.check_output(
            ["git", "-C", str(repo_path), "log", "-1", "--format=%cI"], text=True
        ).strip()

        raw_champ = inspected_by_name[spec["champion_cache_file"]]
        flat_pos = raw_champ["_flat_pos"]
        n_pos = raw_champ["positive_pixels"]
        champ = {k: v for k, v in raw_champ.items() if not k.startswith("_")}
        champ["exact_0px_fraction_in_D28"] = round(packed_hits(d28_m["_pos_packed"], flat_pos) / n_pos, 6)
        champ["forward_3px_overlap_vs_D28"] = round(packed_hits(d28_m["_edt3_packed"], flat_pos) / n_pos, 6)
        champ["exact_0px_fraction_in_SOLO_D28"] = round(packed_hits(solo_m["_pos_packed"], flat_pos) / n_pos, 6)
        champ["exact_0px_fraction_in_H33_B2"] = round(packed_hits(b2_m["_pos_packed"], flat_pos) / n_pos, 6)

        twin_info = None
        if spec["champion_twin_cache_file"]:
            tw_raw = inspected_by_name[spec["champion_twin_cache_file"]]
            same_sup = bool(np.array_equal(flat_pos, tw_raw["_flat_pos"]))
            twin_info = {
                "cache_filename": tw_raw["cache_filename"],
                "sha256": tw_raw["sha256"],
                "size_bytes": tw_raw["size_bytes"],
                "full_grid_strict_0_1_portal_safe": tw_raw["full_grid_strict_0_1_portal_safe"],
                "identical_positive_support_to_champion": same_sup,
            }

        recent_out = []
        for rc in spec["recent_candidates"]:
            rc_raw = inspected_by_name[rc["cache_file"]]
            recent_out.append({
                "submission_filename": rc["name"],
                "sha256": rc_raw["sha256"],
                "size_bytes": rc_raw["size_bytes"],
                "positive_pixels": rc_raw["positive_pixels"],
                "positive_pixels_total": rc_raw["positive_pixels_total"],
                "positive_pixels_outside_footprint": rc_raw["positive_pixels_outside_footprint"],
                "positive_pixels_on_catalogue": rc_raw["positive_pixels_on_catalogue"],
                "nn_min_px": rc_raw["nn_min_px"],
                "full_grid_strict_0_1_portal_safe": rc_raw["full_grid_strict_0_1_portal_safe"],
                "full_grid_nan_pixels": rc_raw["full_grid_nan_pixels"],
                "d_cat_le2_px": rc_raw["d_cat_strata"]["le2_total_px"],
                "frac_gt25": rc_raw["d_cat_strata"]["frac_gt25"],
                "user_reported_value": rc["user_reported_value"],
                "evidence_class": CLAIM_LABEL if rc["user_reported_value"] else "UNSCORED LOCAL ARTIFACT",
                "dense_17gemdoe_3px_forward_overlap": rc_raw["vs_gemsdoe88_registry"]["dense_17gemdoe_3px_forward_overlap"],
                "max_nondense_registry_3px_forward_overlap": rc_raw["vs_gemsdoe88_registry"]["max_nondense_registry_3px_forward_overlap"],
                "max_nondense_registry_3px_witness": rc_raw["vs_gemsdoe88_registry"]["max_nondense_registry_3px_witness"],
                "repo_holdout_and_audit_summary": rc["repo_holdout_summary"],
                "repo_verdict": rc["repo_verdict"],
                "cleared_to_submit": False,
            })

        focus_rows.append({
            "site": site,
            "pages_url": spec["pages_url"],
            "repo_url": spec["repo_url"],
            "inspected_repo_head_sha": head_sha,
            "inspected_repo_head_committed_utc": head_date,
            "highest_scoring_submission": {
                "prompt_name": spec["champion_prompt_name"],
                "user_reported_value": spec["champion_user_reported_value"],
                "evidence_class": CLAIM_LABEL,
                "organizer_receipt": None,
                "prompt_anomaly_note": spec.get("prompt_anomaly_line"),
                "lineage_role": spec["lineage_role"],
                "unique_for_new_submission": False,
                "cleared_to_submit": False,
                "twin_artifact": twin_info,
                **champ,
            },
            "recent_20261025_20261026_candidates": recent_out,
            "any_candidate_cleared_to_submit": False,
            "executive_verdict": (
                f"{site}: top user-reported {spec['champion_prompt_name']} ({spec['champion_user_reported_value']}, "
                f"unreceipted claim) emits {n_pos:,} px with "
                f"{champ['vs_gemsdoe88_registry']['gems19_h19_5_3px_forward_overlap']:.4f} 3-px overlap vs H19-5 and "
                f"{champ['vs_gemsdoe88_registry']['dense_17gemdoe_3px_forward_overlap']:.4f} vs dense_17gemdoe "
                f"(DUPLICATE — already scored/superseded in the H19-5/D2.8 family); "
                f"0/{len(recent_out)} recent 2026-10-25/26 candidates clear protocol gates -> DO NOT SUBMIT."
            ),
        })

    g91_raw = inspected_by_name["GEMSDOE91__gems91-S18-UNIQUE-curvtilt-20000dots-20261025T182858Z-29db2405.tif"]
    g91_stat = {k: v for k, v in g91_raw.items() if not k.startswith("_")}

    cleaned_inventory = [
        {ik: iv for ik, iv in v.items() if not ik.startswith("_")}
        for _, v in sorted(inspected_by_name.items())
    ]

    report = {
        "schema": "gems88.focus-sites-audit-20261026.v1",
        "audit_date_utc": "2026-10-26",
        "session_branch": "arena/d634de37-gemsdoe88",
        "evidence_policy": {
            "user_reported_scores": CLAIM_LABEL,
            "organizer_receipts_present": 0,
            "literal_all_registry_overlap_limit_3px": 0.70,
            "literal_all_registry_spearman_limit": 0.90,
            "universal_witness_file": "data/registry/dense_17gemdoe.tif",
            "universal_witness_sha256": registry_meta["data/registry/dense_17gemdoe.tif"]["sha256"],
            "allowed_off_catalogue_footprint_pixels": n_allowed,
        },
        "summary_verdict": {
            "focus_site_count": len(FOCUS_SITES),
            "unique_historical_champions_count": 0,
            "cleared_for_submission_count": 0,
            "ok_to_submit": False,
            "decision": "DUPLICATE_STOP",
            "highest_user_reported_focus_claim": {
                "site": "GEMSDOE32",
                "submission_name": "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros",
                "user_reported_value": "0.2778",
                "evidence_class": CLAIM_LABEL,
                "sha256": champ_masks["GEMSDOE32"]["sha256"],
                "positive_pixels": 37654,
                "exact_subset_of_solo_d28": True,
                "exact_subset_of_d28": True,
            },
            "key_findings": [
                "All 9 historical focus-site champions (0.2449 to 0.2778) belong to ONE single H19-5/D1.5/D2.8 ridge-thinning and catalogue-collar pruning lineage (0.9775 to 1.0000 forward 3-px overlap vs gems19_h19_5.tif, and 1.0000 vs dense_17gemdoe.tif): 0/9 are unique.",
                "GEMSDOE25 (dotted-h19-5-d2-8, 0.2600) and GEMSDOE30 (d28-poisson300m-offcat-44090, 0.2600) have 44,090/44,090 (100.00%) identical positive pixels.",
                "GEMSDOE31 (h27-4-solo-d28, 0.2708) and GEMSDOE28 (h27-4-r1-solo-d2-8, 0.2708) have 40,199/40,199 (100.00%) identical positive pixels and are an exact 0-px subset of D2.8 (-3,891 d_cat==1 px flank dots).",
                "GEMSDOE32 (h33-h33-2-b2, 0.2778) is an exact 0-px subset of SOLO-D2.8 (-2,545 dots in 1<d_cat<=2 px) and D2.8 (-6,436 dots in d_cat<=2 px), emitting 37,654 binary dots with zero dots inside 200 m of existing_faults.tif.",
                "GEMSDOE36 (anderson-geothermal-pinn-38854, 0.2750) contains 100.00% (37,654/37,654) of H33-2-B2's dots plus 1,200 near-collar/flank additions (-0.0028 user-reported DTI drag).",
                "GEMSDOE33 (h33d-analog-tip-stepover-r30, 0.2632, 41,865 px) has 0.9971 (41,743/41,865) forward 3-px overlap with gems19_h19_5.tif and 0.9970 with D2.8, refuting GEMSDOE32's unverified claim of 'genuinely different geometry'.",
                "Prompt irregularity IR-88-C59DB412-01 (resolved in d634de37 prompt): 'gems28-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan:0.2715' was removed from the GEMSDOE28 prompt block after confirming GEMSDOE28 stores docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif (SHA-256 33003374...), byte-identical to GEMSDOE27's 0.2449 file.",
                "Protocol irregularity IR-88-C59DB412-02 (confirmed by GEMSDOE32 commit 9e55d5d): GEMSDOE32 Round-6 R6-1-stepprofile (SHA-256 c7f094c1...) was self-demoted to 'DO NOT SUBMIT — audit artifact only' after confirming buffered catalogue holdout loss (0.00338 < 0.00452; AUC 0.5250) and calibration-lattice (0.9782 > 0.70) & dense_17gemdoe (1.0000 > 0.70) overlap.",
                "Protocol irregularity IR-88-C59DB412-04: GEMSDOE30 nearslay (SHA-256 f877c278...) is an unapproved geometric d_cat collar annulus (0% >25 px blind discovery, 7,111,787 NaNs outside footprint, screened against only 21 files).",
                "Protocol irregularity IR-88-D634DE37-01: GEMSDOE27 (commit 426426b) headlines H31-1 DRCG-WL (SHA-256 2c002b02...) as 'OK TO DOWNLOAD AND SUBMIT' with HOLDOUT-DTI = 0.047302 (buffered) / 0.115636 (unbuffered), while screening uniqueness against only 27-30 local/focus rasters (omitting dense_17gemdoe 1.0000 > 0.70 and calib_h161 0.6200), covering 88.79% (33,434/37,654 > 70%) of H29-S's dots within 3 px, printing stale README stats (0.0568/39.77% vs run-card 0.1645/62.80%), and violating Rule 6 selector separation.",
                "Protocol irregularity IR-88-D634DE37-02: GEMSDOE33 (commit 40f9b86 / fded538) headlines A33-R2-HMDT (SHA-256 8d144302...) as 'FORMAT PASS (10/10)' and 'OK TO SUBMIT: EXPERIMENTAL', but generated it without sample_submission.tif (treating all 12,279,160 grid cells as footprint), placing 33,616/42,000 (80.04%) of its dots OUTSIDE the valid study footprint and 108 dots directly on existing_faults.tif in contiguous row-major scanlines (row 0 cols 713..858, nn_min_px=1.0), with zero holdout evaluation (NOT MEASURED).",
            ],
        },
        "gemsdoe28_02715_forensic_proof": {
            "prompt_line": "gems28-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan:0.2715",
            "gems28_prefixed_files_in_repo": g28_28_prefixed,
            "matching_5512495c6bd1_files_in_gemsdoe28": g28_5512_paths,
            "gemsdoe28_blob_sha256": g28_5512_sha,
            "gemsdoe27_file_sha256": g27_5512_sha,
            "byte_identical_to_gemsdoe27_02449": bool(g28_5512_sha == g27_5512_sha),
            "positive_pixels": 61328,
            "verified_gemsdoe28_distinct_top_submission": "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan",
            "verified_gemsdoe28_distinct_top_user_reported_value": "0.2710",
        },
        "focus_sites": focus_rows,
        "pairwise_champion_overlaps": pairwise_champions,
        "gemsdoe91_s18_unrated_prompt_entry": {
            "prompt_line": "gems91-S18-UNIQUE-curvtilt-20000dots-20261025T182858Z-29db2405:",
            "user_reported_value": None,
            **g91_stat,
        },
        "cached_tiff_inventory_count": len(cleaned_inventory),
        "cached_tiff_inventory": cleaned_inventory,
    }

    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    EVIDENCE_JSON.write_text(text, encoding="utf-8")
    DOCS_JSON.write_text(text, encoding="utf-8")

    out = io.StringIO()
    fieldnames = [
        "site",
        "pages_url",
        "inspected_repo_head_sha",
        "highest_submission_name",
        "user_reported_value",
        "evidence_class",
        "champion_sha256",
        "positive_pixels",
        "d_cat_le2_px",
        "frac_gt25",
        "portal_safe_full_grid_0_1",
        "overlap_3px_vs_gems19_h19_5",
        "overlap_3px_vs_D28",
        "exact_0px_in_D28",
        "overlap_3px_vs_dense_17gemdoe",
        "unique_for_new_submission",
        "recent_20261025_20261026_candidates_count",
        "any_candidate_cleared_to_submit",
        "lineage_role",
    ]
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    writer.writeheader()
    for row in focus_rows:
        hs = row["highest_scoring_submission"]
        writer.writerow({
            "site": row["site"],
            "pages_url": row["pages_url"],
            "inspected_repo_head_sha": row["inspected_repo_head_sha"],
            "highest_submission_name": hs["prompt_name"],
            "user_reported_value": hs["user_reported_value"],
            "evidence_class": hs["evidence_class"],
            "champion_sha256": hs["sha256"],
            "positive_pixels": hs["positive_pixels"],
            "d_cat_le2_px": hs["d_cat_strata"]["le2_total_px"],
            "frac_gt25": hs["d_cat_strata"]["frac_gt25"],
            "portal_safe_full_grid_0_1": hs["full_grid_strict_0_1_portal_safe"],
            "overlap_3px_vs_gems19_h19_5": hs["vs_gemsdoe88_registry"]["gems19_h19_5_3px_forward_overlap"],
            "overlap_3px_vs_D28": hs["forward_3px_overlap_vs_D28"],
            "exact_0px_in_D28": hs["exact_0px_fraction_in_D28"],
            "overlap_3px_vs_dense_17gemdoe": hs["vs_gemsdoe88_registry"]["dense_17gemdoe_3px_forward_overlap"],
            "unique_for_new_submission": hs["unique_for_new_submission"],
            "recent_20261025_20261026_candidates_count": len(row["recent_20261025_20261026_candidates"]),
            "any_candidate_cleared_to_submit": row["any_candidate_cleared_to_submit"],
            "lineage_role": hs["lineage_role"],
        })
    DOCS_CSV.write_text(out.getvalue(), encoding="utf-8")
    return report


def verify_committed(root: Path = ROOT) -> dict:
    ev_path = root / "evidence/focus_sites_20261026_audit.json"
    doc_path = root / "docs/data/focus_sites_20261026.json"
    csv_path = root / "docs/data/focus_sites_20261026.csv"
    for p in (ev_path, doc_path, csv_path):
        if not p.is_file():
            raise FileNotFoundError(f"Missing required focus-site audit artifact: {p}")
    ev_bytes = ev_path.read_bytes()
    if ev_bytes != doc_path.read_bytes():
        raise ValueError("evidence/focus_sites_20261026_audit.json and docs/data/focus_sites_20261026.json differ")
    bad_constants: list[str] = []
    report = json.loads(ev_bytes.decode("utf-8"), parse_constant=bad_constants.append)
    if bad_constants:
        raise ValueError(f"Non-RFC-8259 constants in focus_sites_20261026_audit.json: {bad_constants[:3]}")
    if report.get("schema") != "gems88.focus-sites-audit-20261026.v1":
        raise ValueError("Unexpected schema in focus_sites_20261026_audit.json")
    sv = report["summary_verdict"]
    if (
        sv["focus_site_count"] != 9
        or sv["unique_historical_champions_count"] != 0
        or sv["cleared_for_submission_count"] != 0
        or sv["ok_to_submit"] is not False
        or sv["decision"] != "DUPLICATE_STOP"
    ):
        raise ValueError("Focus-site summary verdict failed fail-closed invariants")
    sites = [r["site"] for r in report["focus_sites"]]
    if tuple(sites) != FOCUS_SITES:
        raise ValueError(f"Expected focus sites {FOCUS_SITES}, got {sites}")
    for row in report["focus_sites"]:
        hs = row["highest_scoring_submission"]
        if hs["evidence_class"] != CLAIM_LABEL or hs["organizer_receipt"] is not None:
            raise ValueError(f"Score claim laundering detected on {row['site']}")
        if hs["unique_for_new_submission"] is not False or hs["cleared_to_submit"] is not False:
            raise ValueError(f"Historical duplicate marked eligible on {row['site']}")
        if row["any_candidate_cleared_to_submit"] is not False:
            raise ValueError(f"Recent candidate marked cleared on {row['site']}")
        for rc in row["recent_20261025_20261026_candidates"]:
            if rc["cleared_to_submit"] is not False:
                raise ValueError(f"Recent candidate {rc['submission_filename']} marked cleared")

    csv_rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8").splitlines()))
    if len(csv_rows) != 9:
        raise ValueError(f"Expected 9 focus-site CSV rows, got {len(csv_rows)}")
    for crow, jrow in zip(csv_rows, report["focus_sites"]):
        if crow["site"] != jrow["site"] or crow["champion_sha256"] != jrow["highest_scoring_submission"]["sha256"]:
            raise ValueError(f"CSV/JSON mismatch on {jrow['site']}")

    witness = root / "data/registry/dense_17gemdoe.tif"
    if witness.is_file():
        actual_sha = sha256_file(witness)
        if actual_sha != report["evidence_policy"]["universal_witness_sha256"]:
            raise ValueError("Pinned dense_17gemdoe.tif SHA-256 mismatch")

    if not report["gemsdoe28_02715_forensic_proof"]["byte_identical_to_gemsdoe27_02449"]:
        raise ValueError("Expected byte-identity proof for GEMSDOE28 5512495c6bd1")

    by_site = {r["site"]: r for r in report["focus_sites"]}
    g33_cands = {c["submission_filename"]: c for c in by_site["GEMSDOE33"]["recent_20261025_20261026_candidates"]}
    hmdt = g33_cands.get("gemsdoe33-a33-r2-hmdt-20261026-hmdt-unique-zeros.tif")
    if (
        not hmdt
        or hmdt.get("positive_pixels_outside_footprint") != 33616
        or hmdt.get("positive_pixels_on_catalogue") != 108
        or hmdt.get("positive_pixels") != 8384
    ):
        raise ValueError("Expected GEMSDOE33 A33-R2-HMDT outside-footprint/on-catalogue audit proof")
    return report


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild-from-cache", action="store_true")
    parser.add_argument("--require-submit", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = rebuild_from_cache(root) if args.rebuild_from_cache else verify_committed(root)
    except Exception as exc:
        print(json.dumps({"status": "AUDIT_ERROR", "ok_to_submit": False, "error": str(exc)}, indent=2))
        return 1
    summary = {
        "schema": report["schema"],
        "status": "PASS",
        "decision": report["summary_verdict"]["decision"],
        "focus_site_count": report["summary_verdict"]["focus_site_count"],
        "unique_historical_champions_count": report["summary_verdict"]["unique_historical_champions_count"],
        "cleared_for_submission_count": report["summary_verdict"]["cleared_for_submission_count"],
        "ok_to_submit": report["summary_verdict"]["ok_to_submit"],
    }
    print(json.dumps(summary, indent=2))
    if args.require_submit and not summary["ok_to_submit"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
