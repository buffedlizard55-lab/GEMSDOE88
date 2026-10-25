#!/usr/bin/env bash
# Deterministically download and verify competition data for GEMSDOE88.
#
# Supported operational modes:
# 1. Unrestricted machine: downloads official competition files via official Dropbox/DOE GDR links.
# 2. Network-restricted sandbox (allowlisted GitHub): restores pinned files via python3 scripts/restore_inputs.py.
#
# Verified SHA-256 targets:
# - sample_submission.tif: 2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc
# - existing_faults.tif:   7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093
# - training_features.tif: 4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATA_DIR="${ROOT_DIR}/data"

mkdir -p "${DATA_DIR}" "${DATA_DIR}/bridge" "${DATA_DIR}/official"

echo "=== GEMSDOE88: Downloading Competition Data ==="
echo "Target directory: ${DATA_DIR}"

# Check if data already exists and is valid
if [ -f "${DATA_DIR}/training_features.tif" ] && [ -f "${DATA_DIR}/bridge/sample_submission.tif" ] && [ -f "${DATA_DIR}/bridge/existing_faults.tif" ]; then
    echo "Core competition data files already present on disk."
    python3 "${SCRIPT_DIR}/prepare_data.py"
    exit 0
fi

# Attempt GitHub-pinned deterministic restore first (works on network-restricted sandbox)
echo "Attempting deterministic restore via scripts/restore_inputs.py..."
if python3 "${SCRIPT_DIR}/restore_inputs.py" && python3 "${SCRIPT_DIR}/restore_siblings.py"; then
    echo "Deterministic restore succeeded."
    python3 "${SCRIPT_DIR}/prepare_data.py"
    exit 0
fi

echo "Fallback: Downloading via direct official links..."
# Official Dropbox links provided in competition instructions:
# sample_submission.tif / example_submission.tif
curl -fL "https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=1" \
    -o "${DATA_DIR}/sample_submission.tif" || true

# existing_faults.tif
curl -fL "https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=1" \
    -o "${DATA_DIR}/existing_faults.tif" || true

# training_features.tif (gems-geodawn-numerical-features.tif)
curl -fL "https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=1" \
    -o "${DATA_DIR}/training_features.tif" || true

python3 "${SCRIPT_DIR}/prepare_data.py"
