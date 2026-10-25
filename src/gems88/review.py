"""Auditable session-review contracts for GEMSDOE88.

This module deliberately contains no model fitting or submission writer.  It is
used by ``scripts/review_repo_20261025.py`` to keep the research queue, source
provenance, and fail-closed decision machine-readable.  In particular, a
format-valid GeoTIFF is not promoted by this module: scientific evidence,
registry uniqueness, and the separate weekly-slot selector remain independent.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Hypothesis:
    """One preregistered, falsifiable method candidate.

    ``expected_gain`` and ``implementation_cost`` are ordinal planning labels,
    not scores or probabilities.  Keeping them as strings prevents a planning
    judgement from being accidentally rendered as HOLDOUT-DTI.
    """

    rank: int
    id: str
    layers: tuple[str, ...]
    physical_signature: str
    missing_fault_rationale: str
    non_fault_mimic: str
    difference_from_repo: str
    expected_gain: str
    implementation_cost: str
    external_data: str
    status: str = "UNTESTED"

    def as_json(self) -> dict[str, Any]:
        value = asdict(self)
        value["layers"] = list(self.layers)
        return value


# H88-MTAS is deliberately excluded: registry/mtas88_experiment_run_card.json
# and evidence/mtas88_experiment_20261025.json record that lane as executed and
# negative. The queue below contains only proposals with no matching executable
# experiment/run card in this repository. Exact input names are from
# src/gems88/physics.py / registry/feature_receipt.json; this is not proof that
# the owner-mirrored values are authenticated organizer downloads.
HISTORICALLY_EXECUTED_LANES = frozenset({"H88-MTAS"})

HYPOTHESES: tuple[Hypothesis, ...] = (
    Hypothesis(
        1,
        "H88-FARC",
        (
            "chi_step_max",
            "ksn_jump_norm",
            "topo10_hs_lineament",
            "lidar_scarp_coh",
            "det_elev_slope",
        ),
        "Cross-catchment replication of signed channel-profile breaks, normalized within catchment and channel-order strata and tested against a slope-matched pseudo-crest null.",
        "A blind or unmapped rupture can perturb channel profiles and low-relief surfaces across several independent catchments without producing a single catalogue-grade scarp; repeated, strike-compatible breaks are the proposed discriminator.",
        "Lithologic knickzones, inherited drainage capture, and regional base-level or climate change can also produce channel-profile breaks.",
        "QTSK/TDKL score local knickwave magnitude or scarp polarity. FARC requires cross-catchment replication against a channel-order/slope-matched null; no matching implementation or experiment card was found in this repository.",
        "medium (qualitative; unmeasured)",
        "medium",
        "none proposed; uses existing DEM-derived cached channels. The restored owner mirror is not authenticated against current organizer files.",
    ),
    Hypothesis(
        2,
        "H88-TCONS",
        (
            "probe2m_dab_local",
            "well_temp_anom",
            "cond_edge_300m",
            "depth_to_base_log",
        ),
        "A depth-conditioned temperature-to-conductivity residual: retain local thermal anomalies not explained by regional conductance or basin depth, then test spatial coherence along blind structures.",
        "Focused fluid flow could make a thermal/conductivity residual near a buried fault even where the surface scarp is absent; this tests a geothermal-fluid association rather than treating a vent as a fault label.",
        "Lake-brine conductivity, groundwater circulation, and unfractured permeable lithology can produce the same thermal/conductive anomaly.",
        "DHTC combines deep heat/MT and basement structure; TCONS would use head-/depth-matched negative controls to isolate the conditional residual. No exact TCONS method was found in the repository.",
        "medium potential, high uncertainty (qualitative; unmeasured)",
        "high",
        "none proposed beyond the cached stack; before sharing derivatives, verify the official DOE GDR INGENIOUS source and license at https://gdr.openei.org/submissions/1391. Current owner-mirror provenance is not independently authenticated.",
    ),
    Hypothesis(
        3,
        "H88-PRAN",
        (
            "rad_k_over_th",
            "det_elev_slope",
            "topo10_curv_prof",
            "depth_to_base_log",
        ),
        "A terrain-bin-matched K:Th radiometric residual with along-strike persistence, rather than a global radiometric high.",
        "Hydrothermal alteration or soil redistribution along a covered structure may persist in shallow radiometry even where no discrete scarp was mapped; terrain matching is intended to remove relief-related baseline effects.",
        "K-rich transported alluvium, parent-rock boundaries, and soil-moisture effects can produce the same K:Th contrast.",
        "MVRD uses radiometric evidence with scarp fields; PRAN proposes a terrain-conditioned null and along-strike persistence rather than catalogue-derived placement. No exact PRAN experiment was found in the repository.",
        "low-to-medium (qualitative; unmeasured)",
        "low-to-medium",
        "none proposed; uses cached GeoDAWN-derived radiometry and existing terrain layers. The owner-mirror values and redistribution terms still require verification.",
    ),
    Hypothesis(
        4,
        "H88-FLAC",
        (
            "rtp_grad_200m",
            "grav_grad_200m",
            "cond_edge_300m",
            "geod_shearrate",
            "geod_dilaterate",
        ),
        "Cross-sensor edge persistence after a predeclared survey-line-direction artifact veto and local continuity test.",
        "A real concealed structure should be supported by independent sensors and should not exist only as an acquisition-direction seam; this is a robustness-oriented detector for faults lacking obvious surface expression.",
        "Tie-line leveling, gridding artifacts, and broad lithologic contacts aligned with acquisition direction can mimic the signature.",
        "MGC/XGCE compare cross-field edge geometry but do not use this explicit flight-direction null; FLAC is a quality-controlled edge persistence test. No exact FLAC experiment was found in the repository.",
        "low (qualitative; unmeasured)",
        "low",
        "none proposed; GeoDAWN acquisition metadata is an official manual-review source, not a new raster. The current run did not re-fetch that source.",
    ),
)

OFFICIAL_SOURCES: tuple[dict[str, str], ...] = (
    {
        "id": "competition_problem",
        "url": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
        "status": "OFFICIAL_PAGE_FETCHED_2026-10-25",
        "verified_claim": "The target is geological faults indicative of geothermal resources; the page states the 100 m EPSG:32611 feature grid, [0,1] GeoTIFF predictions, and 300 m triangular distance weighting.",
    },
    {
        "id": "competition_leaderboard",
        "url": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
        "status": "OFFICIAL_PAGE_FETCHED_2026-10-25",
        "verified_claim": "The fetched public page displayed xiaofanhu at 0.4413. This is OBSERVED-PUBLIC, not a score for a GEMSDOE88 artifact and not a private/final result.",
    },
    {
        "id": "competition_data",
        "url": "https://www.drivendata.org/competitions/306/competition-doe-gems/data/",
        "status": "OFFICIAL_MANUAL_REVIEW_LINK_AUTHENTICATION_REQUIRED",
        "verified_claim": "The organizer data page is the authoritative place to obtain challenge files; this sandbox uses no DrivenData credentials and does not call it as an authenticated download.",
    },
    {
        "id": "official_rules",
        "url": "https://docs.nlr.gov/docs/fy26osti/96647.pdf",
        "status": "OFFICIAL_PDF_FETCHED_2026-10-25",
        "verified_claim": "The rules state that one 100 m GeoTIFF is submitted, allow up to three submissions per week as specified by the website, and require one selected submission for both prize rounds; they also require disclosure of generative-AI use.",
    },
    {
        "id": "reference_solution",
        "url": "https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b",
        "status": "OFFICIAL_REPOSITORY_HASH_VERIFIED_2026-10-25",
        "verified_claim": "The pinned README instructs competitors to obtain competition data from the challenge website and documents CPU-only and GPU environment options.",
    },
    {
        "id": "geodawn",
        "url": "https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and",
        "status": "OFFICIAL_USGS_PAGE_FETCHED_2026-10-25",
        "verified_claim": "USGS describes the magnetic/radiometric survey, lidar coordination, flight specifications, processing, and CC0 rights on the landing page.",
    },
    {
        "id": "ingenious",
        "url": "https://gdr.openei.org/submissions/1391",
        "status": "OFFICIAL_GDR_PAGE_FETCHED_2026-10-25",
        "verified_claim": "The GDR page identifies the INGENIOUS Great Basin compilation, DOI 10.15121/1881483, free access, and a CC BY 4.0 license link; individual derivative rights still require checking.",
    },
    {
        "id": "epsg_32611",
        "url": "https://epsg.io/32611",
        "status": "EPSG_PAGE_FETCHED_2026-10-25",
        "verified_claim": "EPSG:32611 is WGS 84 / UTM zone 11N with metre units; the page is the CRS reference, not a competition submission receipt.",
    },
)


def hypothesis_queue() -> list[dict[str, Any]]:
    """Return a JSON-safe copy of the current, unexecuted candidate queue."""

    return [h.as_json() for h in HYPOTHESES]


def validate_hypothesis_queue(queue: list[dict[str, Any]] | None = None) -> None:
    """Fail closed if a report accidentally loses the requested ranking fields."""

    rows = hypothesis_queue() if queue is None else queue
    if not 3 <= len(rows) <= 5:
        raise ValueError(f"expected 3-5 hypotheses, got {len(rows)}")
    ranks = [int(row["rank"]) for row in rows]
    if ranks != list(range(1, len(rows) + 1)):
        raise ValueError(f"hypothesis ranks must be consecutive from 1: {ranks}")
    ids = [row["id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("hypothesis ids must be unique")
    completed = sorted(set(ids) & HISTORICALLY_EXECUTED_LANES)
    if completed:
        raise ValueError(f"executed lanes cannot be advertised as untested: {completed}")
    required = (
        "layers",
        "physical_signature",
        "missing_fault_rationale",
        "non_fault_mimic",
        "difference_from_repo",
        "expected_gain",
        "implementation_cost",
        "external_data",
    )
    for row in rows:
        if row.get("status") != "UNTESTED":
            raise ValueError(f"historical/untested status mismatch for {row.get('id')}")
        for key in required:
            value = row.get(key)
            if not value:
                raise ValueError(f"hypothesis {row.get('id')} missing {key}")


def safe_note(note: str, *, maximum: int = 140) -> str:
    """Validate a portal note without truncating it or silently changing it."""

    if not isinstance(note, str) or not note.strip():
        raise ValueError("submission note must be non-empty text")
    if len(note) > maximum:
        raise ValueError(f"submission note is {len(note)} characters; maximum is {maximum}")
    return note
