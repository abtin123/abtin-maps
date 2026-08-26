"""رندر مرحله‌ای و قابل‌ادامهٔ atlas برای تمام بسته‌های نقشهٔ آبتین.

هر کشور به یک شبکهٔ ``grid_size × grid_size`` تقسیم می‌شود. هر invocation فقط
یک stage را با یک renderer می‌سازد و پس از تأیید خروجی، نشانگر ``complete.json``
می‌نویسد. بنابراین می‌توان هر stage را در یک GitHub job جدا اجرا کرد: اجرای
بعدی stageهای کامل را reuse می‌کند و تنها بخش ناقص را بازسازی می‌کند.

مسیرهای مهم:
  checkpoints/<CODE>/stages/R00C00/  کاشی‌های WebP و نشانگر تکمیل همان stage
  out/<CODE>.amap                         atlas نهایی پس از --merge

این ابزار هیچ منبع OSM جدیدی تولید یا منتشر نمی‌کند؛ داده‌ها فقط از PBF رسمی
Geofabrik که در catalog ثبت شده خوانده می‌شوند.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_country_package import (
    ATTRIBUTION,
    ODBL_URL,
    OSM_COPYRIGHT_URL,
    TOOLS,
    download_with_resume,
    load_profile,
    remote_size,
    run,
)

FORMAT_VERSION = 1
DEFAULT_GRID_SIZE = 4


def grid_bboxes(bbox: list[float], grid_size: int, overlap: float) -> list[tuple[str, list[float]]]:
    """یک bbox را با هم‌پوشانی داخلی به شبکهٔ مربع‌های نام‌دار تقسیم می‌کند."""
    min_lon, min_lat, max_lon, max_lat = (float(v) for v in bbox)
    if not (min_lon < max_lon and min_lat < max_lat):
        raise SystemExit(f"bbox نامعتبر است: {bbox}")
    lon_step = (max_lon - min_lon) / grid_size
    lat_step = (max_lat - min_lat) / grid_size
    stages: list[tuple[str, list[float]]] = []
    for row in range(grid_size):
        for col in range(grid_size):
            left = min_lon + col * lon_step
            right = min_lon + (col + 1) * lon_step
            bottom = min_lat + row * lat_step
            top = min_lat + (row + 1) * lat_step
            if col > 0:
                left -= overlap
            if col < grid_size - 1:
                right += overlap
            if row > 0:
                bottom -= overlap
            if row < grid_size - 1:
                top += overlap
            stages.append((f"R{row:02d}C{col:02d}", [left, bottom, right, top]))
    return stages


def source_fingerprint(url: str) -> dict[str, str]:
    """هویت نسخهٔ فعلی PBF را از سرور رسمی می‌گیرد.

    این fingerprint بخشی از marker هر stage است. اگر Geofabrik فایل latest را
    به‌روزرسانی کند، ETag یا Last-Modified/اندازه تغییر می‌کند و checkpoint
    قبلی عمداً نامعتبر می‌شود.
    """
    request = urllib.request.Request(
        url,
        method="HEAD",
        headers={"User-Agent": "AbtinMapBuilder/2.0 (checkpoint validation)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            headers = response.headers
            return {
                "url": url,
                "etag": str(headers.get("ETag") or ""),
                "last_modified": str(headers.get("Last-Modified") or ""),
                "content_length": str(headers.get("Content-Length") or ""),
            }
    except Exception as exc:
        raise SystemExit(f"دریافت fingerprint منبع Geofabrik ناموفق بود: {exc}") from exc


def profile_signature(
    profile: dict[str, Any], grid_size: int, overlap: float, source: dict[str, str],
) -> dict[str, Any]:
    """تنظیمات مؤثر رندر که تغییرشان checkpoint قبلی را نامعتبر می‌کند."""
    return {
        "format_version": FORMAT_VERSION,
        "grid_size": grid_size,
        "overlap": overlap,
        "render_min_zoom": int(profile.get("render_min_zoom", 2)),
        "render_max_zoom": int(profile.get("render_max_zoom", 14)),
        "webp_quality": int(profile.get("webp_quality", 60)),
        "webp_method": int(profile.get("webp_method", 1)),
        "max_open_tiles": max(32, int(profile.get("max_open_tiles", 512))),
        "include_poi_tiles": bool(profile.get("include_poi_tiles")),
        "include_buildings": bool(profile.get("include_buildings")),
        "source": source,
    }


def complete_marker(stage_dir: Path) -> Path:
    return stage_dir / "complete.json"


def is_complete(stage_dir: Path, expected: dict[str, Any]) -> bool:
    marker = complete_marker(stage_dir)
    if not marker.exists():
        return False
    try:
        recorded = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if recorded.get("signature") != expected:
        return False
    tile_count = int(recorded.get("webp_files", 0))
    actual_count = sum(1 for _ in stage_dir.rglob("*.webp"))
    return actual_count == tile_count


def pbf_for(profile: dict[str, Any], code: str, source_dir: Path, *, dry_run: bool) -> Path:
    source_dir.mkdir(parents=True, exist_ok=True)
    pbf_url = str(profile.get("pbf_url") or "")
    if not pbf_url.startswith("https://download.geofabrik.de/"):
        raise SystemExit("PBF باید extract عمومی HTTPS از Geofabrik باشد")
    target = source_dir / f"{code}.osm.pbf"
    if target.exists() and target.stat().st_size >= 200_000:
        return target
    download_with_resume(pbf_url, target, dry_run=dry_run)
    return target


def render_stage(
    *, profile: dict[str, Any], code: str, stage_name: str, bounds: list[float],
    stage_dir: Path, source_dir: Path, signature: dict[str, Any], dry_run: bool,
) -> None:
    if is_complete(stage_dir, signature):
        print(f"checkpoint معتبر است؛ stage {code}/{stage_name} دوباره ساخته نمی‌شود", flush=True)
        return
    if not dry_run and shutil.which("osmium") is None:
        raise SystemExit("osmium-tool نصب نیست؛ ساخت stage بدون برش جغرافیایی مجاز نیست")

    shutil.rmtree(stage_dir, ignore_errors=True)
    stage_dir.parent.mkdir(parents=True, exist_ok=True)
    pbf = pbf_for(profile, code, source_dir, dry_run=dry_run)
    shard_pbf = source_dir / f"{code}.{stage_name}.osm.pbf"
    try:
        run([
            "osmium", "extract", "--overwrite", "-b", ",".join(str(v) for v in bounds),
            "-s", "complete_ways", "-o", str(shard_pbf), str(pbf),
        ], dry_run=dry_run)
        command = [
            sys.executable, str(TOOLS / "rendered_tile_builder.py"), str(shard_pbf),
            "--code", code, "--out-dir", str(stage_dir.parent), "--shard-out", str(stage_dir),
            "--min-zoom", str(signature["render_min_zoom"]),
            "--max-zoom", str(signature["render_max_zoom"]),
            "--webp-quality", str(signature["webp_quality"]),
            "--webp-method", str(signature["webp_method"]),
            "--workers", "1",
            "--max-open-tiles", str(signature["max_open_tiles"]),
        ]
        if signature["include_poi_tiles"]:
            command.append("--include-poi-tiles")
        if signature["include_buildings"]:
            command.append("--include-buildings")
        run(command, dry_run=dry_run)
        if dry_run:
            return
        webp_files = sum(1 for _ in stage_dir.rglob("*.webp"))
        marker = {
            "stage": stage_name,
            "bounds": bounds,
            "signature": signature,
            "webp_files": webp_files,
            "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        complete_marker(stage_dir).write_text(
            json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        print(f"checkpoint ساخته شد: {code}/{stage_name} ({webp_files:,} کاشی)", flush=True)
    finally:
        if not dry_run:
            shard_pbf.unlink(missing_ok=True)


def merge_stages(
    *, profile: dict[str, Any], code: str, all_stages: list[tuple[str, list[float]]],
    checkpoint_root: Path, out_dir: Path, signature: dict[str, Any], dry_run: bool,
) -> None:
    missing = [name for name, _ in all_stages if not is_complete(checkpoint_root / "stages" / name, signature)]
    if missing:
        raise SystemExit(
            f"ادغام مجاز نیست؛ {len(missing)} checkpoint کامل نیست: {', '.join(missing)}",
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    stage_dirs = [checkpoint_root / "stages" / name for name, _ in all_stages]
    bbox = [float(v) for v in profile["bbox"]]
    command = [
        sys.executable, str(TOOLS / "rendered_tile_builder.py"),
        "--code", code, "--out-dir", str(out_dir), "--merge-shards", *(str(path) for path in stage_dirs),
        "--min-zoom", str(signature["render_min_zoom"]),
        "--max-zoom", str(signature["render_max_zoom"]),
        "--target-mb", str(int(profile.get("atlas_target_mb", 260))),
        "--bounds", *(str(v) for v in bbox),
    ]
    run(command, dry_run=dry_run)


def main() -> int:
    parser = argparse.ArgumentParser(description="رندر checkpoint‌دار atlas برای هر کشور")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--code", required=True)
    parser.add_argument("--checkpoint-dir", default="checkpoints")
    parser.add_argument("--source-dir", default="src")
    parser.add_argument("--out-dir", default="out")
    parser.add_argument("--grid-size", type=int, default=DEFAULT_GRID_SIZE)
    parser.add_argument("--overlap-deg", type=float, default=0.20)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--stage", help="نام stage مانند R00C00 یا شمارهٔ صفرمبنا")
    group.add_argument("--merge", action="store_true", help="همهٔ checkpointهای کامل را به atlas نهایی ادغام می‌کند")
    parser.add_argument("--keep-source", action="store_true", help="PBF اصلی را پس از stage حذف نکن")
    parser.add_argument("--max-source-gb", type=float, default=8.0)
    parser.add_argument("--allow-large-source", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not 1 <= args.grid_size <= 12:
        raise SystemExit("grid-size باید بین 1 و 12 باشد")
    if not 0 <= args.overlap_deg < 2:
        raise SystemExit("overlap-deg نامعتبر است")
    profile = load_profile(Path(args.catalog), args.code)
    code = str(profile["code"]).upper()
    bbox = profile.get("bbox")
    if not (isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(v, (int, float)) for v in bbox)):
        raise SystemExit(f"bbox معتبر برای {code} در catalog وجود ندارد")
    pbf_url = str(profile.get("pbf_url") or "")
    size = remote_size(pbf_url)
    limit = int(args.max_source_gb * 1024 * 1024 * 1024)
    if size and size > limit and not args.allow_large_source:
        raise SystemExit(
            f"ورودی {code} حدود {size / 1024 ** 3:.1f}GB است؛ --allow-large-source لازم است.",
        )

    all_stages = grid_bboxes([float(v) for v in bbox], args.grid_size, args.overlap_deg)
    source = source_fingerprint(pbf_url)
    signature = profile_signature(profile, args.grid_size, args.overlap_deg, source)
    checkpoint_root = Path(args.checkpoint_dir) / code
    source_dir = Path(args.source_dir)
    try:
        if args.merge:
            merge_stages(
                profile=profile, code=code, all_stages=all_stages,
                checkpoint_root=checkpoint_root, out_dir=Path(args.out_dir),
                signature=signature, dry_run=args.dry_run,
            )
            return 0

        by_name = dict(all_stages)
        requested = args.stage.upper()
        if requested.isdigit():
            index = int(requested)
            if not 0 <= index < len(all_stages):
                raise SystemExit(f"شمارهٔ stage باید بین 0 و {len(all_stages) - 1} باشد")
            requested = all_stages[index][0]
        if requested not in by_name:
            raise SystemExit(f"stage ناشناخته است: {args.stage}; معتبر: {', '.join(by_name)}")
        render_stage(
            profile=profile, code=code, stage_name=requested, bounds=by_name[requested],
            stage_dir=checkpoint_root / "stages" / requested, source_dir=source_dir,
            signature=signature, dry_run=args.dry_run,
        )
        return 0
    finally:
        if not args.keep_source and not args.dry_run:
            (source_dir / f"{code}.osm.pbf").unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
