#!/usr/bin/env bash
# Weekly updater for one country. Reuses a previously downloaded Geofabrik PBF
# when possible and asks pyosmium-up-to-date to apply OSM replication diffs.
# Planetiler itself performs a full import of the updated PBF; only countries
# whose upstream revision changed are rebuilt by build_all_maps.py. The mobile
# app receives a chunk delta when it is smaller than the full ABM.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CODE="${1:?Usage: weekly_update.sh CC <pbf-url> <cache-dir> <output-dir> [bbox]}"
PBF_URL="${2:?Usage: weekly_update.sh CC <pbf-url> <cache-dir> <output-dir> [bbox]}"
CACHE="${3:?Usage: weekly_update.sh CC <pbf-url> <cache-dir> <output-dir> [bbox]}"
OUT="${4:?Usage: weekly_update.sh CC <pbf-url> <cache-dir> <output-dir> [bbox]}"
BBOX="${5:-}"
mkdir -p "$CACHE" "$OUT"
PBF="$CACHE/${CODE^^}.osm.pbf"
if [[ -s "$PBF" ]]; then
  python3 -m pip install --disable-pip-version-check --user pyosmium >/dev/null
  if ! pyosmium-up-to-date --size 20000 -v "$PBF"; then
    echo "Incremental OSM replication update failed; refreshing the extract once." >&2
    rm -f "$PBF"
  fi
fi
if [[ ! -s "$PBF" ]]; then
  curl --fail --location --retry 8 --retry-all-errors --retry-delay 10 "$PBF_URL" -o "$PBF"
fi
args=("$CODE" "$PBF" "$OUT")
[[ -n "$BBOX" ]] && args+=("$BBOX")
exec bash "$ROOT/tool/maps/build_country_abm.sh" "${args[@]}"
