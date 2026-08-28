#!/usr/bin/env python3
"""Verify an ABTINMAP one-file container without rendering it.

An .abm container is a standards-compliant PMTiles v3 archive whose PMTiles
metadata describes an appended routing graph and style resources. This verifier
checks the same contract that the mobile reader requires before a map is made
available for use.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

PMTILES_MAGIC = b"PMTiles"
PMTILES_VERSION = 3
PMTILES_HEADER_SIZE = 127
ABM_MAGIC = b"ABTINMAP"
REQUIRED_ENTRIES = {
    "styles/day.json",
    "styles/night.json",
    "sprites/abtin.json",
    "sprites/abtin.png",
    "sprites/abtin@2x.json",
    "sprites/abtin@2x.png",
    "glyphs/Vazirmatn/0-255.pbf",
    "glyphs/Vazirmatn/256-511.pbf",
    "glyphs/Vazirmatn/1536-1791.pbf",
    "glyphs/Vazirmatn/1792-2047.pbf",
    "glyphs/Vazirmatn/8192-8447.pbf",
    "glyphs/Vazirmatn/64256-64511.pbf",
    "glyphs/Vazirmatn/64512-64767.pbf",
    "glyphs/Vazirmatn/65024-65279.pbf",
    "glyphs/Vazirmatn/65280-65535.pbf",
}
STYLE_ENTRIES = {"styles/day.json", "styles/night.json"}


def fail(message: str) -> None:
    raise SystemExit(f"Invalid ABM container: {message}")


def read_exact(handle: Any, offset: int, length: int, label: str) -> bytes:
    handle.seek(offset)
    data = handle.read(length)
    if len(data) != length:
        fail(f"{label} is truncated")
    return data


def decode_internal(data: bytes, compression: int) -> bytes:
    if compression == 1:
        return data
    if compression == 2:
        return gzip.decompress(data)
    if compression == 3:
        try:
            import brotli
        except ImportError as exc:
            raise SystemExit("Brotli metadata requires the Python brotli package") from exc
        return brotli.decompress(data)
    if compression == 4:
        try:
            import zstandard
        except ImportError as exc:
            raise SystemExit("Zstandard metadata requires the Python zstandard package") from exc
        return zstandard.ZstdDecompressor().decompress(data)
    fail(f"unsupported PMTiles internal compression value {compression}")


def integer(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        fail(f"{label} must be a non-negative integer")
    return value


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_payload(
    handle: Any,
    file_size: int,
    value: object,
    label: str,
    expected_magic: bytes | None = None,
    expected_path: str | None = None,
) -> tuple[int, int]:
    if not isinstance(value, dict):
        fail(f"{label} is not an object")
    offset = integer(value.get("offset"), f"{label}.offset")
    length = integer(value.get("length"), f"{label}.length")
    expected_hash = value.get("sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        fail(f"{label}.sha256 is invalid")
    if offset > file_size or length > file_size - offset:
        fail(f"{label} range falls outside the archive")
    data = read_exact(handle, offset, length, label)
    if digest(data) != expected_hash.lower():
        fail(f"{label} checksum does not match metadata")
    if expected_magic is not None and not data.startswith(expected_magic):
        fail(f"{label} does not start with the expected magic")
    if expected_path is not None:
        try:
            style = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            fail(f"{label} is not valid UTF-8 JSON: {exc}")
        if not isinstance(style, dict) or "__ABTIN_PMTILES_URI__" not in data.decode("utf-8"):
            fail(f"{label} does not reference the embedded PMTiles source")
    return offset, length


def verify(path: Path, expected_region: str | None) -> dict[str, object]:
    if not path.is_file():
        fail(f"archive does not exist: {path}")
    file_size = path.stat().st_size
    if file_size < PMTILES_HEADER_SIZE:
        fail("archive is shorter than a PMTiles v3 header")

    with path.open("rb") as handle:
        header = read_exact(handle, 0, PMTILES_HEADER_SIZE, "PMTiles header")
        if header[:7] != PMTILES_MAGIC or header[7] != PMTILES_VERSION:
            fail("file is not a PMTiles v3 archive")
        root_offset, root_length = struct.unpack_from("<QQ", header, 8)
        metadata_offset, metadata_length = struct.unpack_from("<QQ", header, 24)
        leaf_offset, leaf_length = struct.unpack_from("<QQ", header, 40)
        tile_offset, tile_length = struct.unpack_from("<QQ", header, 56)
        ranges = (
            (root_offset, root_length, "root directory"),
            (metadata_offset, metadata_length, "metadata"),
            (leaf_offset, leaf_length, "leaf directories"),
            (tile_offset, tile_length, "tile data"),
        )
        for offset, length, label in ranges:
            if offset > file_size or length > file_size - offset:
                fail(f"PMTiles {label} range falls outside the archive")
        if metadata_offset + metadata_length != file_size:
            fail("metadata must be the final PMTiles section")

        try:
            raw_metadata = decode_internal(
                read_exact(handle, metadata_offset, metadata_length, "PMTiles metadata"),
                header[97],
            )
            metadata = json.loads(raw_metadata.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            fail(f"metadata cannot be decoded as JSON: {exc}")
        if not isinstance(metadata, dict):
            fail("PMTiles metadata is not a JSON object")
        container = metadata.get("abtin_container")
        if not isinstance(container, dict) or container.get("version") != 1:
            fail("abtin_container v1 metadata is missing")
        region = container.get("region")
        if (not isinstance(region, str) or
                not 2 <= len(region) <= 16 or
                region != region.upper() or
                not region.replace('-', '').isalnum()):
            fail("abtin_container region is invalid")
        if expected_region is not None and region != expected_region.upper():
            fail(f"region is {region}, expected {expected_region.upper()}")

        graph_offset, graph_length = verify_payload(
            handle,
            file_size,
            container.get("graph"),
            "graph",
            expected_magic=ABM_MAGIC,
        )
        entries = container.get("entries")
        if not isinstance(entries, list):
            fail("abtin_container entries is not a list")
        seen_paths: set[str] = set()
        payload_ranges = [(graph_offset, graph_length, "graph")]
        for entry in entries:
            if not isinstance(entry, dict):
                fail("a container entry is not an object")
            internal_path = entry.get("path")
            if not isinstance(internal_path, str) or not internal_path or internal_path.startswith("/") or ".." in internal_path.split("/"):
                fail("a container entry path is unsafe")
            if internal_path in seen_paths:
                fail(f"duplicate entry path: {internal_path}")
            seen_paths.add(internal_path)
            offset, length = verify_payload(
                handle,
                file_size,
                entry,
                f"entry {internal_path}",
                expected_path=internal_path if internal_path in STYLE_ENTRIES else None,
            )
            payload_ranges.append((offset, length, internal_path))

        missing = REQUIRED_ENTRIES - seen_paths
        if missing:
            fail(f"missing required entry: {', '.join(sorted(missing))}")
        tile_end = tile_offset + tile_length
        for offset, length, label in payload_ranges:
            if offset < tile_offset or offset + length > tile_end:
                fail(f"{label} is not inside declared PMTiles tile data")
        for index, (offset, length, label) in enumerate(payload_ranges):
            for other_offset, other_length, other_label in payload_ranges[index + 1 :]:
                if offset < other_offset + other_length and other_offset < offset + length:
                    fail(f"{label} overlaps {other_label}")

    return {
        "archive": str(path),
        "bytes": file_size,
        "region": region,
        "entries": sorted(seen_paths),
        "graph_bytes": graph_length,
        "sha256": file_digest(path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--region", help="Expected uppercase country or regional code, for example IR or US-WEST")
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, args.region), ensure_ascii=False))


if __name__ == "__main__":
    main()
