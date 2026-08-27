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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--code", required=True)
    parser.add_argument("--name-fa", required=True)
    parser.add_argument("--name-en", required=True)
    parser.add_argument("--bbox", type=parse_bbox, required=True)
    parser.add_argument("--source-url", required=True)
    args = parser.parse_args()

    code = args.code.upper()
    if not code.replace("-", "").isalnum():
        raise SystemExit("Country code must contain only letters, digits, or hyphen.")
    if args.archive.name != f"{code}.abm":
        raise SystemExit(f"Archive must be named exactly {code}.abm")
    if not args.archive.is_file():
        raise SystemExit(f"Archive was not found: {args.archive}")

    entry: dict[str, object] = {
        "code": code,
        "name_fa": args.name_fa,
        "name_en": args.name_en,
        "bbox": args.bbox,
        "files": [
            {
                "name": args.archive.name,
                "size": args.archive.stat().st_size,
                "sha256": file_sha256(args.archive),
            }
        ],
        "total_size": args.archive.stat().st_size,
        "sha256": file_sha256(args.archive),
        "source": {
            "provider": "OpenStreetMap",
            "url": args.source_url,
            "attribution": "© OpenStreetMap contributors, ODbL 1.0",
            "license_url": "https://opendatacommons.org/licenses/odbl/1.0/",
            "copyright_url": "https://www.openstreetmap.org/copyright",
        },
        "vector_map": {
            "embedded": True,
            "day_style": "styles/day.json",
            "night_style": "styles/night.json",
            "resources": [],
        },
    }
    existing = load_previous(args.previous)
    merged = [item for item in existing if str(item.get("code", "")).upper() != code]
    merged.append(entry)
    merged.sort(key=lambda item: str(item.get("code", "")))
    output = {
        "schema_version": 4,
        "release_tag": args.release_tag,
        "generated_at": datetime.now(UTC).isoformat(),
        "countries": merged,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest updated: {args.output} | countries={len(merged)} | replaced={code}")


if __name__ == "__main__":
    main()
