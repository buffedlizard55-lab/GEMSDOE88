"""Auditable session-review contracts for GEMSDOE88.

This module deliberately contains no model fitting or submission writer.  It is
used by ``scripts/review_repo_20261025.py`` to keep the research queue, source
provenance, and fail-closed decision machine-readable.  In particular, a
format-valid GeoTIFF is not promoted by this module: scientific evidence,
registry uniqueness, and the separate weekly-slot selector remain independent.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
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


# The queue is intentionally separate from historical lanes.  The entries are
# methods to test, not claims that a feature is predictive.  The exact input
# names are the names emitted by src/gems88/physics.py or the 19-band manifest.
HYPOTHESES: tuple[Hypothesis, ...] = (
    Hypothesis(
        1,
        "H88-MTAS",
        (
            "rtp_grad_200m",
            "rtp_grad_800m",
            "grav_grad_200m",
            "grav_grad_800m",
            "depth_to_base_log",
            "det_elev_slope",
            "geod_transtension",
        ),
        "A normalized cross-scale gravity-to-magnetic admittance residual: a short-scale gravity edge that persists while the magnetic edge is smoothed or demagnetized, gated by basin cover and low relief.",
        "A buried or cover-obscured basement discontinuity can retain a density edge without producing a mapped surface scarp; it therefore targets a missing fault rather than copying the catalogue geometry.",
        "An unfaulted intrusive or volcanic lithologic contact with density contrast but weak magnetic contrast; flight-line leveling seams are a second acquisition confounder.",
        "No existing lane in this repository combines the two scale differences across gravity and RTP as one residual. MRR is within-magnetic residualization; PHASE is angular discordance; GTHC is upward-continuation/amplitude logic.",
        "highest",
        "low-medium",
        "none; uses the restored cached stack",
    ),
    Hypothesis(
        2,
        "H88-PRAN",
        (
            "rad_k_over_th",
            "det_elev_slope",
            "topo10_curv_prof",
            "depth_to_base_log",
        ),
        "Terrain-bin-matched radiometric K:Th residual with along-strike coherence, rather than a global radiometric high.",
        "Hydrothermal alteration or soil redistribution along a covered structure may persist in shallow radiometry even when a discrete scarp is absent; matching relief reduces the mapped-scarp shortcut.",
        "K-rich transported alluvium, parent-rock boundaries, and radiometric soil-moisture effects.",
        "MVRD uses radiometric evidence with scarp fields; this candidate tests a terrain-matched conditional null and does not use catalogue geometry for its surface.",
        "medium",
        "low-medium",
        "none; all named layers are already restored",
    ),
    Hypothesis(
        3,
        "H88-FARC",
        (
            "chi_step_max",
            "ksn_jump_norm",
            "topo10_hs_lineament",
            "lidar_scarp_coh",
            "det_elev_slope",
        ),
        "Repeated, signed cross-channel drainage offsets normalized within catchment and channel-order strata, with a matched pseudo-crest null.",
        "A blind rupture crossing several independent channels can leave repeated baseline offsets even when all individual scarps are below mapping confidence; replication is the missing-fault criterion.",
        "Lithologic knickzones, inherited drainage capture, and regional base-level or climate change.",
        "QTSK/TDKL rank absolute knickwaves or scarp polarity; FARC requires cross-catchment replication against a channel-matched null, a different statistic.",
        "medium",
        "medium",
        "none; uses cached DEM-derived channels",
    ),
    Hypothesis(
        4,
        "H88-TCONS",
        (
            "probe2m_dab_local",
            "well_temp_anom",
            "cond_edge_300m",
            "depth_to_base_log",
        ),
        "Depth-conditioned temperature-to-conductivity residual: a local thermal anomaly that is not explained by regional conductance or basin depth.",
        "A focused fluid pathway can produce a thermal response offset from a broad conductive basin halo and may mark a blind permeable fault; the residual is designed to target the mismatch.",
        "Lake-brine conductivity, groundwater circulation, and unfractured permeable lithology.",
        "DHTC combines deep heat/MT and basement structure; TCONS is a conditional residual with head-matched negative controls and no direct vent label.",
        "medium",
        "medium",
        "none for the cached owner-mirror stack; official GDR license must be rechecked before sharing derivatives",
    ),
    Hypothesis(
        5,
        "H88-FLAC",
        (
            "rtp_grad_200m",
            "grav_grad_200m",
            "cond_edge_300m",
            "geod_shearrate",
            "geod_dilaterate",
        ),
        "Multi-sensor edge persistence after an explicit flight-line-direction artifact veto and local cross-sensor continuity test.",
        "A fault-related edge should persist across independent sensors and not be confined to the documented east-west survey-line direction; this can recover a concealed discontinuity while rejecting a processing seam.",
        "Common gridding artifacts, tie-line leveling, and broad lithologic contacts that align with acquisition direction.",
        "MGC/XGCE reward cross-field edge geometry but do not apply a preregistered flight-direction null; FLAC is a robustness/control transform, not a new data source.",
        "low-medium",
        "low",
        "none; GeoDAWN acquisition metadata are official context, not a new raster",
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
    """Replay the original review's five hypotheses, not today's active queue.

    These statuses were recorded before MTAS was later executed. Current
    source-bound proposal/evaluation state is registry/hypothesis_queue.json.
    Source-access records below are likewise historical, not live fetches.
    """

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


# Parallel 78cfb743 proposal snapshot after H88-MTAS (PR #146, negative 0.197730) and
# H88-MMRX (PR #152, negative 0.188378) were executed and archived.
LIVE_UNTRIED_HYPOTHESES: tuple[Hypothesis, ...] = (
    Hypothesis(
        1,
        "H88-FARC",
        (
            "dem10_chi_100m_i16.tif",
            "dem10_chi_100m_sig_i32.tif",
            "topo_10m_derived_100m_u8.tif",
            "lidar_scarp_features_u8.tif",
            "det_elev",
            "det_elev_slope",
        ),
        "Cross-catchment replicated signed fluvial chi/ksn offset polarity across >=3 independent Strahler/chi-stratified drainages along strike, scored against a catchment-permuted pseudo-crest null.",
        "Low-slip piedmont or alluvial-fan fault splays often fall below single-scarp mapping thresholds in individual fans, yet a continuous basement-rooted strand offsets neighboring independent drainages with consistent down-to-basin polarity.",
        "Resistant dipping ash-flow tuff ledges (stratigraphic knickzones), Pleistocene pluvial Lake Lahontan/Bonneville shoreline benches, and drainage-capture divide migration.",
        "QTSK and TDKL score point/pixel knickpoint amplitude or local scarp aspect; PRISM scores piedmont ridge intersections; MMRX tested magnetic marker restoration (negative 0.188378). None tests replicated signed fluvial steps across >=3 independent catchments vs a channel-order null.",
        "high",
        "medium",
        "none beyond restored SHA-pinned stack (upstream public source: USGS 3DEP 10 m DEM)",
    ),
    Hypothesis(
        2,
        "H88-EELG",
        (
            "rtp",
            "tmi_hg",
            "tmi_vg_finite_clamped",
            "iso_grav_anom",
            "iso_grav_anom_hg",
            "iso_grav_anom_vg",
            "depth_to_base_surf",
            "det_elev",
        ),
        "2D windowed Reid-et-al. Euler deconvolution solved for contact/fault structural index N in {0.0, 0.5} independently on isostatic gravity and finite-clamped RTP, retaining tightly clustered horizontal origins (sigma <= 150 m) whose inverted depth z0 agrees with depth_to_base_surf along >=1.5 km strike.",
        "Beneath unbroken Quaternary valley fill where surface scarps are absent, raw horizontal-gradient maxima shift downdip and smear laterally with burial depth; Euler homogeneity inversion collapses dipping step gradients back to the subsurface fault-contact apex while separating step contacts (N ~ 0-0.5) from compact intrusives (N >= 2).",
        "Unfaulted steep plutonic or caldera-margin intrusive contacts, incised paleochannel walls in Tertiary volcanics, and Band 9 (tmi_vg) -FLT_MAX sentinel artifacts if uncleaned.",
        "TILTZERO and GZZC trace zero contours; HGVC and VCAZ use raw horizontal-gradient ridges/azimuths; MTAS used 200 m vs 800 m scalar gradient differences (negative 0.197730). No lane in GEMSDOE88 has solved Euler homogeneity equations for (x0, y0, z0) at structural index N in {0, 0.5} or filtered by depth_to_base_surf consistency.",
        "medium-high",
        "low-medium",
        "none; 100% within core 19-band training_features.tif",
    ),
    Hypothesis(
        3,
        "H88-PRAN",
        (
            "geodawn_rad_u8.tif",
            "rtp",
            "det_elev_slope",
            "depth_to_base_surf",
            "topo_10m_derived_100m_u8.tif",
        ),
        "Terrain-bin-conditioned radiometric K/Th alteration-width asymmetry (stratified on slope, profile curvature, and basement depth to remove bedrock-exposure bias) paired with a co-located RTP magnetite-destruction trough.",
        "Hydrothermal fluid circulation along unmapped permeable fault segments potassically alters wallrock (illite/adularia raising K/Th while oxidizing magnetite, depressing RTP) even when surface scarps are eroded or cemented.",
        "Unfaulted potassic rhyolite domes/ash-flow tuffs, arkosic alluvial fans shed from granitoids, playa-margin clay illuviation, and u8 index quantization limits.",
        "KTH-ANTISYMMETRIC-STEP tested unconditional cross-strike step antisymmetry (negative); MVRD mixed radiometry directly with scarp fields. Neither conditions out topographic outcrop exposure before testing co-located RTP magnetite-destruction troughs.",
        "medium",
        "low-medium",
        "none beyond restored SHA-pinned stack (upstream public source: USGS GeoDAWN CC0 compilation)",
    ),
    Hypothesis(
        4,
        "H88-SESR",
        (
            "geod_2ndinv",
            "geod_shearrate",
            "geod_dilaterate",
            "deq_n100a15",
            "ieq_n100a15",
            "cond_surf",
            "iso_grav_anom_hg",
        ),
        "Kinematic transtension obliquity psi = atan2(geod_dilaterate, geod_shearrate) crossed with microseismic density-gradient edges as a zero-catalogue modulator on sharp gravity/surface-conductance structural boundaries.",
        "Great Basin and Walker Lane blind geothermal conduits concentrate in active transtensional step-overs and accommodation zones where strain transfers across short oblique faults omitted from 1:250k Quaternary fault maps.",
        "Long-wavelength GPS continuum smoothing halos, off-fault volcanic/geothermal swarm seismicity, and conductive evaporite/clay playas.",
        "SDTL used deterministic Mohr-Coulomb stress assumptions; RELAY-DILATIONAL used visible-catalogue geometry; SEPA tested persistence without kinematic shear-dilation obliquity gating on MT+gravity edges.",
        "medium",
        "low",
        "none; 100% within core 19-band training_features.tif",
    ),
    Hypothesis(
        5,
        "H88-FLAC",
        (
            "rtp",
            "iso_grav_anom_hg",
            "cond_surf",
            "det_elev_slope",
            "geodawn_extensions_u8.tif",
        ),
        "Directional steerable-filter decomposition that penalizes narrow E-W (090 deg +- 8 deg) single-sensor magnetic lineaments lacking gravity, conductivity, or topographic corroboration while retaining multi-sensor oblique structures.",
        "Suppressing airborne magnetic flight-line leveling corrugations frees dot budget in covered basins so genuine low-amplitude NNE/NNW concealed intrabasin faults clear the emission threshold without extra false-positive mass.",
        "Genuine E-W transverse accommodation faults or caldera ring fractures lacking density/topographic contrast, plus E-W cultural infrastructure.",
        "SSA, XGCE, and BPWD reward multi-sensor agreement isotropically without an explicit GeoDAWN E-W acquisition-azimuth veto.",
        "low-medium",
        "low",
        "none; GeoDAWN E-W flight-line azimuth comes from official survey metadata",
    ),
)


def executed_registry_lanes(root: Path) -> set[str]:
    """Return canonical lane IDs that already have an executed raster/holdout run card."""
    executed: set[str] = set()
    reg_dir = Path(root) / "registry"
    if not reg_dir.is_dir():
        return executed
    for card_path in sorted(reg_dir.glob("*run_card*.json")):
        try:
            data = json.loads(card_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        lane = data.get("lane") or data.get("lane_id") or data.get("hypothesis_id")
        if not isinstance(lane, str) or not lane.strip():
            continue
        # Pre-placement stop cards (raster_sha256 is None and no holdout dti) do not mark a lane executed.
        has_raster = bool(
            data.get("raster_sha256")
            or (isinstance(data.get("raster"), dict) and data["raster"].get("sha256"))
            or (isinstance(data.get("submission"), dict) and (data["submission"].get("sha256") or data["submission"].get("raster_sha256")))
            or data.get("sha256")
            or data.get("sha256_tif")
        )
        if has_raster:
            executed.add(lane.strip().split()[0])
    return executed


def live_untried_hypothesis_queue(root: Path) -> list[dict[str, Any]]:
    """Return the parallel 78cfb743 proposal snapshot, screening executed IDs.

    This compatibility interface is not the primary site/selector queue. The
    source-bound active queue is registry/hypothesis_queue.json; matching names
    alone cannot establish physical novelty. No source is fetched here.
    """
    rows = [h.as_json() for h in LIVE_UNTRIED_HYPOTHESES]
    validate_hypothesis_queue(rows)
    executed = executed_registry_lanes(root)
    collisions = sorted(row["id"] for row in rows if row["id"] in executed)
    if collisions:
        raise ValueError(f"untried hypothesis queue collides with executed registry lanes: {collisions}")
    return rows

