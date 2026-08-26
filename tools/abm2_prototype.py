"""Prototype محدود ABM2؛ فقط برای benchmark، نه جایگزین ABM v2.

از یک PBF واقعی، یک tile برداری MVT می‌سازد، آن را مثل بخش VCH2 در ABM2
به‌صورت مستقل Zstd می‌کند و زمان read + decompress را اندازه می‌گیرد. خروجی
فقط یک tile است تا پیش از هر مهاجرت، مسیر فنی و بودجهٔ عملکرد با دادهٔ واقعی
اثبات شود.
"""

import argparse
import json
import math
import os
import struct
import tempfile
import time
from pathlib import Path

import mapbox_vector_tile
import osmium
import zstandard as zstd


MAGIC = b"ABTIN2\0\0"
HEADER_BYTES = 256
INDEX_PAGE_BYTES = 4096


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """(west, south, east, north) برای یک tile Web Mercator."""
    n = 1 << z
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0

    def latitude(tile_y: int) -> float:
        mercator = math.pi * (1.0 - 2.0 * tile_y / n)
        return math.degrees(math.atan(math.sinh(mercator)))

    return west, latitude(y + 1), east, latitude(y)


def tile_xy(lon: float, lat: float, z: int) -> tuple[int, int]:
    n = 1 << z
    x = int((lon + 180.0) / 360.0 * n)
    lat = max(-85.05112878, min(85.05112878, lat))
    rad = math.radians(lat)
    y = int((1.0 - math.log(math.tan(rad) + 1 / math.cos(rad)) / math.pi) / 2 * n)
    return min(max(x, 0), n - 1), min(max(y, 0), n - 1)


class RoadCollector(osmium.SimpleHandler):
    def __init__(self, bounds: tuple[float, float, float, float]):
        super().__init__()
        self.west, self.south, self.east, self.north = bounds
        self.features: list[dict] = []

    def way(self, way):
        road_type = way.tags.get("highway")
        if not road_type:
            return
        try:
            coords = [(node.lon, node.lat) for node in way.nodes if node.location.valid()]
        except Exception:
            return
        if len(coords) < 2:
            return
        if not any(self.west <= lon <= self.east and self.south <= lat <= self.north for lon, lat in coords):
            return
        self.features.append({
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "class": road_type,
                "name": way.tags.get("name:fa") or way.tags.get("name") or "",
                "oneway": way.tags.get("oneway") in ("yes", "true", "1"),
            },
            "id": int(way.id),
        })


def build_chunk(payload: bytes, z: int, x: int, y: int) -> bytes:
    """VCH2 با یک BASE_MVT section؛ قرارداد کامل در ABM2_SPEC.md است."""
    tile_key = (z << 58) | (x << 29) | y
    header = struct.pack("<4sBBHQII", b"VCH2", 1, z, 1, tile_key, 1, 0)
    section_offset = len(header) + 16
    section = struct.pack("<BBHIII", 1, 0, 0, section_offset, len(payload), 0)
    return header + section + payload


def write_container(output: Path, compressed_chunk: bytes, raw_chunk: bytes, z: int, x: int, y: int) -> dict:
    """مینیمال‌ترین container قابل seek برای benchmark یک tile واقعی."""
    index_offset = HEADER_BYTES
    chunk_offset = HEADER_BYTES + INDEX_PAGE_BYTES
    tile_key = (z << 58) | (x << 29) | y
    index = bytearray(INDEX_PAGE_BYTES)
    struct.pack_into("<4sHHI", index, 0, b"IDX2", 1, 0, 1)
    struct.pack_into(
        "<QIHHQIIIQI",
        index,
        16,
        tile_key,
        1,
        0,
        0,
        chunk_offset,
        len(compressed_chunk),
        len(raw_chunk),
        0,
        0,
        1,
    )
    header = bytearray(HEADER_BYTES)
    struct.pack_into("<8sHHII", header, 0, MAGIC, 2, 0, HEADER_BYTES, 0)
    struct.pack_into("<QQII", header, 100, index_offset, 1, 0, 0)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        handle.write(header)
        handle.write(index)
        handle.write(compressed_chunk)
    return {"chunk_offset": chunk_offset, "stored_bytes": len(compressed_chunk), "raw_bytes": len(raw_chunk)}


def measure_read(path: Path, chunk_offset: int, stored_bytes: int, repeats: int) -> dict:
    decoder = zstd.ZstdDecompressor()
    samples_ms: list[float] = []
    with path.open("rb") as handle:
        for _ in range(repeats):
            handle.seek(chunk_offset)
            started = time.perf_counter_ns()
            compressed = handle.read(stored_bytes)
            decoder.decompress(compressed)
            samples_ms.append((time.perf_counter_ns() - started) / 1_000_000)
    ordered = sorted(samples_ms)
    return {
        "samples_ms": [round(value, 3) for value in samples_ms],
        "p50_ms": round(ordered[len(ordered) // 2], 3),
        "p95_ms": round(ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)], 3),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ABM2 one-tile MVT benchmark prototype")
    parser.add_argument("input", help="فایل واقعی .osm.pbf")
    parser.add_argument("--lon", type=float, required=True, help="طول جغرافیایی مرکز prototype")
    parser.add_argument("--lat", type=float, required=True, help="عرض جغرافیایی مرکز prototype")
    parser.add_argument("--zoom", type=int, default=13)
    parser.add_argument("--output", default="out/prototype.abm2")
    parser.add_argument("--repeats", type=int, default=50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    x, y = tile_xy(args.lon, args.lat, args.zoom)
    bounds = tile_bounds(args.zoom, x, y)
    collector = RoadCollector(bounds)
    collector.apply_file(args.input, locations=True)
    if not collector.features:
        raise SystemExit("هیچ road feature واقعی داخل tile انتخاب‌شده پیدا نشد")
    mvt = mapbox_vector_tile.encode(
        [{"name": "roads", "features": collector.features}],
        default_options={"quantize_bounds": bounds, "extents": 4096, "y_coord_down": False},
    )
    raw_chunk = build_chunk(mvt, args.zoom, x, y)
    compressed = zstd.ZstdCompressor(level=6).compress(raw_chunk)
    output = Path(args.output)
    record = write_container(output, compressed, raw_chunk, args.zoom, x, y)
    benchmark = measure_read(output, record["chunk_offset"], record["stored_bytes"], args.repeats)
    result = {
        "input": os.path.abspath(args.input),
        "tile": {"z": args.zoom, "x": x, "y": y, "bounds": bounds},
        "road_features": len(collector.features),
        "mvt_bytes": len(mvt),
        "container_bytes": output.stat().st_size,
        "chunk": record,
        "read_decompress": benchmark,
    }
    result_path = output.with_suffix(".benchmark.json")
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"benchmark={result_path}")


if __name__ == "__main__":
    main()
