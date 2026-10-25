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
    novelty_scope: str = (
        "The exact formulation was not found in the checked repository; related feature families exist. "
        "This is not a claim of global or fleet-wide novelty."
    )

    def as_json(self) -> dict[str, Any]:
        value = asdict(self)
        value["layers"] = list(self.layers)
        return value


# This is a method-level shortlist, not a claim that its raw inputs or broad
# geological families are new.  Exact formulations are untested; related lanes
# are named in each contrast.  Historical H88-MTAS is deliberately excluded.
HYPOTHESES: tuple[Hypothesis, ...] = (
    Hypothesis(
        1,
        "MAGNETIC-MARKER-RESTORATION",
        (
            "training_features.tif:B02_rtp",
            "training_features.tif:B14_tmi",
            "training_features.tif:B13_iso_grav_anom",
            "training_features.tif:B12_det_elev",
            "training_features.tif:B15_depth_to_base_surf",
        ),
        "Whiten paired magnetic texture patches on opposite sides of a candidate discontinuity; estimate a translation by phase correlation and require a stable displacement that restores marker continuity across independent swaths.",
        "A buried or covered basement rupture can offset a subsurface magnetic marker while leaving no resolvable surface scarp; the signal is the repeatable displacement, not a ridge crest or mapped-fault distance.",
        "Depositional facies pinch-out or an intrusive contact; GeoDAWN flight-line leveling seams are an acquisition confounder.",
        "MAG-FABRIC-DISLOCATION measures opposite-side axial gradient-orientation change, while PHASE/XGCE compare gradient geometry. None of those exact implementations estimates a translation that restores matched-patch texture continuity; the conceptual magnetic-dislocation family is related, not novel globally.",
        "moderate, uncertain",
        "medium-high",
        "No new raster proposed; uses bands in the existing feature manifest. The full training stack is absent in this checkout and owner-mirror provenance/rights were not refreshed this review.",
    ),
    Hypothesis(
        2,
        "DRAINAGE-VETOED-SCARP-PROFILE-RESTORATION",
        (
            "training_features.tif:B12_det_elev",
            "training_features.tif:B19_det_elev_slope",
            "topo_10m_derived_100m_u8.tif:curvature_relief_aspect",
            "lidar_scarp_features_u8.tif:downface_upface_cross_scarp",
        ),
        "Fit flanking elevation profiles to a shared smooth landform plus a signed step; compare held-out profile likelihood against a smooth no-step null, repeat along strike, and veto drainage-aligned corridors.",
        "Low-amplitude cover-softened offsets can be invisible to a single-cell ridge detector but become measurable when the same signed step repeats along an otherwise continuous piedmont profile.",
        "Fluvial terrace risers, fan toes and pluvial shoreline benches.",
        "TDKL, VESS, LSC and SHORE use scarp/knickpoint evidence, but the exact held-out profile-restoration likelihood with a preregistered drainage veto was not found. This is a new test statistic within a heavily tested scarp family, not a globally novel geological idea.",
        "moderate-low, uncertain",
        "medium",
        "No new raster proposed; depends on existing terrain/LiDAR-derived inputs. The full feature stack is absent here and source-byte identity/redistribution terms were not freshly authenticated.",
    ),
    Hypothesis(
        3,
        "TERRAIN-MATCHED-ALTERATION-WIDTH-ASYMMETRY",
        (
            "geodawn_rad_u8.tif:K_Th_U",
            "training_features.tif:B02_rtp",
            "training_features.tif:B19_det_elev_slope",
            "training_features.tif:B15_depth_to_base_surf",
        ),
        "After fitting a terrain- and parent-background-matched radiometric null on training blocks, compare cross-strike K:Th residual decay widths on opposite flanks; require a localized magnetic-amplitude depression, not a radiometric edge alone.",
        "A concealed fluid pathway may alter one permeable wall more broadly than the other even where the fault lacks a mapped surface break; paired flank width reduces broad lithologic-background effects.",
        "Differential weathering of adjacent units, transported K-rich alluvium and soil-moisture effects.",
        "KTH-88 already tests a signed opposite-flank K:Th step and MVRD/other lanes use radiometric or redox evidence. The untested formulation is terrain-matched residual decay-width asymmetry, not generic K:Th enrichment or asymmetry.",
        "low-moderate, uncertain",
        "medium",
        "No new raster proposed; existing GeoDAWN-derived channels are referenced. The full stack is absent and this review did not refresh GeoDAWN provenance or derivative-sharing terms.",
    ),
    Hypothesis(
        4,
        "CONDUCTIVE-BASIN-BREACH-CONTINUITY",
        (
            "training_features.tif:B17_cond_surf",
            "training_features.tif:B13_iso_grav_anom",
            "training_features.tif:B15_depth_to_base_surf",
            "training_features.tif:B12_det_elev",
        ),
        "Test whether a narrow conductive connection crosses an independently estimated basin-boundary saddle and coincides with a basement/gravity discontinuity; compare with a smooth basin-fill model and a drainage-aligned null.",
        "A covered permeable connection crossing a structural basin boundary could be omitted by surface-trace mapping and could mark a blind geothermal fluid pathway.",
        "An unfaulted permeable alluvial paleochannel or saline groundwater plume.",
        "CTRA/DHTC use conductive curvature, thermal or multi-sensor co-occurrence. No exact topology-preserving breach-across-saddle test with a drainage-aligned null was found; its component sensors and conductive-fault family are already represented.",
        "low, uncertain",
        "medium-high",
        "No new raster proposed; depends on existing conductance/gravity/depth bands. Their full-stack availability, organizer identity and reuse terms are not freshly verified here.",
    ),
)


OFFICIAL_SOURCES: tuple[dict[str, str], ...] = (
    {
        "id": "competition_problem",
        "url": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
        "status": "LINKED_NOT_FETCHED_IN_THIS_REVIEW",
        "verified_claim": "Official manual-review link only. Claims in prior local source ledgers are historical and were not refreshed here.",
    },
    {
        "id": "competition_leaderboard",
        "url": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
        "status": "NOT_FETCHED_IN_THIS_REVIEW_CURRENT_STANDING_UNVERIFIED",
        "verified_claim": "No current leaderboard retrieval was made. The 0.3195 and 0.4413 figures remain differently scoped historical/user-reported claims in repository materials.",
    },
    {
        "id": "competition_data",
        "url": "https://www.drivendata.org/competitions/306/competition-doe-gems/data/",
        "status": "AUTHENTICATED_ACCESS_NOT_AVAILABLE",
        "verified_claim": "Official review link only; no DrivenData login or authenticated download was used. Owner-mirror hashes do not authenticate organizer bytes or redistribution rights.",
    },
    {
        "id": "official_rules",
        "url": "https://docs.nlr.gov/docs/fy26osti/96647.pdf",
        "status": "NOT_FETCHED_IN_THIS_REVIEW",
        "verified_claim": "Official manual-review link only. No current rules, deadline, weekly allowance or terms are asserted from a fresh retrieval.",
    },
    {
        "id": "reference_solution",
        "url": "https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md",
        "status": "PINNED_GITHUB_HTML_FETCHED_2026-10-25; API_ATTEMPT_403",
        "verified_claim": "The GitHub API request returned HTTP 403 rate limit at 2026-10-25 13:52:36 UTC, but a later fetch_page of this exact pinned GitHub HTML URL succeeded. The README identifies the official GEMS Prize reference solution, directs data downloads to the challenge website, and describes CPU-only and GPU options (including Apple Silicon MPS). This does not authenticate organizer data, current rules, or any score receipt.",
    },
    {
        "id": "geodawn",
        "url": "https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and",
        "status": "LINKED_NOT_FETCHED_IN_THIS_REVIEW",
        "verified_claim": "Official manual-review link only; no new USGS retrieval or license/availability check was made.",
    },
    {
        "id": "ingenious",
        "url": "https://gdr.openei.org/submissions/1391",
        "status": "LINKED_NOT_FETCHED_IN_THIS_REVIEW",
        "verified_claim": "Official manual-review link only; no new GDR retrieval or derivative-rights check was made.",
    },
    {
        "id": "usgs_3dep",
        "url": "https://www.usgs.gov/3d-elevation-program",
        "status": "LINKED_NOT_FETCHED_IN_THIS_REVIEW",
        "verified_claim": "Official manual-review link only; no new 3DEP availability or license check was made.",
    },
    {
        "id": "epsg_32611",
        "url": "https://epsg.io/32611",
        "status": "LINKED_NOT_FETCHED_IN_THIS_REVIEW",
        "verified_claim": "CRS review link only; no new EPSG retrieval was made.",
    },
)


def hypothesis_queue() -> list[dict[str, Any]]:
    """Return a JSON-safe copy of four method-level, untested formulations."""

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
    required = (
        "layers",
        "physical_signature",
        "missing_fault_rationale",
        "non_fault_mimic",
        "difference_from_repo",
        "expected_gain",
        "implementation_cost",
        "external_data",
        "novelty_scope",
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
