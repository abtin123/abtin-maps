#!/usr/bin/env python3
"""Merge one built `CC.abm` container into the app's map manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_bbox(raw: str) -> list[float]:
    try:
        values = [float(value.strip()) for value in raw.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("bbox must be minLon,minLat,maxLon,maxLat") from exc
    if len(values) != 4 or values[0] >= values[2] or values[1] >= values[3]:
        raise argparse.ArgumentTypeError("bbox must be minLon,minLat,maxLon,maxLat")
    return values


def load_previous(path: Path | None) -> list[dict[str, object]]:
    if path is None or not path.is_file():
        return []
    decoded = json.loads(path.read_text(encoding="utf-8"))
    countries = decoded.get("countries") if isinstance(decoded, dict) else None
    if not isinstance(countries, list):
        raise SystemExit(f"Previous manifest has no countries array: {path}")
    return [entry for entry in countries if isinstance(entry, dict)]


VECTOR_STYLE_RESOURCES = [
    "sprites/abtin.json",
    "sprites/abtin.png",
    "sprites/abtin@2x.json",
    "sprites/abtin@2x.png",
    "search/places.sqlite",
    "glyphs/Vazirmatn/0-255.pbf",
    "glyphs/Vazirmatn/256-511.pbf",
    "glyphs/Vazirmatn/1536-1791.pbf",
    "glyphs/Vazirmatn/1792-2047.pbf",
    "glyphs/Vazirmatn/8192-8447.pbf",
    "glyphs/Vazirmatn/64256-64511.pbf",
    "glyphs/Vazirmatn/64512-64767.pbf",
    "glyphs/Vazirmatn/65024-65279.pbf",
    "glyphs/Vazirmatn/65280-65535.pbf",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--parts-manifest", type=Path)
    parser.add_argument("--code", required=True)
    parser.add_argument("--name-fa", required=True)
    parser.add_argument("--name-en", required=True)
    parser.add_argument("--country-code", default="")
    parser.add_argument("--country-name-fa", default="")
    parser.add_argument("--country-name-en", default="")
    parser.add_argument("--region-name-fa", default="")
    parser.add_argument("--region-name-en", default="")
    parser.add_argument("--group-order", type=int, default=0)
    parser.add_argument("--bbox", type=parse_bbox, required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-signature", default="")
    parser.add_argument("--patch-json", type=Path)
    parser.add_argument("--patch-bin", type=Path)
    args = parser.parse_args()

    code = args.code.upper()
    if not code.replace("-", "").isalnum():
        raise SystemExit("Country code must contain only letters, digits, or hyphen.")
    if args.archive and args.archive.name != f"{code}.abm":
        raise SystemExit(f"Archive must be named exactly {code}.abm")
    if not args.archive and not args.parts_manifest:
        raise SystemExit("Provide --archive or --parts-manifest")
    if args.archive and not args.archive.is_file():
        raise SystemExit(f"Archive was not found: {args.archive}")

    country_code = (args.country_code or code[:2]).upper()
    patch = None
    if args.patch_json and args.patch_bin and args.patch_json.is_file() and args.patch_bin.is_file():
        patch_data = json.loads(args.patch_json.read_text(encoding="utf-8"))
        if patch_data.get("schema") == "ABTINMAP-CHUNK-PATCH/1":
            patch = {
                "base_sha256": str(patch_data.get("base_sha256", "")),
                "manifest_file": args.patch_json.name,
                "bin_file": args.patch_bin.name,
                "size": args.patch_bin.stat().st_size,
                "sha256": file_sha256(args.patch_bin),
            }
    entry: dict[str, object] = {
        "code": code,
        "name_fa": args.name_fa,
        "name_en": args.name_en,
        "country_code": country_code,
        "country_name_fa": args.country_name_fa or args.name_fa,
        "country_name_en": args.country_name_en or args.name_en,
        "region_name_fa": args.region_name_fa or args.name_fa,
        "region_name_en": args.region_name_en or args.name_en,
        "group_order": args.group_order,
        "bbox": args.bbox,
        "files": [],
        "total_size": 0,
        "sha256": "",
        "source": {
            "provider": "OpenStreetMap",
            "signature": args.source_signature,
            "url": args.source_url,
            "attribution": "© OpenStreetMap contributors, ODbL 1.0",
            "license_url": "https://opendatacommons.org/licenses/odbl/1.0/",
            "copyright_url": "https://www.openstreetmap.org/copyright",
        },
        "patch": patch,
        "vector_map": {
            "embedded": True,
            "day_style": "styles/day.json",
            "night_style": "styles/night.json",
            "resources": VECTOR_STYLE_RESOURCES,
        },
    }
    if args.parts_manifest:
        pm = json.loads(args.parts_manifest.read_text(encoding="utf-8"))
        parts = pm.get("parts") if isinstance(pm, dict) else None
        if not isinstance(parts, list) or not parts:
            raise SystemExit("Invalid parts manifest")
        joined_hash = hashlib.sha256()
        total = 0
        base = args.parts_manifest.parent
        for part in parts:
            name = str(part.get("name", "")); f = base / name
            if not f.is_file(): raise SystemExit(f"Missing ABM part: {f}")
            size = f.stat().st_size; digest = file_sha256(f); total += size
            with f.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    joined_hash.update(chunk)
            entry["files"].append({"name": name, "size": size, "sha256": digest})
        entry["total_size"] = total
        entry["sha256"] = joined_hash.hexdigest()
    else:
        entry["files"] = [{"name": args.archive.name, "size": args.archive.stat().st_size, "sha256": file_sha256(args.archive)}]
        entry["total_size"] = args.archive.stat().st_size
        entry["sha256"] = file_sha256(args.archive)
    existing = load_previous(args.previous)
    merged = [item for item in existing if str(item.get("code", "")).upper() != code]
    merged.append(entry)
    merged.sort(key=lambda item: str(item.get("code", "")))
    output = {
        "schema_version": 5,
        "release_tag": args.release_tag,
        "generated_at": datetime.now(UTC).isoformat(),
        "countries": merged,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest updated: {args.output} | countries={len(merged)} | replaced={code}")


if __name__ == "__main__":
    main()
