"""Build the AbtinMaps country build catalogue from Geofabrik's public index.

This tool never downloads map PBFs.  It only reads Geofabrik's public, stable
index and produces a reviewed build-catalogue that the map builder can consume.
Curated profiles in countries.json override generated display text and tuning.

Examples:
  python3 tools/sync_geofabrik_catalog.py \
    --curated tools/countries.json --out tools/countries.resolved.json
  python3 tools/sync_geofabrik_catalog.py --index-file /tmp/index-v1.json \
    --curated tools/countries.json --out /tmp/catalog.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


INDEX_URL = "https://download.geofabrik.de/index-v1.json"
ODBL_URL = "https://opendatacommons.org/licenses/odbl/1.0/"
OSM_COPYRIGHT_URL = "https://www.openstreetmap.org/copyright"
ATTRIBUTION = "Map data from OpenStreetMap, ODbL 1.0"
ALLOWED_HOSTS = {"download.geofabrik.de"}


def _safe_code(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9-]+", "-", value.upper()).strip("-")
    if not result or len(result) > 16:
        raise ValueError(f"شناسهٔ extract قابل استفاده نیست: {value!r}")
    return result


def _pbf_url(feature: dict[str, Any]) -> str | None:
    url = (feature.get("properties") or {}).get("urls", {}).get("pbf")
    if not isinstance(url, str) or not url.startswith("https://"):
        return None
    host = urlparse(url).hostname
    return url if host in ALLOWED_HOSTS else None


def _iter_positions(value: Any) -> Iterable[tuple[float, float]]:
    if isinstance(value, (list, tuple)) and len(value) >= 2 and all(
        isinstance(item, (int, float)) for item in value[:2]
    ):
        yield float(value[0]), float(value[1])
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_positions(item)


def _bbox(geometry: Any) -> list[float] | None:
    if not isinstance(geometry, dict):
        return None
    positions = list(_iter_positions(geometry.get("coordinates")))
    if not positions:
        return None
    lons, lats = zip(*positions)
    return [round(min(lons), 6), round(min(lats), 6),
            round(max(lons), 6), round(max(lats), 6)]


def _load_json(path_or_url: str) -> dict[str, Any]:
    if path_or_url.startswith("https://"):
        request = urllib.request.Request(
            path_or_url,
            headers={"User-Agent": "AbtinMapsCatalog/1.0 (+offline map builder)"},
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read()
    else:
        data = Path(path_or_url).read_bytes()
    decoded = json.loads(data.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("فهرست Geofabrik معتبر نیست")
    return decoded


def _country_code(properties: dict[str, Any]) -> tuple[str, str, bool] | None:
    iso1 = [str(value).upper() for value in properties.get("iso3166-1:alpha2", [])
            if isinstance(value, str) and len(value) == 2]
    iso2 = [str(value).upper() for value in properties.get("iso3166-2", [])
            if isinstance(value, str) and len(value) >= 4]
    if len(iso1) == 1:
        return iso1[0], iso1[0], False
    if len(iso1) > 1:
        return _safe_code("-".join(iso1)), iso1[0], False
    if len(iso2) == 1:
        return _safe_code(iso2[0]), iso2[0][:2], True
    return None


def _curated_by_code(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    decoded = json.loads(path.read_text(encoding="utf-8"))
    entries = decoded.get("countries", []) if isinstance(decoded, dict) else []
    result: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("code"), str):
            result[entry["code"].upper()] = dict(entry)
    return result


def _normalise_generated(feature: dict[str, Any], curated: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    properties = feature.get("properties") or {}
    if not isinstance(properties, dict):
        return None
    pbf = _pbf_url(feature)
    identity = _country_code(properties)
    if pbf is None or identity is None:
        return None
    code, country_code, is_subregion = identity
    english_name = str(properties.get("name") or code)
    parent = str(properties.get("parent") or "")
    override = curated.get(code, {})
    entry: dict[str, Any] = dict(override)
    entry.update({
        "code": code,
        "name_en": entry.get("name_en") or english_name,
        "name_fa": entry.get("name_fa") or english_name,
        "country_code": entry.get("country_code") or country_code,
        "country_name_en": entry.get("country_name_en") or english_name,
        "country_name_fa": entry.get("country_name_fa") or entry.get("name_fa") or english_name,
        "region_name_en": entry.get("region_name_en") or english_name,
        "region_name_fa": entry.get("region_name_fa") or entry.get("name_fa") or english_name,
        "pbf_url": pbf,
        "pbf_updates_url": (properties.get("urls") or {}).get("updates", ""),
        "geofabrik_id": str(properties.get("id") or ""),
        "geofabrik_parent": parent,
        "bbox": _bbox(feature.get("geometry")),
        "is_subregion": is_subregion,
        "source_attribution": ATTRIBUTION,
        "source_license_url": ODBL_URL,
        "source_copyright_url": OSM_COPYRIGHT_URL,
        "source_provider": "Geofabrik / OpenStreetMap",
    })
    entry.setdefault("render_max_zoom", 14)
    entry.setdefault("atlas_target_mb", 260)
    entry.setdefault("group_order", 0)
    return entry


def _entry_sort_key(entry: dict[str, Any]) -> tuple[str, int, str]:
    return (
        str(entry.get("country_code") or entry["code"]),
        int(entry.get("group_order") or 0),
        str(entry["code"]),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ساخت catalog قابل انتشار آبتین‌مپ از index عمومی Geofabrik",
    )
    parser.add_argument("--index-url", default=INDEX_URL)
    parser.add_argument("--index-file", help="فایل index-v1.json cache شده؛ جای index-url")
    parser.add_argument("--curated", default="tools/countries.json")
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--include-subregions", action="store_true",
        help="regionهای ISO-3166-2 را نیز می‌افزاید؛ برای کشور بزرگ/تقسیم‌شده",
    )
    parser.add_argument(
        "--only", default="",
        help="فقط codeهای داده‌شده با کاما را نگه می‌دارد؛ برای build آزمایشی",
    )
    args = parser.parse_args()

    index = _load_json(args.index_file or args.index_url)
    features = index.get("features")
    if not isinstance(features, list):
        raise SystemExit("index Geofabrik فاقد features است")
    curated = _curated_by_code(Path(args.curated))
    sharded_parents = {
        str(entry.get("country_code", "")).upper()
        for entry in curated.values()
        if str(entry.get("country_code", "")).upper()
        and str(entry.get("country_code", "")).upper() != str(entry.get("code", "")).upper()
    }
    entries: dict[str, dict[str, Any]] = {}
    for feature in features:
        if not isinstance(feature, dict):
            continue
        entry = _normalise_generated(feature, curated)
        if entry is None:
            continue
        if entry["code"] in sharded_parents and entry["code"] not in curated:
            continue
        if entry["is_subregion"] and not args.include_subregions and entry["code"] not in curated:
            continue
        entries[entry["code"]] = entry

    for code, entry in curated.items():
        pbf = entry.get("pbf_url")
        host = urlparse(str(pbf)).hostname if isinstance(pbf, str) else None
        if host not in ALLOWED_HOSTS:
            continue
        name_fa = str(entry.get("name_fa") or code)
        name_en = str(entry.get("name_en") or code)
        country_code = str(entry.get("country_code") or code[:2]).upper()
        entries.setdefault(code, {
            **entry,
            "code": code,
            "name_fa": name_fa,
            "name_en": name_en,
            "country_code": country_code,
            "country_name_fa": str(entry.get("country_name_fa") or name_fa),
            "country_name_en": str(entry.get("country_name_en") or name_en),
            "region_name_fa": str(entry.get("region_name_fa") or name_fa),
            "region_name_en": str(entry.get("region_name_en") or name_en),
            "group_order": int(entry.get("group_order") or 0),
            "render_max_zoom": int(entry.get("render_max_zoom") or 14),
            "atlas_target_mb": int(entry.get("atlas_target_mb") or 260),
            "bbox": entry.get("bbox"),
            "source_attribution": ATTRIBUTION,
            "source_license_url": ODBL_URL,
            "source_copyright_url": OSM_COPYRIGHT_URL,
            "source_provider": "Geofabrik / OpenStreetMap",
        })

    wanted = {part.strip().upper() for part in args.only.split(",") if part.strip()}
    result = sorted(
        (entry for entry in entries.values()
         if not wanted or entry["code"] in wanted or entry.get("country_code", "").upper() in wanted),
        key=_entry_sort_key,
    )
    missing = wanted - {entry["code"] for entry in result} - {
        str(entry.get("country_code", "")).upper() for entry in result
    }
    if missing:
        print(f"هشدار: profile پیدا نشد: {', '.join(sorted(missing))}", file=sys.stderr)

    output = {
        "schema": 2,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_index": args.index_file or args.index_url,
        "source_attribution": ATTRIBUTION,
        "source_license_url": ODBL_URL,
        "countries": result,
    }
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    country_count = len({str(item.get("country_code") or item["code"]) for item in result})
    print(f"catalog -> {target} | {len(result)} profile | {country_count} کشور")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
