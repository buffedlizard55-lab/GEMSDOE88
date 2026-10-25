#!/usr/bin/env bash
# Restore SHA-pinned OWNER MIRRORS. This is NOT an authenticated organizer download.
# Default: core 19-band features + shared external inputs, then prepare_data.py.
# --validation: only the grid/catalogue/core registry needed by the release audit.
# --registry: additionally restore the pinned sibling inventory (not a new model).
# The user-provided Dropbox URLs are not automatically labelled official sources
# or used as an unverified fallback. A failed pinned restore exits nonzero.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON="${PYTHON:-python3}"
if [[ -x "${ROOT_DIR}/.venv/bin/python" && "${PYTHON}" == "python3" ]]; then
    PYTHON="${ROOT_DIR}/.venv/bin/python"
fi
if (( $# > 1 )); then
    echo "Usage: bash scripts/download_competition_data.sh [--validation|--registry]" >&2
    exit 1
fi
MODE="${1:-}"
case "${MODE}" in
    --validation)
        "${PYTHON}" "${SCRIPT_DIR}/restore_inputs.py" --validation
        ;;
    ""|--registry)
        "${PYTHON}" "${SCRIPT_DIR}/restore_inputs.py"
        if [[ "${MODE}" == "--registry" ]]; then
            "${PYTHON}" "${SCRIPT_DIR}/restore_siblings.py"
        fi
        "${PYTHON}" "${SCRIPT_DIR}/prepare_data.py"
        ;;
    *)
        echo "Usage: bash scripts/download_competition_data.sh [--validation|--registry]" >&2
        exit 1
        ;;
esac
echo "Owner-mirror bytes verified locally. Organizer provenance, generation gates and slot approval are separate."
