#!/usr/bin/env bash
# Builds one offline country as a single CC.abm container.
# Prerequisites: Docker, Python 3, pip packages osmium/zstandard, pmtiles CLI.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CODE="${1:?Usage: build_country_abm.sh CC <pbf-url-or-path> <output-directory>}"
PBF_SOURCE="${2:?Usage: build_country_abm.sh CC <pbf-url-or-path> <output-directory>}"
OUT_DIR="${3:?Usage: build_country_abm.sh CC <pbf-url-or-path> <output-directory>}"
CODE="${CODE^^}"
mkdir -p "$OUT_DIR"
OUT_DIR="$(cd "$OUT_DIR" && pwd)"
WORK_DIR="${OUT_DIR}/work-${CODE}"
ARCHIVE="${OUT_DIR}/${CODE}.abm"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required for Planetiler." >&2
  exit 2
fi
if ! command -v pmtiles >/dev/null 2>&1; then
  echo "pmtiles CLI is required. Install it from https://github.com/protomaps/go-pmtiles/releases" >&2
  exit 2
fi

rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
trap 'rm -rf "$WORK_DIR"' EXIT

if [[ "$PBF_SOURCE" =~ ^https?:// ]]; then
  curl --fail --location --retry 3 --connect-timeout 30 "$PBF_SOURCE" -o "$WORK_DIR/input.osm.pbf"
else
  test -f "$PBF_SOURCE"
  cp "$PBF_SOURCE" "$WORK_DIR/input.osm.pbf"
fi

cp "$ROOT/tool/maps/abtin_basemap.yml" "$WORK_DIR/abtin_basemap.yml"
cp "$ROOT/tool/maps/styles/day.json" "$WORK_DIR/day.json"
cp "$ROOT/tool/maps/styles/night.json" "$WORK_DIR/night.json"

# Planetiler creates standard MVT PMTiles. No POI layer is present in the
# schema; user-selectable local POIs remain the ABM application's responsibility.
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$WORK_DIR:/data" \
  ghcr.io/onthegomap/planetiler:0.10.2 \
  generate-custom \
  --schema=/data/abtin_basemap.yml \
  --osm_path=/data/input.osm.pbf \
  --output=/data/vector.pmtiles \
  --force

# Planetiler may leave the valid archive unclustered. Canonicalize it in place
# before embedding the routing graph, then verify the standard PMTiles layout.
CLUSTER_LOG="$WORK_DIR/pmtiles-cluster.log"
if ! pmtiles cluster "$WORK_DIR/vector.pmtiles" >"$CLUSTER_LOG" 2>&1; then
  if ! grep -q 'already clustered' "$CLUSTER_LOG"; then
    cat "$CLUSTER_LOG" >&2
    exit 1
  fi
fi
cat "$CLUSTER_LOG"
pmtiles verify "$WORK_DIR/vector.pmtiles"
python3 -m pip install --disable-pip-version-check --user osmium zstandard brotli
python3 "$ROOT/tool/maps/build_abm_graph.py" \
  --pbf "$WORK_DIR/input.osm.pbf" \
  --output "$WORK_DIR/graph.abm" \
  --region "$CODE"
python3 "$ROOT/tool/maps/verify_abm_graph.py" "$WORK_DIR/graph.abm"
python3 "$ROOT/tool/maps/pack_abm_container.py" \
  --region "$CODE" \
  --pmtiles "$WORK_DIR/vector.pmtiles" \
  --graph "$WORK_DIR/graph.abm" \
  --day-style "$WORK_DIR/day.json" \
  --night-style "$WORK_DIR/night.json" \
  --output "$ARCHIVE"

# This verifies that the PMTiles reader accepts the final one-file container,
# not only the temporary .pmtiles payload.
pmtiles verify "$ARCHIVE"
python3 "$ROOT/tool/maps/verify_abm_container.py" "$ARCHIVE" --region "$CODE"
printf 'Built single country archive: %s\n' "$ARCHIVE"
sha256sum "$ARCHIVE"
