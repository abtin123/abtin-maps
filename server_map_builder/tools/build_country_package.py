#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build one legal offline ABM package from a generated country profile.

The script is deliberately country/profile scoped.  It may be called from a
CI matrix or locally for one chosen country.  It does not start a world-sized
build simply because a catalogue contains many countries.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any


TOOLS = Path(__file__).resolve().parent
ODBL_URL = "https://opendatacommons.org/licenses/odbl/1.0/"
OSM_COPYRIGHT_URL = "https://www.openstreetmap.org/copyright"
ATTRIBUTION = "Map data from OpenStreetMap, ODbL 1.0"


def load_profile(catalog_path: Path, code: str) -> dict[str, Any]:
    decoded = json.loads(catalog_path.read_text(encoding="utf-8"))
    entries = decoded.get("countries", []) if isinstance(decoded, dict) else []
    target = code.upper()
    for entry in entries:
        if isinstance(entry, dict) and str(entry.get("code", "")).upper() == target:
            return entry
    raise SystemExit(f"profile نقشه برای «{code}» در {catalog_path} پیدا نشد")


def run(command: list[str], *, dry_run: bool) -> None:
    print("+", " ".join(command), flush=True)
    if not dry_run:
        subprocess.run(command, check=True)


def remote_size(url: str) -> int | None:
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "AbtinMapBuilder/2.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            value = response.headers.get("Content-Length")
            return int(value) if value and value.isdigit() else None
    except Exception:
        return None


def download_with_resume(url: str, destination: Path, *, dry_run: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    # curl -C - فایل .part را در صورت پشتیبانی سرور از Range ادامه می‌دهد.
    # فایل نهایی فقط پس از download کامل rename می‌شود.
    pending = destination.with_suffix(destination.suffix + ".part")
    command = [
        "curl", "--fail", "--location", "--continue-at", "-",
        "--retry", "5", "--retry-delay", "8", "--retry-all-errors",
        "--user-agent", "AbtinMapBuilder/2.0 (legal OSM offline package)",
        "--output", str(pending), url,
    ]
    run(command, dry_run=dry_run)
    if not dry_run:
        pending.replace(destination)


def main() -> int:
    parser = argparse.ArgumentParser(description="ساخت یک بستهٔ offline ABM برای یک profile کشور")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--code", required=True)
    parser.add_argument("--out-dir", default="out")
    parser.add_argument("--source-dir", default="src")
    parser.add_argument("--input-pbf", help="PBF محلی؛ در این حالت دانلود انجام نمی‌شود")
    parser.add_argument("--release-tag", default="maps-v3")
    parser.add_argument("--repo", default="abtin123/abtin-maps")
    parser.add_argument("--max-source-gb", type=float, default=8.0)
    parser.add_argument("--allow-large-source", action="store_true")
    parser.add_argument("--keep-source", action="store_true")
    parser.add_argument("--skip-atlas", action="store_true", help="فقط برای اشکال‌زدایی ABM خام؛ انتشار با این گزینه ممنوع است")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    profile = load_profile(Path(args.catalog), args.code)
    code = str(profile["code"]).upper()
    pbf_url = str(profile.get("pbf_url") or "")
    if not args.input_pbf and not pbf_url.startswith("https://download.geofabrik.de/"):
        raise SystemExit("URL ورودی باید extract عمومی HTTPS از Geofabrik باشد")
    out_dir = Path(args.out_dir)
    source_dir = Path(args.source_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)
    target_pbf = Path(args.input_pbf) if args.input_pbf else source_dir / f"{code}.osm.pbf"

    if not args.input_pbf:
        size = remote_size(pbf_url)
        limit = int(args.max_source_gb * 1024 * 1024 * 1024)
        if size and size > limit and not args.allow_large_source:
            raise SystemExit(
                f"ورودی {code} حدود {size / 1024 ** 3:.1f}GB است؛ "
                "برای جلوگیری از پرشدن دیسک، --allow-large-source را فقط روی runner مناسب اضافه کنید."
            )
        if not target_pbf.exists() or target_pbf.stat().st_size < 200_000:
            download_with_resume(pbf_url, target_pbf, dry_run=args.dry_run)

    abm = out_dir / f"{code}.abm"
    string_state = TOOLS / "string_state" / f"{code}.json"
    base_command = [
        sys.executable, str(TOOLS / "abtinmap_build.py"), str(target_pbf),
        "--output", str(abm), "--region", code, "--profile", "compact",
        "--building-min-zoom", "16", "--poi-min-zoom", "16",
        "--string-state", str(string_state),
    ]
    run(base_command, dry_run=args.dry_run)

    rendered_meta: Path | None = None
    if not args.skip_atlas:
        atlas_command = [
            sys.executable, str(TOOLS / "rendered_tile_builder.py"), str(target_pbf),
            "--code", code, "--out-dir", str(out_dir),
            "--min-zoom", str(int(profile.get("render_min_zoom", 5))),
            "--max-zoom", str(int(profile.get("render_max_zoom", 16))),
            "--target-mb", str(int(profile.get("atlas_target_mb", 260))),
            "--workers", str(int(profile.get("render_workers", 4))),
            "--webp-quality", str(int(profile.get("webp_quality", 60))),
            "--webp-method", str(int(profile.get("webp_method", 1))),
            "--max-open-tiles", str(int(profile.get("max_open_tiles", 512))),
        ]
        bounds = profile.get("bbox")
        if isinstance(bounds, list) and len(bounds) == 4 and all(isinstance(v, (int, float)) for v in bounds):
            atlas_command.extend(["--bounds", *(str(float(value)) for value in bounds)])
        run(atlas_command, dry_run=args.dry_run)
        atlas = out_dir / f"{code}.amap"
        preview = out_dir / f"{code}.preview.webp"
        run([
            sys.executable, str(TOOLS / "embed_rendered_atlas.py"),
            str(abm), str(atlas), "--preview", str(preview),
        ], dry_run=args.dry_run)
        rendered_meta = out_dir / f"rendered-{code}.json"

    run([sys.executable, str(TOOLS / "abtinmap_inspect.py"), str(abm)], dry_run=args.dry_run)
    manifest_command = [
        sys.executable, str(TOOLS / "make_manifest.py"), str(abm),
        "--code", code,
        "--name-fa", str(profile.get("name_fa") or code),
        "--name-en", str(profile.get("name_en") or code),
        "--country-code", str(profile.get("country_code") or code[:2]),
        "--country-name-fa", str(profile.get("country_name_fa") or profile.get("name_fa") or code),
        "--country-name-en", str(profile.get("country_name_en") or profile.get("name_en") or code),
        "--region-name-fa", str(profile.get("region_name_fa") or profile.get("name_fa") or code),
        "--region-name-en", str(profile.get("region_name_en") or profile.get("name_en") or code),
        "--group-order", str(int(profile.get("group_order") or 0)),
        "--out-dir", str(out_dir), "--release-tag", args.release_tag, "--repo", args.repo,
        "--source-url", pbf_url,
        "--source-provider", str(profile.get("source_provider") or "Geofabrik / OpenStreetMap"),
        "--source-attribution", str(profile.get("source_attribution") or ATTRIBUTION),
        "--source-license-url", str(profile.get("source_license_url") or ODBL_URL),
        "--source-copyright-url", str(profile.get("source_copyright_url") or OSM_COPYRIGHT_URL),
    ]
    if rendered_meta is not None:
        manifest_command.extend(["--rendered-meta", str(rendered_meta)])
    run(manifest_command, dry_run=args.dry_run)

    if not args.dry_run and not args.skip_atlas:
        # metadata کوچکِ رندر بخشی از provenance و manifest است؛ فقط archive و
        # preview موقت که پیش‌تر در ABM embed شده‌اند پاک می‌شوند.
        for temporary in (out_dir / f"{code}.amap", out_dir / f"{code}.preview.webp"):
            if temporary.exists():
                temporary.unlink()
    if not args.dry_run and not args.keep_source and not args.input_pbf:
        target_pbf.unlink(missing_ok=True)
    print(f"پکیج {code} آماده است: {out_dir / f'manifest-{code}.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
