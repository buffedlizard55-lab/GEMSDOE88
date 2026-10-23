#!/usr/bin/env bash
# Optional fetcher for Hypothesis H88-H5 external public datasets outside the Arena 6-host sandbox allowlist.
# All URLs are official, open-access US public datasets (Public Domain 17 U.S.C. § 105 / CC BY 4.0).
set -euo pipefail

DEST="${1:-.cache/external}"
mkdir -p "${DEST}"

echo "[1/3] Fetching USGS ANSS ComCat earthquake hypocenters (Public Domain 17 U.S.C. § 105)..."
curl -fsSL \
  "https://earthquake.usgs.gov/fdsnws/event/1/query?format=text&minlatitude=37.45&maxlatitude=40.75&minlongitude=-120.0&maxlongitude=-116.2&minmagnitude=3.0&starttime=2015-01-01&endtime=2026-10-21" \
  -o "${DEST}/usgs_comcat_2015_2026_m30.txt"

echo "[2/3] Querying NASA ASF OPERA/ARIA Sentinel-1 Surface Displacement catalog metadata (Public Domain)..."
curl -fsSL \
  "https://api.daac.asf.alaska.edu/services/search/param?dataset=OPERA-S1&bbox=-120.0,37.45,-116.2,40.75&output=json&maxResults=250" \
  -o "${DEST}/asf_opera_s1_catalog.json"

echo "[3/3] Fetching UNR Nevada Geodetic Laboratory MIDAS horizontal/vertical GPS velocity summary (CC BY 4.0)..."
curl -fsSL \
  "http://geodesy.unr.edu/velocities/midas.IGS14.txt" \
  -o "${DEST}/unr_ngl_midas_igs14.txt"

echo "Done. Optional Phase-2 layers saved to ${DEST}/"
