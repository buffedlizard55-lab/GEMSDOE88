# Session `d498c1ca` (2026-10-26) — ranked untried hypotheses

**Execution gate:** `DUPLICATE_STOP`. `scripts/generation_guard.py` forbids feature construction, holdout fitting, and TIFF writing. **0 experiments, 0 new rasters, 0 weekly slots.** Expected DTI is **not** written as a score.

These five mechanisms were grep-checked against `src/gems88/`, `scripts/`, and `NEW_HYPOTHESES.md` names. They are **not** authorization to bypass the unique-raster rule.

| Rank | ID | Layers | Signature | Why off-catalogue | Cost | New data? |
|---:|---|---|---|---|---|---|
| 1 | **H88-CURPD** | `training_features.tif` B02 `rtp`, B09 `tmi_vg`, B15 `depth_to_base_surf` | Spector–Grant radially averaged log-power slope → Curie-point depth undulation | Blind basin interiors lack Qfaults scarps but may show shallow Curie troughs from hydrothermal heat | Low–med (FFT windows) | No |
| 2 | **H88-AIRYFX** | B13 `iso_grav_anom`, B18 `iso_grav_anom_hg`, B12 `det_elev`, B15 | Residual of Airy isostatic prediction vs observed Bouguer/isostatic anomaly at flexural wavelengths | Buried range-front steps under fans without LiDAR scarps | Med | No |
| 3 | **H88-THAZ** | `2m_temperature_probe.tif`, B18 gravity HG, B17 `cond_surf` | Horizontal thermal-gradient **azimuth** vs gravity-step strike (not Peclet concavity / VCAZ) | Blind upflow corridors misaligned with mapped scarps | Low | No |
| 4 | **H88-RADPER** | B02 tilt-from-RTP, B09 VG, lidar scarp u8 if present | Radon-domain persistence of linear magnetic tilt zeros **after** drainage-azimuth veto | Catches linear basement edges missed by dotted-ridge H19.5 copies | Med | No |
| 5 | **H88-USMT** | B15, B17 + USGS/IRIS 3D MT | Phase-tensor skew β_PT / tipper | Deep roots of blind systems | High | **Yes** — [ScienceBase](https://www.sciencebase.gov/catalog/), [IRIS SPUD EMTF](https://ds.iris.edu/spud/emtf), [GDR 1391](https://gdr.openei.org/submissions/1391). **Not fetchable** on this sandbox allowlist. |

**Named non-fault mimics:** (1) remanent volcanic Curie artifacts; (2) unfaulted crustal root Airy mismatch; (3) playa brine thermal stripes; (4) canal/road linear culture; (5) galvanic distortion.

**Different from this repo:** BPWD/PSGV use Baranov/Poisson worms, not Spector–Grant z_Curie maps; VCAZ uses vertical Peclet, not horizontal thermal azimuth; MTAS is mag-grav admittance not Airy residual; GEMSDOE42 worm-persistence is a sibling claim, not implemented here.

**Conditional first choice if the 17GEMSDOE rule is revised:** H88-CURPD (local stack only). **Not run this session.**
