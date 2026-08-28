#!/usr/bin/env python3
"""Build all Geofabrik countries/regions and always emit a final manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

INDEX_URL = "https://download.geofabrik.de/index-v1.json"
# Geofabrik publishes the United States as one very large PBF. These four
# overlapping boxes keep the source country complete while making output units
# independently buildable. Other large countries use Geofabrik child regions.
US_PARTS = [
    ("US-WEST", "West", "-125,24,-104,50"),
    ("US-CENTRAL", "Central", "-110,24,-88,50"),
    ("US-EAST", "East", "-94,24,-66,50"),
    ("US-ALASKA", "Alaska", "-171,50,-129,72"),
    ("US-HAWAII", "Hawaii", "-161,18,-154,23"),
]

def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))

def bounds(geometry: dict) -> str:
    points = []
    def walk(value):
        if isinstance(value, list):
            if len(value) >= 2 and all(isinstance(v, (int, float)) for v in value[:2]):
                points.append((float(value[0]), float(value[1])))
            else:
                for item in value: walk(item)
    walk(geometry.get("coordinates", []))
    if not points:
        raise ValueError("feature has no geometry coordinates")
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return f"{min(xs):.6f},{min(ys):.6f},{max(xs):.6f},{max(ys):.6f}"

def discover_entries(index: dict) -> list[dict]:
    features = [x for x in index.get("features", []) if isinstance(x, dict)]
    props = [x.get("properties", {}) for x in features]
    countries = [x for x in features if x.get("properties", {}).get("iso3166-1:alpha2")]
    by_parent = {}
    for x in features:
        parent = x.get("properties", {}).get("parent")
        if parent: by_parent.setdefault(parent, []).append(x)
    entries = []
    for feature in countries:
        p = feature["properties"]
        code = str(p["iso3166-1:alpha2"][0]).upper()
        country_id = str(p.get("id", ""))
        children = [x for x in by_parent.get(country_id, [])
                    if x.get("properties", {}).get("urls", {}).get("pbf")]
        # Child regions are used for countries where Geofabrik exposes a real
        # regional split. The top-level country archive is not duplicated.
        if code != "US" and len(children) >= 3:
            for child in children:
                cp = child["properties"]
                try: child_bbox = bounds(child.get("geometry", {}))
                except ValueError: continue
                entries.append({
                    "code": f"{code}-{str(cp.get('id', 'part')).upper()}",
                    "name_fa": f"{p.get('name', code)} - {cp.get('name', 'بخش')}",
                    "name_en": f"{p.get('name', code)} - {cp.get('name', 'region')}",
                    "country_code": code,
                    "country_name_fa": p.get('name', code),
                    "country_name_en": p.get('name', code),
                    "region_name_fa": cp.get('name', 'بخش'),
                    "region_name_en": cp.get('name', 'region'),
                    "group_order": len(entries),
                    "bbox": child_bbox,
                    "pbf_url": cp["urls"]["pbf"],
                })
            continue
        if code == "US":
            pbf = p.get("urls", {}).get("pbf")
            for part_code, part_name, part_bbox in US_PARTS:
                entries.append({
                    "code": part_code,
                    "name_fa": f"{p.get('name', 'United States')} - {part_name}",
                    "name_en": f"{p.get('name', 'United States')} - {part_name}",
                    "country_code": "US",
                    "country_name_fa": "United States of America",
                    "country_name_en": "United States of America",
                    "region_name_fa": part_name,
                    "region_name_en": part_name,
                    "group_order": len(entries),
                    "bbox": part_bbox,
                    "pbf_url": pbf,
                })
            continue
        try: country_bbox = bounds(feature.get("geometry", {}))
        except ValueError: continue
        entries.append({
            "code": code,
            "name_fa": p.get("name", code),
            "name_en": p.get("name", code),
            "country_code": code,
            "country_name_fa": p.get("name", code),
            "country_name_en": p.get("name", code),
            "region_name_fa": "",
            "region_name_en": "",
            "group_order": 0,
            "bbox": country_bbox,
            "pbf_url": p.get("urls", {}).get("pbf"),
        })
    return [e for e in entries if e["pbf_url"]]

def empty_manifest(path: Path, tag: str) -> None:
    path.write_text(json.dumps({
        "schema_version": 4, "release_tag": tag,
        "generated_at": datetime.now(UTC).isoformat(), "countries": []
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--index-url", default=INDEX_URL)
    parser.add_argument("--countries-file", type=Path)
    parser.add_argument("--chunk-index", type=int, default=0)
    parser.add_argument("--chunk-count", type=int, default=1)
    parser.add_argument("--existing-assets", type=Path)
    args = parser.parse_args()
    if args.chunk_count < 1 or not 0 <= args.chunk_index < args.chunk_count:
        raise SystemExit("chunk-index must be within chunk-count")
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = args.output / "manifest.json"
    if args.previous and args.previous.is_file(): shutil.copy2(args.previous, manifest)
    else: empty_manifest(manifest, args.release_tag)
    existing_assets = set()
    if args.existing_assets and args.existing_assets.is_file():
        existing_assets = {line.strip() for line in args.existing_assets.read_text(encoding='utf-8').splitlines() if line.strip()}
    try:
        previous_data = json.loads(manifest.read_text(encoding='utf-8'))
        previous_entries = {
            str(item.get('code', '')).upper(): item
            for item in previous_data.get('countries', [])
            if isinstance(item, dict)
        }
    except Exception:
        previous_entries = {}
    try:
        entries = json.loads(args.countries_file.read_text(encoding="utf-8")) if args.countries_file else discover_entries(fetch_json(args.index_url))
    except Exception as exc:
        report = {"generated_at": datetime.now(UTC).isoformat(), "successes": [], "failures": [{"stage": "discover", "error": str(exc)}]}
        (args.output / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0
    if isinstance(entries, dict): entries = entries.get("countries", entries.get("regions", []))
    entries = [entry for index, entry in enumerate(entries)
               if index % args.chunk_count == args.chunk_index]
    successes, failures = [], []
    updater = args.root / "tool/maps/update_map_manifest.py"
    builder = args.root / "tool/maps/build_country_abm.sh"
    with tempfile.TemporaryDirectory(prefix="abtin-map-build-") as temp:
        for number, entry in enumerate(entries, 1):
            code = str(entry.get("code", "")).upper()
            try:
                if not code or not entry.get("pbf_url"):
                    raise ValueError("missing code or pbf_url")
                archive = args.output / f"{code}.abm"
                previous = previous_entries.get(code, {})
                if (previous.get('sha256') and archive.name in existing_assets):
                    print(f"SKIP {code}: existing Release asset is retained")
                    successes.append({"code": code, "archive": archive.name, "skipped": True})
                    continue
                subprocess.run(["bash", str(builder), code, str(entry["pbf_url"]), str(args.output), *( [str(entry["bbox"])] if entry.get("bbox") else [])], check=True)
                if not archive.is_file(): raise RuntimeError("builder returned without archive")
                next_manifest = Path(temp) / "manifest.json"
                subprocess.run([
                    sys.executable, str(updater),
                    "--output", str(next_manifest),
                    "--previous", str(manifest),
                    "--release-tag", args.release_tag,
                    "--archive", str(archive),
                    "--code", code,
                    "--name-fa", str(entry.get("name_fa", code)),
                    "--name-en", str(entry.get("name_en", code)),
                    "--country-code", str(entry.get("country_code", code[:2])),
                    "--country-name-fa", str(entry.get("country_name_fa", entry.get("name_fa", code))),
                    "--country-name-en", str(entry.get("country_name_en", entry.get("name_en", code))),
                    "--region-name-fa", str(entry.get("region_name_fa", entry.get("name_fa", code))),
                    "--region-name-en", str(entry.get("region_name_en", entry.get("name_en", code))),
                    "--group-order", str(entry.get("group_order", 0)),
                    "--bbox", str(entry.get("bbox", "-180,-90,180,90")),
                    "--source-url", str(entry["pbf_url"]),
                ], check=True)
                shutil.copy2(next_manifest, manifest)
                successes.append({"code": code, "archive": archive.name})
            except Exception as exc:
                failures.append({"code": code or f"entry-{number}", "error": str(exc)})
                print(f"SKIP {code or number}: {exc}", file=sys.stderr)
    report = {"generated_at": datetime.now(UTC).isoformat(), "release_tag": args.release_tag, "success_count": len(successes), "failure_count": len(failures), "successes": successes, "failures": failures}
    (args.output / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Completed all entries: success={len(successes)} failure={len(failures)} manifest={manifest}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
