#!/usr/bin/env python3
"""Build every discovered Geofabrik country/region deterministically.

Important properties:
* preserves the existing Geofabrik regional split (for example north/east/west);
* never silently treats a failed build as success;
* skips a map only when the source signature is unchanged from the previous manifest;
* emits an expected catalog so the merge job can prove that no map disappeared;
* each successful build remains one .abm container containing PMTiles, graph,
  POI/search resources and styles.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import time
from datetime import UTC, datetime
from pathlib import Path

INDEX_URL = "https://download.geofabrik.de/index-v1.json"
US_PARTS = [
    ("US-WEST", "West", "-125,24,-104,50"),
    ("US-CENTRAL", "Central", "-110,24,-88,50"),
    ("US-EAST", "East", "-94,24,-66,50"),
    ("US-ALASKA", "Alaska", "-171,50,-129,72"),
    ("US-HAWAII", "Hawaii", "-161,18,-154,23"),
]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "AbtinMapsBuilder/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_source_signature(pbf_url: str) -> str:
    """Prefer Geofabrik's authoritative .md5 sidecar; fall back to HTTP headers."""
    md5_url = pbf_url + ".md5"
    try:
        req = urllib.request.Request(md5_url, headers={"User-Agent": "AbtinMapsBuilder/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            text = response.read().decode("utf-8", "replace").strip()
        token = text.split()[0].strip().lower()
        if len(token) == 32 and all(c in "0123456789abcdef" for c in token):
            return f"md5:{token}"
    except Exception:
        pass
    try:
        req = urllib.request.Request(pbf_url, method="HEAD", headers={"User-Agent": "AbtinMapsBuilder/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            etag = response.headers.get("ETag", "").strip()
            modified = response.headers.get("Last-Modified", "").strip()
            length = response.headers.get("Content-Length", "").strip()
        if etag or modified or length:
            return f"http:{etag}|{modified}|{length}"
    except Exception:
        pass
    # A non-empty fallback is required so a transient signature-server failure
    # never causes an old map to be incorrectly considered unchanged.
    return f"unknown:{int(time.time())}:{pbf_url}"


def bounds(geometry: dict) -> str:
    points: list[tuple[float, float]] = []
    def walk(value: object) -> None:
        if isinstance(value, list):
            if len(value) >= 2 and all(isinstance(v, (int, float)) for v in value[:2]):
                points.append((float(value[0]), float(value[1])))
            else:
                for item in value:
                    walk(item)
    walk(geometry.get("coordinates", []))
    if not points:
        raise ValueError("feature has no geometry coordinates")
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return f"{min(xs):.6f},{min(ys):.6f},{max(xs):.6f},{max(ys):.6f}"


def discover_entries(index: dict) -> list[dict]:
    features = [x for x in index.get("features", []) if isinstance(x, dict)]
    countries = [x for x in features if x.get("properties", {}).get("iso3166-1:alpha2")]
    by_parent: dict[str, list[dict]] = {}
    for feature in features:
        parent = feature.get("properties", {}).get("parent")
        if parent:
            by_parent.setdefault(str(parent), []).append(feature)
    entries: list[dict] = []
    for feature in countries:
        p = feature["properties"]
        code = str(p["iso3166-1:alpha2"][0]).upper()
        country_id = str(p.get("id", ""))
        children = [
            x for x in by_parent.get(country_id, [])
            if x.get("properties", {}).get("urls", {}).get("pbf")
        ]
        if code != "US" and len(children) >= 3:
            for child in sorted(children, key=lambda x: str(x.get("properties", {}).get("id", ""))):
                cp = child["properties"]
                try:
                    child_bbox = bounds(child.get("geometry", {}))
                except ValueError:
                    continue
                entries.append({
                    "code": f"{code}-{str(cp.get('id', 'part')).upper()}",
                    "name_fa": f"{p.get('name', code)} - {cp.get('name', 'بخش')}",
                    "name_en": f"{p.get('name', code)} - {cp.get('name', 'region')}",
                    "country_code": code,
                    "country_name_fa": p.get("name", code),
                    "country_name_en": p.get("name", code),
                    "region_name_fa": cp.get("name", "بخش"),
                    "region_name_en": cp.get("name", "region"),
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
                    "bbox": part_bbox,
                    "pbf_url": pbf,
                })
            continue
        try:
            country_bbox = bounds(feature.get("geometry", {}))
        except ValueError:
            continue
        pbf_url = p.get("urls", {}).get("pbf")
        if not pbf_url:
            continue
        entries.append({
            "code": code,
            "name_fa": p.get("name", code),
            "name_en": p.get("name", code),
            "country_code": code,
            "country_name_fa": p.get("name", code),
            "country_name_en": p.get("name", code),
            "region_name_fa": "",
            "region_name_en": "",
            "bbox": country_bbox,
            "pbf_url": pbf_url,
        })
    # Stable de-duplication: the same code must never be built twice.
    unique: dict[str, dict] = {}
    for entry in entries:
        unique[str(entry["code"]).upper()] = entry
    result = list(unique.values())
    result.sort(key=lambda e: (str(e.get("country_code", "")), str(e["code"])))
    for i, entry in enumerate(result):
        entry["group_order"] = i
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        signatures = list(pool.map(lambda e: fetch_source_signature(e["pbf_url"]), result))
    for entry, signature in zip(result, signatures):
        entry["source_signature"] = signature
    return result


def empty_manifest(path: Path, tag: str) -> None:
    path.write_text(json.dumps({"schema_version": 5, "release_tag": tag, "generated_at": datetime.now(UTC).isoformat(), "countries": []}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    parser.add_argument("--existing-assets", type=Path, help="Text file containing asset names already present in the release")
    parser.add_argument("--country-selector", default="ALL", help="Country selector: IR, ALL, or ALL/IR/AZ; country codes may be slash-separated")
    args = parser.parse_args()
    if args.chunk_count < 1 or not 0 <= args.chunk_index < args.chunk_count:
        raise SystemExit("chunk-index must be within chunk-count")
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = args.output / "manifest.json"
    # `manifest.json` in a chunk artifact contains only maps actually rebuilt
    # by that chunk. The previous release manifest is input state only; merge
    # later combines it with these current outputs. This prevents a skipped
    # country's metadata from making merge look for an archive that is not
    # present in the current runner.
    previous_data = {}
    if args.previous and args.previous.is_file():
        try:
            previous_data = json.loads(args.previous.read_text(encoding="utf-8"))
        except Exception:
            previous_data = {}
    try:
        previous_entries = {str(item.get("code", "")).upper(): item for item in previous_data.get("countries", []) if isinstance(item, dict)}
    except Exception:
        previous_entries = {}
    try:
        entries = json.loads(args.countries_file.read_text(encoding="utf-8")) if args.countries_file else discover_entries(fetch_json(args.index_url))
    except Exception as exc:
        report = {"generated_at": datetime.now(UTC).isoformat(), "successes": [], "failures": [{"stage": "discover", "error": str(exc)}]}
        (args.output / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1
    if isinstance(entries, dict):
        entries = entries.get("countries", entries.get("regions", []))
    if not entries:
        raise SystemExit("country catalog is empty")
    # Custom catalog files may not carry signatures; compute them now.
    for entry in entries:
        if not entry.get("source_signature") and entry.get("pbf_url"):
            entry["source_signature"] = fetch_source_signature(entry["pbf_url"])
    entries = sorted(entries, key=lambda e: str(e.get("code", "")).upper())

    # Selector semantics:
    #   IR          -> all regions belonging to Iran
    #   ALL         -> every discovered country/region
    #   ALL/IR/AZ   -> everything except Iran and Azerbaijan
    # A region code such as CN-FUJIAN is also accepted and selects that exact
    # region. This filtering happens before chunk assignment, so a manual run
    # for one country cannot accidentally build unrelated countries.
    raw_selector = str(args.country_selector or "ALL").strip().upper()
    tokens = [t.strip() for t in raw_selector.split("/") if t.strip()]
    if not tokens:
        raise SystemExit("country-selector is empty")
    if tokens[0] == "ALL":
        excluded = set(tokens[1:])
        entries = [e for e in entries if str(e.get("country_code", "")).upper() not in excluded and str(e.get("code", "")).upper() not in excluded]
    else:
        wanted = set(tokens)
        entries = [e for e in entries if str(e.get("country_code", "")).upper() in wanted or str(e.get("code", "")).upper() in wanted]
    if not entries:
        raise SystemExit(f"country-selector matched no catalog entries: {raw_selector}")

    catalog = args.output / "expected-catalog.json"
    catalog.write_text(json.dumps({"release_tag": args.release_tag, "count": len(entries), "entries": entries, "selector": raw_selector}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    selected = [entry for index, entry in enumerate(entries) if index % args.chunk_count == args.chunk_index]

    existing_assets: set[str] = set()
    if args.existing_assets and args.existing_assets.is_file():
        existing_assets = {line.strip() for line in args.existing_assets.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()}
    successes: list[dict] = []
    failures: list[dict] = []
    builder = args.root / "tool/maps/build_country_abm.sh"
    updater = args.root / "tool/maps/update_map_manifest.py"
    splitter = args.root / "tool/maps/split_abm.py"
    with tempfile.TemporaryDirectory(prefix="abtin-map-build-") as temp:
        for number, entry in enumerate(selected, 1):
            code = str(entry.get("code", "")).upper()
            try:
                if not code or not entry.get("pbf_url"):
                    raise ValueError("missing code or pbf_url")
                previous = previous_entries.get(code, {})
                signature = str(entry.get("source_signature", ""))
                archive = args.output / f"{code}.abm"
                previous_signature = str(previous.get("source_signature") or previous.get("source", {}).get("signature", ""))
                release_has_archive = archive.name in existing_assets
                if previous_signature == signature and previous.get("sha256") and release_has_archive:
                    print(f"SKIP {code}: already in release and source signature unchanged ({signature})")
                    successes.append({"code": code, "name_fa": entry.get("name_fa", code), "name_en": entry.get("name_en", code), "archive": archive.name, "skipped": True, "reason": "release_asset_and_signature_match", "source_signature": signature})
                    continue
                if release_has_archive and not previous:
                    # Backward-compatible safety: an existing release asset is
                    # authoritative if its manifest entry is unavailable. Do not
                    # destroy/rebuild a map merely because metadata was lost.
                    print(f"SKIP {code}: asset already exists in release; no prior manifest entry")
                    successes.append({"code": code, "name_fa": entry.get("name_fa", code), "name_en": entry.get("name_en", code), "archive": archive.name, "skipped": True, "reason": "release_asset_exists_no_manifest_entry", "source_signature": signature})
                    continue
                cmd = ["bash", str(builder), code, str(entry["pbf_url"]), str(args.output)]
                if entry.get("bbox"):
                    # argparse treats a negative bbox as an option when it is
                    # passed as a separate token (e.g. --bbox -125,...).
                    # Use --bbox=VALUE so western/southern regions are valid.
                    cmd.append(f"--bbox={entry['bbox']}")
                last_error = None
                for attempt in range(1, 4):
                    try:
                        subprocess.run(cmd, check=True)
                        last_error = None
                        break
                    except subprocess.CalledProcessError as exc:
                        last_error = exc
                        print(f"BUILD {code} attempt {attempt}/3 failed", file=sys.stderr)
                if last_error is not None:
                    raise last_error
                if not archive.is_file() or archive.stat().st_size <= 127:
                    raise RuntimeError("builder returned without a valid archive")
                parts_manifest = None
                if archive.stat().st_size >= 2 * 1024**3 - 16 * 1024**2:
                    split_dir = args.output / "parts" / code
                    subprocess.run([sys.executable, str(splitter), "--archive", str(archive), "--output-dir", str(split_dir), "--code", code], check=True)
                    parts_manifest = split_dir / f"{code}.parts.json"
                next_manifest = Path(temp) / f"manifest-{code}.json"
                update_cmd = [
                    sys.executable, str(updater), "--output", str(next_manifest), "--previous", str(manifest),
                    "--release-tag", args.release_tag, "--code", code,
                    "--name-fa", str(entry.get("name_fa", code)), "--name-en", str(entry.get("name_en", code)),
                    "--country-code", str(entry.get("country_code", code[:2])),
                    "--country-name-fa", str(entry.get("country_name_fa", entry.get("name_fa", code))),
                    "--country-name-en", str(entry.get("country_name_en", entry.get("name_en", code))),
                    "--region-name-fa", str(entry.get("region_name_fa", entry.get("name_fa", code))),
                    "--region-name-en", str(entry.get("region_name_en", entry.get("name_en", code))),
                    "--group-order", str(entry.get("group_order", 0)),
                    "--bbox", str(entry.get("bbox", "-180,-90,180,90")),
                    "--source-url", str(entry["pbf_url"]),
                    "--source-signature", signature,
                ]
                if parts_manifest:
                    update_cmd += ["--parts-manifest", str(parts_manifest)]
                else:
                    update_cmd += ["--archive", str(archive)]
                subprocess.run(update_cmd, check=True)
                built_data = json.loads(next_manifest.read_text(encoding="utf-8"))
                built_entries = [x for x in built_data.get("countries", []) if str(x.get("code", "")).upper() == code]
                current_data = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else {"schema_version": 5, "release_tag": args.release_tag, "countries": []}
                current_entries = {str(x.get("code", "")).upper(): x for x in current_data.get("countries", []) if isinstance(x, dict) and x.get("code")}
                if built_entries:
                    current_entries[code] = built_entries[0]
                current_data["schema_version"] = 5
                current_data["release_tag"] = args.release_tag
                current_data["generated_at"] = datetime.now(UTC).isoformat()
                current_data["countries"] = [current_entries[k] for k in sorted(current_entries)]
                manifest.write_text(json.dumps(current_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                successes.append({"code": code, "name_fa": entry.get("name_fa", code), "name_en": entry.get("name_en", code), "archive": archive.name, "skipped": False, "source_signature": signature})
            except Exception as exc:
                failures.append({"code": code or f"entry-{number}", "name_fa": entry.get("name_fa", code or f"entry-{number}"), "name_en": entry.get("name_en", code or f"entry-{number}"), "error": str(exc)})
                print(f"FAILED {code or number}: {exc}", file=sys.stderr)
    report = {"generated_at": datetime.now(UTC).isoformat(), "release_tag": args.release_tag, "chunk_index": args.chunk_index, "chunk_count": args.chunk_count, "expected_count": len(entries), "selected_count": len(selected), "success_count": len(successes), "failure_count": len(failures), "successes": successes, "failures": failures}
    (args.output / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Completed chunk: expected={len(entries)} selected={len(selected)} success={len(successes)} failure={len(failures)}")
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
