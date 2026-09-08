#!/usr/bin/env bash
# Builds one offline country as a data-only CC.abm container (vector map data + routing/search data) and a maximum-compression CC.abm.zip distribution copy.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CODE="${1:?Usage: build_country_abm.sh CC <pbf-url-or-path> <output-directory> [bbox]}"
PBF_SOURCE="${2:?Usage: build_country_abm.sh CC <pbf-url-or-path> <output-directory> [bbox]}"
OUT_DIR="${3:?Usage: build_country_abm.sh CC <pbf-url-or-path> <output-directory> [bbox]}"
BBOX="${4:-}"
if [[ "$BBOX" == --bbox=* ]]; then BBOX="${BBOX#--bbox=}"; fi
CODE="${CODE^^}"
mkdir -p "$OUT_DIR"; OUT_DIR="$(cd "$OUT_DIR" && pwd)"; WORK_DIR="$OUT_DIR/work-$CODE"; ARCHIVE="$OUT_DIR/$CODE.abm"; ZIP_ARCHIVE="$OUT_DIR/$CODE.abm.zip"
command -v docker >/dev/null || { echo "Docker is required for Planetiler." >&2; exit 2; }
command -v pmtiles >/dev/null || { echo "pmtiles CLI is required." >&2; exit 2; }
rm -rf "$WORK_DIR"; mkdir -p "$WORK_DIR"; trap 'rm -rf "$WORK_DIR"' EXIT

download_with_retry(){ local url="$1" dest="$2" max_attempts=8 attempt=1 wait=10; while ((attempt<=max_attempts)); do if curl --fail --location --connect-timeout 30 --retry 3 --retry-all-errors "$url" -o "$dest"; then return 0; fi; echo "Download attempt $attempt/$max_attempts failed; retrying in ${wait}s..." >&2; sleep "$wait"; attempt=$((attempt+1)); wait=$((wait*2>120?120:wait*2)); done; return 1; }
if [[ "$PBF_SOURCE" =~ ^https?:// ]]; then
 download_with_retry "$PBF_SOURCE" "$WORK_DIR/input.osm.pbf"
 if download_with_retry "$PBF_SOURCE.md5" "$WORK_DIR/input.osm.pbf.md5"; then expected_md5="$(awk '{print $1;exit}' "$WORK_DIR/input.osm.pbf.md5")"; (cd "$WORK_DIR" && echo "$expected_md5  input.osm.pbf" | md5sum -c -); else echo "Warning: PBF MD5 unavailable; continuing." >&2; fi
else test -f "$PBF_SOURCE"; cp "$PBF_SOURCE" "$WORK_DIR/input.osm.pbf"; fi
if [[ -n "$BBOX" ]]; then command -v osmium >/dev/null || { echo "osmium is required for bbox builds." >&2; exit 2; }; osmium extract --bbox="$BBOX" --strategy complete_ways -o "$WORK_DIR/input-clipped.osm.pbf" "$WORK_DIR/input.osm.pbf"; mv "$WORK_DIR/input-clipped.osm.pbf" "$WORK_DIR/input.osm.pbf"; fi

docker run --rm --user "$(id -u):$(id -g)" -v "$WORK_DIR:/data" ghcr.io/onthegomap/planetiler:0.10.2 generate-custom --schema=/data/abtin_basemap.yml --osm_path=/data/input.osm.pbf --output=/data/vector.pmtiles --force
CLUSTER_LOG="$WORK_DIR/pmtiles-cluster.log"; if ! pmtiles cluster "$WORK_DIR/vector.pmtiles" >"$CLUSTER_LOG" 2>&1; then grep -q 'already clustered' "$CLUSTER_LOG" || { cat "$CLUSTER_LOG" >&2; exit 1; }; fi; cat "$CLUSTER_LOG"; pmtiles verify "$WORK_DIR/vector.pmtiles"
python3 -c 'import osmium,zstandard,brotli' 2>/dev/null || { echo "Missing Python dependencies." >&2; exit 2; }
python3 "$ROOT/tool/maps/build_abm_graph.py" --pbf "$WORK_DIR/input.osm.pbf" --output "$WORK_DIR/graph.abm" --region "$CODE"
python3 "$ROOT/tool/maps/verify_abm_graph.py" "$WORK_DIR/graph.abm"
python3 "$ROOT/tool/maps/build_search_index.py" --pbf "$WORK_DIR/input.osm.pbf" --output "$WORK_DIR/search.sqlite"
python3 "$ROOT/tool/maps/pack_abm_container.py" --region "$CODE" --pmtiles "$WORK_DIR/vector.pmtiles" --graph "$WORK_DIR/graph.abm" --search-index "$WORK_DIR/search.sqlite" --output "$ARCHIVE"
python3 "$ROOT/tool/maps/verify_abm_container.py" "$ARCHIVE" --region "$CODE"
# Keep the canonical .abm untouched for direct/offline use. Also create a
# deterministic maximum-compression ZIP distribution copy. ZIP is applied
# only after ABM verification so compression can never hide a corrupt map.
python3 "$ROOT/tool/maps/zip_abm.py" --input "$ARCHIVE" --output "$ZIP_ARCHIVE"
printf 'Built single country archive: %s\n' "$ARCHIVE"
printf 'Built compressed distribution: %s\n' "$ZIP_ARCHIVE"
sha256sum "$ARCHIVE" "$ZIP_ARCHIVE"
