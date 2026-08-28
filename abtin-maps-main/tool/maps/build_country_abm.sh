#!/usr/bin/env bash
# Builds one offline country as a single CC.abm container.
# Prerequisites: Docker, Python 3, pip packages osmium/zstandard, pmtiles CLI.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CODE="${1:?Usage: build_country_abm.sh CC <pbf-url-or-path> <output-directory> [bbox]}"
PBF_SOURCE="${2:?Usage: build_country_abm.sh CC <pbf-url-or-path> <output-directory> [bbox]}"
OUT_DIR="${3:?Usage: build_country_abm.sh CC <pbf-url-or-path> <output-directory> [bbox]}"
BBOX="${4:-}"
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

# Geofabrik occasionally returns 502/503 for tens of seconds to a few minutes
# during overload; curl's built-in --retry (3 attempts, short backoff) is not
# enough to ride that out, so we wrap it in our own retry loop with longer,
# increasing waits before giving up.
download_with_retry() {
  local url="$1" dest="$2" max_attempts=8 attempt=1 wait=10
  while (( attempt <= max_attempts )); do
    if curl --fail --location --connect-timeout 30 --retry 3 --retry-all-errors \
         "$url" -o "$dest"; then
      return 0
    fi
    echo "Download attempt ${attempt}/${max_attempts} failed for $url; retrying in ${wait}s..." >&2
    sleep "$wait"
    attempt=$((attempt + 1))
    wait=$(( wait * 2 > 120 ? 120 : wait * 2 ))
  done
  echo "Giving up after ${max_attempts} attempts: $url" >&2
  return 1
}

if [[ "$PBF_SOURCE" =~ ^https?:// ]]; then
  download_with_retry "$PBF_SOURCE" "$WORK_DIR/input.osm.pbf"
else
  test -f "$PBF_SOURCE"
  cp "$PBF_SOURCE" "$WORK_DIR/input.osm.pbf"
fi

# A bbox is used for large-country regional builds. The source PBF can be a
# full-country download, while Planetiler and graph generation receive only
# this region. Without a bbox the original whole-country behavior is kept.
if [[ -n "$BBOX" ]]; then
  command -v osmium >/dev/null 2>&1 || {
    echo "osmium is required when a regional bbox is supplied." >&2
    exit 2
  }
  osmium extract --bbox "$BBOX" --strategy complete_ways \
    -o "$WORK_DIR/input-clipped.osm.pbf" "$WORK_DIR/input.osm.pbf"
  mv "$WORK_DIR/input-clipped.osm.pbf" "$WORK_DIR/input.osm.pbf"
fi

cp "$ROOT/tool/maps/abtin_basemap.yml" "$WORK_DIR/abtin_basemap.yml"
cp "$ROOT/tool/maps/styles/day.json" "$WORK_DIR/day.json"
cp "$ROOT/tool/maps/styles/night.json" "$WORK_DIR/night.json"

# Label glyphs and the POI sprite are embedded in the same .abm container.
# MapLibre extracts only these small resources into its local cache; it never
# downloads a second map, sprite, or font at runtime.
mkdir -p "$WORK_DIR/resources/glyphs/Vazirmatn" "$WORK_DIR/resources/sprites"
GLYPH_DIR="$WORK_DIR/resources/glyphs/Vazirmatn"
GLYPH_RANGES=(
  0-255 256-511 1536-1791 1792-2047 8192-8447
  64256-64511 64512-64767 65024-65279 65280-65535
)
LOCAL_GLYPH_DIR="$ROOT/assets/glyphs/Vazirmatn"
# The builder repository may omit app-only assets or contain only part of the
# ranges. Fill each missing range from the public openmaptiles archive instead
# of relying on a wildcard copy that fails when the directory is absent.
GLYPH_BASE_URL='https://raw.githubusercontent.com/openmaptiles/fonts/gh-pages/Klokantech%20Noto%20Sans%20Regular'
for range in "${GLYPH_RANGES[@]}"; do
  if [[ -s "$LOCAL_GLYPH_DIR/${range}.pbf" ]]; then
    cp "$LOCAL_GLYPH_DIR/${range}.pbf" "$GLYPH_DIR/${range}.pbf"
  else
    download_with_retry "$GLYPH_BASE_URL/${range}.pbf" "$GLYPH_DIR/${range}.pbf"
  fi
done
SPRITE_DIR="$ROOT/assets/sprites"
for sprite in abtin.json abtin.png abtin@2x.json abtin@2x.png; do
  test -f "$SPRITE_DIR/$sprite" || {
    echo "Missing required POI sprite: $SPRITE_DIR/$sprite" >&2
    exit 2
  }
  cp "$SPRITE_DIR/$sprite" "$WORK_DIR/resources/sprites/"
done
resource_args=()
for glyph in "$WORK_DIR"/resources/glyphs/Vazirmatn/*.pbf; do
  resource_args+=(--resource "glyphs/Vazirmatn/$(basename "$glyph")=$glyph")
done
for sprite in "$WORK_DIR"/resources/sprites/*; do
  resource_args+=(--resource "sprites/$(basename "$sprite")=$sprite")
done

# Planetiler creates standard MVT PMTiles with roads, labels, and POIs.
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
  "${resource_args[@]}" \
  --output "$ARCHIVE"

# This verifies that the PMTiles reader accepts the final one-file container,
# not only the temporary .pmtiles payload.
pmtiles verify "$ARCHIVE"
python3 "$ROOT/tool/maps/verify_abm_container.py" "$ARCHIVE" --region "$CODE"
printf 'Built single country archive: %s\n' "$ARCHIVE"
sha256sum "$ARCHIVE"
