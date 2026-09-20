#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(path: Path | None) -> dict:
    if not path or not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            value = json.load(f)
        return value if isinstance(value, dict) else {}
    except Exception as exc:
        print(f"Warning: cannot read {path}: {exc}")
        return {}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_info(path: Path) -> dict:
    return {
        "name": path.name,
        "size": path.stat().st_size,
        "sha256": sha256(path),
    }


def country_code(path: Path) -> str | None:
    if path.suffix.lower() != ".abm":
        return None
    code = path.stem.strip().upper()
    return code or None


def index(manifest: dict) -> dict[str, dict]:
    result = {}
    for item in manifest.get("countries", []) or []:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code", "")).strip().upper()
        if code:
            result[code] = dict(item)
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--previous-manifest", type=Path)
    p.add_argument("--current-manifest", type=Path)
    p.add_argument("--asset-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--release-tag", default="")
    args = p.parse_args()

    previous = load_json(args.previous_manifest)
    current = load_json(args.current_manifest)

    # Start with ALL countries known by the previous release.
    countries = index(previous)

    # Current build wins for countries that were rebuilt.
    for code, item in index(current).items():
        countries[code] = item

    # The release's actual ABM files are authoritative for file/hash/size.
    # This is what prevents IR.abm from disappearing when only AM is rebuilt.
    assets = sorted(
        x for x in args.asset_dir.rglob("*.abm")
        if x.is_file()
    )

    for asset in assets:
        code = country_code(asset)
        if not code:
            continue

        old = countries.get(code, {
            "code": code,
            "country_code": code,
            "name_fa": code,
            "name_en": code,
        })

        old["code"] = code
        old["files"] = [file_info(asset)]
        old["total_size"] = asset.stat().st_size
        old["sha256"] = sha256(asset)
        countries[code] = old

    result = {
        "release_tag": (
            args.release_tag
            or current.get("release_tag")
            or previous.get("release_tag")
            or ""
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "countries": [countries[k] for k in sorted(countries)],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Manifest: {args.output}")
    print(f"Countries: {len(result['countries'])}")
    for item in result["countries"]:
        print(f"  {item['code']}: {item['files'][0]['name']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
