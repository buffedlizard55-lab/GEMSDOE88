#!/usr/bin/env python3
"""Deterministically restore hash-pinned competition, registry, and external inputs.

* ``python scripts/restore_inputs.py --validation`` restores ``sample_submission.tif``,
  ``existing_faults.tif``, and all 18 multi-repo registry rasters in ``data/registry/``.
* ``python scripts/restore_inputs.py`` additionally restores the 19-band 419 MB
  ``data/training_features.tif`` and 15 official-source external datasets.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

FEATURE_REPO = "https://github.com/buffedlizard55-lab/GEMSDOE.git"
FEATURE_COMMIT = "bb2e070a3659f4f5c16ac927e62606f1f7f495a6"
FEATURE_SHA256 = "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5"
# Actual blob names in the pinned GEMSDOE commit (verified 2026-10-23 via the
# GitHub contents API); the earlier ``training_features.tif.part0N`` guess did not
# exist and made ``restore_inputs.py`` die with FileNotFoundError.
FEATURE_PARTS = [f"data/bridge/gems-geodawn-numerical-features.tif.part-00{i}" for i in range(5)]

VALIDATION_GROUPS = [
  [
    "60GEMSDOE-core-and-early-registry",
    "https://github.com/buffedlizard55-lab/60GEMSDOE.git",
    "02563d07fb85d2f4d35887503d380d34d4017197",
    [
      [
        "data/official/sample_submission.tif",
        "data/bridge/sample_submission.tif",
        "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"
      ],
      [
        "data/official/existing_faults.tif",
        "data/bridge/existing_faults.tif",
        "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093"
      ],
      [
        "registry/rasters/GEMSDOE32__h33-2-b2-zeros.tif",
        "data/registry/h33_education.tif",
        "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
      ],
      [
        "registry/rasters/19GEMSDOE__h19-5-powerlaw-budget-multiline.tif",
        "data/registry/gems19_h19_5.tif",
        "ef2ae808eb7179861b9f1ff753fd3ded625ace7b7c158e29cec45bbd8fa3cfaa"
      ],
      [
        "registry/rasters/GEMSDOE25__dotted-h19-5-d2-8.tif",
        "data/registry/gems25_d28.tif",
        "3e78737f0da8dd2ca66cc6caac0ce8eeefcd6715707f8d1bd3091845cd9bcc30"
      ],
      [
        "registry/rasters/GEMSDOE28__h27-4-r1-solo-d2-8.tif",
        "data/registry/gems28_h27_4.tif",
        "2fc94a38d77f74d4f4ed1a97a83e7bb71a1ceea090515ec641e6681cc47c44c8"
      ],
      [
        "registry/rasters/GEMSDOE36__anderson-geothermal-pinn-38854.tif",
        "data/registry/gems36_anderson_pinn.tif",
        "e15891020b9c57056ac7fa874a5e506fbd6ed9314a4ea8e73af0753887a3708a"
      ],
      [
        "registry/rasters/GEMSDOE49__gate_ortho_w0.25-40k.tif",
        "data/registry/gems49_gate_ortho.tif",
        "3722e26fbf9129874be1fb8c687825803952c57ef1154ed0a21029596bc412f1"
      ],
      [
        "registry/rasters/57GEMSDOE__h57r2-shipped8-all-flank0-20261009T180433Z-90e532947353-zeros.tif",
        "data/registry/gems57_h57r2.tif",
        "9afe74ab2b2fa631e9276cd8e8685fc76086d96d01181101998309b0c0d06a47"
      ],
      [
        "submission/gems60-h68-dem10-lidar-piedmont-dksn-40000-20261011T185033Z-6e9b1e286c45-zeros.tif",
        "data/registry/gems60_h68_piedmont.tif",
        "f4aa17400c7ff9ae12a428862ccaa4e2b0397015a3a7e7b55aa006341599f8ed"
      ],
      [
        "registry/rasters/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif",
        "data/registry/family_60gemsdoe/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif",
        "baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd"
      ],
      [
        "registry/rasters/calib_h195_01922.tif",
        "data/registry/family_60gemsdoe/calib_h195_01922.tif",
        "ec1f9b56b83ce33cad781ceb9f104b18fb4f2ff785263a4e89616af4aabdee8d"
      ],
      [
        "registry/rasters/calib_d15_02477.tif",
        "data/registry/family_60gemsdoe/calib_d15_02477.tif",
        "68d0e2e4fcc594f9a23f56c44b885fee733d026d39be55e18ad2a07289525310"
      ],
      [
        "registry/rasters/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif",
        "data/registry/family_60gemsdoe/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif",
        "91eae1ca42ec845eaa8c2ba32da49806e24751743459b8a10017c479bbe639b8"
      ],
      [
        "registry/rasters/GEMSDOE28__h27-4-r1-solo-d2-8.tif",
        "data/registry/family_60gemsdoe/GEMSDOE28__h27-4-r1-solo-d2-8.tif",
        "2fc94a38d77f74d4f4ed1a97a83e7bb71a1ceea090515ec641e6681cc47c44c8"
      ],
      [
        "registry/rasters/calib_h194_01894.tif",
        "data/registry/family_60gemsdoe/calib_h194_01894.tif",
        "89109a3bd2cd3b12e7a0f388113c519843acfc9c4f46825affefc3e63dd99b22"
      ],
      [
        "registry/rasters/calib_h161_01855.tif",
        "data/registry/family_60gemsdoe/calib_h161_01855.tif",
        "055309694ed499ca3d87e76b3f5e81c292aef6e39c418d33ff5a817aa1309bea"
      ]
    ]
  ],
  [
    "GEMSDOE24-sgmc-validation",
    "https://github.com/buffedlizard55-lab/GEMSDOE24.git",
    "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
    [
      [
        "data/external/derived_sgmc_faults_100m_u8.tif",
        "data/external/derived_sgmc_faults_100m_u8.tif",
        "643cbe992ef4ba37588fb469163ed8291e3ceb23d6c1f78a3cfaa462430c2da0"
      ]
    ]
  ],
  [
    "17GEMSDOE-witness",
    "https://github.com/buffedlizard55-lab/17GEMSDOE.git",
    "6fc71d19d49dca4960d5434bd81b6dd06fcc030a",
    [
      [
        "docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif",
        "data/registry/dense_17gemdoe.tif",
        "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
      ]
    ]
  ],
  [
    "GEMSDOE70-registry",
    "https://github.com/buffedlizard55-lab/GEMSDOE70.git",
    "158aec19800d4c7b8ca9fb94b06567e2b7d61e8d",
    [
      [
        "docs/downloads/gems70-p5-multiphysics-submodular-37654-20261020.tif",
        "data/registry/gems70_p5_multiphysics.tif",
        "f19a78d511f9d822b47ad4d9ce56cf2ccfa415e3d1ca49709a342158de6e7a84"
      ],
      [
        "docs/downloads/gems70-p5-dual-submod300-oof38k-20261020.tif",
        "data/registry/gems70_p5_dualsubmod.tif",
        "d0e41ce921afcf3af33b7d86d75f6a258653dfbb4d050e864babe643245f0ea8"
      ]
    ]
  ],
  [
    "GEMSDOE78-registry",
    "https://github.com/buffedlizard55-lab/GEMSDOE78.git",
    "30f1ab9400f92036b0bc613425f1b5b6046f3897",
    [
      [
        "docs/downloads/gems78-h78-gfv-136b-dink-20261022T070254Z-45cd56e7-zeros.tif",
        "data/registry/gems78_h78_gfv.tif",
        "0338383df9c36c0a2581ddc584e6aafa5ce364ba52cd9e56749628bc4301dd07"
      ]
    ]
  ],
  [
    "GEMSDOE80-registry",
    "https://github.com/buffedlizard55-lab/GEMSDOE80.git",
    "02f8fd64be24de6b90d03c56b675d8a3ac2bbc3c",
    [
      [
        "docs/downloads/gems80-adpt-kkt-lagrangian-36500d-20261022T012049Z-5bd11c85-zeros.tif",
        "data/registry/gems80_adpt_kkt.tif",
        "f538f414fb11169342bb613a9c9c1eb9e075278c511e694d55c96ba0760851f9"
      ],
      [
        "docs/downloads/gems80-h80-dpvc-updip-vent-submod-41600-20261021-zeros.tif",
        "data/registry/gems80_h80_dpvc.tif",
        "b5a6b686ca06af635d682f38cc898156649ae6508fa27fc651455a031f6261a5"
      ]
    ]
  ],
  [
    "GEMSDOE81-registry",
    "https://github.com/buffedlizard55-lab/GEMSDOE81.git",
    "15bf850cfd68dc54f14b96a558f750798a0c4ac8",
    [
      [
        "docs/downloads/gems81-contasb-poisson44090-buf2-20261021T232312Z-04866ff3-zeros.tif",
        "data/registry/gems81_contasb.tif",
        "5d8cd25771a95cd652b99bc13f4cd6c9c0435ce9763f0159609aa7b5033e33d4"
      ]
    ]
  ],
  [
    "GEMSDOE82-registry",
    "https://github.com/buffedlizard55-lab/GEMSDOE82.git",
    "4fb7df6f650f98690c547b4e23bf17deeaa9b141",
    [
      [
        "docs/downloads/gems82-h82-csam-dinkelbach-41200-20261021-zeros.tif",
        "data/registry/gems82_csam_dink.tif",
        "18bdf3f4eb021b0b2a45aca2627d9c81c656d366618cc9f39f413f2163e01767"
      ]
    ]
  ],
  [
    "GEMSDOE83-registry",
    "https://github.com/buffedlizard55-lab/GEMSDOE83.git",
    "da9ec5a3b474e32fe8b124ac079e665315474bbf",
    [
      [
        "docs/downloads/gems83-h83-gvcd-dink300-37654dots-20261021-1a373694-zeros.tif",
        "data/registry/gems83_h83_gvcd.tif",
        "79f14dc84cd7760cb44645bc090ed2d33dbcfe789cec844fd83753fcff1082a2"
      ]
    ]
  ],
  [
    "GEMSDOE85-registry",
    "https://github.com/buffedlizard55-lab/GEMSDOE85.git",
    "2a20a014db0cceeba57e7d7fc507aa68f59e8692",
    [
      [
        "submissions/gems85-h85a-foldproper-hgb-maxcov-37654-20261022T221031Z-bf96e456-zeros.tif",
        "data/registry/gems85_h85a_foldproper.tif",
        "ccc8a7a4e53c406de00c5ba40612f5d3df2b0f4afc869dd1b997d5b836a0209b"
      ]
    ]
  ]
]

EXTERNAL_GROUP = [
  "60GEMSDOE-external-official",
  "https://github.com/buffedlizard55-lab/60GEMSDOE.git",
  "02563d07fb85d2f4d35887503d380d34d4017197",
  [
    [
      "data/external/2m_temperature_probe_INGENIOUS_regional_data.zip",
      "data/external/2m_temperature_probe_INGENIOUS_regional_data.zip",
      "1301f70d230058e616ea5d34d1c7a32fabf7d49198172f376c59c89bd652eca3"
    ],
    [
      "data/external/paleo_geothermal_regional.zip",
      "data/external/paleo_geothermal_regional.zip",
      "faffcf697f32dbbf6cbb317cd1effb3e305538ce38eb239d72d0c6fa071e91ca"
    ],
    [
      "data/external/gdr_wellspring_in_footprint.csv",
      "data/external/gdr_wellspring_in_footprint.csv",
      "122718e65bdf55aab0ee12ad20d80062f0deb1de957225a61ad880dd5dc196ea"
    ],
    [
      "data/external/gdr_volcanic_vents_in_footprint.csv",
      "data/external/gdr_volcanic_vents_in_footprint.csv",
      "f91bafbaccaaf2754e71d60434fc0f9eb2c7b880c6e714883f4974542ff6a0bf"
    ],
    [
      "data/external/trace_segments_utm11.csv",
      "data/external/trace_segments_utm11.csv",
      "c5edf9df3e0e1413c52784884fc38e5b9ca54627b27c6f8baf7713e908f48513"
    ],
    [
      "data/external/lidar_scarp_features_u8.tif",
      "data/external/lidar_scarp_features_u8.tif",
      "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568"
    ],
    [
      "data/external/geodawn_rad_u8.tif",
      "data/external/geodawn_rad_u8.tif",
      "c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682"
    ],
    [
      "data/external/geodawn_extensions_u8.tif",
      "data/external/geodawn_extensions_u8.tif",
      "a35a9c6d2a14786f4dab85481ee59769213072f5dab5b2535ea82ae4d9bb7d9b"
    ],
    [
      "data/external/topo_10m_derived_100m_u8.tif",
      "data/external/topo_10m_derived_100m_u8.tif",
      "a6398d9950965dec6aae6ccecdaa6ced48645d133eab222cbdd11def9bdabfa4"
    ],
    [
      "data/external/dem10_chi_100m_i16.tif",
      "data/external/dem10_chi_100m_i16.tif",
      "8897ba9c30ef1cd7ad5f23c16c6dfd7bb070e7e757f36fd9486eb45edfd973a5"
    ],
    [
      "data/external/dem10_chi_100m.manifest.json",
      "data/external/dem10_chi_100m.manifest.json",
      "187a961ef5da45278c84b25d16296a5f3458da37abff45046d31ed58b9f5af86"
    ],
    [
      "data/external/topo_10m_derived_100m_u8.manifest.json",
      "data/external/topo_10m_derived_100m_u8.manifest.json",
      "181d5527ba7ed2990031918a8b6c9d5d94e3998b2daf656de0c33322ca94120a"
    ],
    [
      "data/external/audit_sources/receipt.json",
      "data/external/audit_sources/receipt.json",
      "45ce9c1cfa91d15358cf22d73735f42d3598931e7d9dfe431576868e7a1011e9"
    ],
    [
      "data/external/sgmc_faults_100m.tif",
      "data/external/sgmc_faults_100m.tif",
      "26d142c4c93282cd94f6950ab96f22aeff59fbbea523d43d662e76fa1b161b5c"
    ],
    [
      "data/geodawn_dem_a2_100m.tif",
      "data/geodawn_dem_a2_100m.tif",
      "d32762a38222764389e948da423ebc6cadd00ac617ad3938d3dd79c6cfe14431"
    ]
  ]
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ok(rel: str, want: str) -> bool:
    p = ROOT / rel
    return p.exists() and sha256(p) == want


def sparse_fetch(repo: str, commit: str, paths: list[str], tmp: Path) -> Path:
    co = tmp / "m"
    subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", "--sparse", repo, str(co)], check=True)
    subprocess.run(["git", "-C", str(co), "fetch", "--quiet", "--depth=1", "origin", commit], check=True)
    subprocess.run(["git", "-C", str(co), "checkout", "--quiet", "--detach", commit], check=True)
    subprocess.run(["git", "-C", str(co), "sparse-checkout", "set", "--no-cone", *("/" + p for p in paths)], check=True)
    return co


def restore_group(label: str, repo: str, commit: str, items: list[list[str] | tuple[str, str, str]]) -> None:
    missing = [(src, dst, want) for src, dst, want in items if not ok(dst, want)]
    if not missing:
        print(f"PIN OK  {label} ({len(items)} files)")
        return
    with tempfile.TemporaryDirectory(dir=DATA) as tmp:
        co = sparse_fetch(repo, commit, [src for src, _, _ in missing], Path(tmp))
        for src, dst, want in missing:
            target = ROOT / dst
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(co / src, target)
            got = sha256(target)
            if got != want:
                target.unlink(missing_ok=True)
                sys.exit(f"SHA256 MISMATCH for {dst}: got {got}, want {want}")
    print(f"RESTORED {label} ({len(missing)} / {len(items)} files)")


def restore_features() -> None:
    if ok("data/training_features.tif", FEATURE_SHA256):
        print("PIN OK  features (data/training_features.tif)")
        return
    target = ROOT / "data/training_features.tif"
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=DATA) as tmp:
        co = sparse_fetch(FEATURE_REPO, FEATURE_COMMIT, FEATURE_PARTS, Path(tmp))
        with target.open("wb") as out:
            for part in FEATURE_PARTS:
                with (co / part).open("rb") as inp:
                    shutil.copyfileobj(inp, out, 1 << 20)
    got = sha256(target)
    if got != FEATURE_SHA256:
        target.unlink(missing_ok=True)
        sys.exit(f"SHA256 MISMATCH for training_features.tif: {got}")
    print("RESTORED features (data/training_features.tif)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--validation", action="store_true",
                    help="Restore grid + all 18 multi-repo registry rasters without 419 MB feature stack")
    args = ap.parse_args()
    DATA.mkdir(exist_ok=True)
    for label, repo, commit, items in VALIDATION_GROUPS:
        restore_group(label, repo, commit, items)
    cache_data = ROOT / ".cache" / "data"
    cache_data.mkdir(parents=True, exist_ok=True)
    for fname in ("sample_submission.tif", "existing_faults.tif"):
        src = ROOT / "data" / "bridge" / fname
        dst = cache_data / fname
        if src.is_file() and (not dst.is_file() or sha256(dst) != sha256(src)):
            shutil.copy2(src, dst)
    if not args.validation:
        restore_features()
        label, repo, commit, items = EXTERNAL_GROUP
        restore_group(label, repo, commit, items)


if __name__ == "__main__":
    main()
