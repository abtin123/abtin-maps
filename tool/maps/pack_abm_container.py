#!/usr/bin/env python3
"""Pack one country map as one standard PMTiles v3 archive named `CC.abm`.

The archive contains only rendered vector tiles plus the routing graph and
search data. Rendering styles/resources are supplied by the app, so they are
not duplicated in every country download.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import struct
import tempfile
from dataclasses import dataclass
from pathlib import Path

PMTILES_MAGIC = b"PMTiles"
ABM_MAGIC = b"ABTINMAP"
HEADER_SIZE = 127

@dataclass(frozen=True)
class PmtilesParts:
    header: bytearray
    root_directory: bytes
    leaf_directories: bytes
    tile_data: bytes
    metadata: dict[str, object]
    internal_compression: int

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def safe_entry_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    if not normalized or normalized.startswith("/") or "../" in normalized or any(part in {"", "."} for part in normalized.split("/")):
        raise argparse.ArgumentTypeError(f"unsafe internal entry path: {value}")
    return normalized

def read_range(handle: object, offset: int, length: int, label: str) -> bytes:
    handle.seek(offset)
    value = handle.read(length)
    if len(value) != length:
        raise SystemExit(f"PMTiles {label} is truncated.")
    return value

def decode_internal(data: bytes, compression: int) -> bytes:
    if compression == 1: return data
    if compression == 2: return gzip.decompress(data)
    if compression == 3:
        import brotli
        return brotli.decompress(data)
    if compression == 4:
        import zstandard
        return zstandard.ZstdDecompressor().decompress(data)
    raise SystemExit(f"Unsupported PMTiles internal compression value: {compression}")

def encode_internal(data: bytes, compression: int) -> bytes:
    if compression == 1: return data
    if compression == 2: return gzip.compress(data, mtime=0)
    if compression == 3:
        import brotli
        return brotli.compress(data)
    if compression == 4:
        import zstandard
        return zstandard.ZstdCompressor(level=10).compress(data)
    raise SystemExit(f"Unsupported PMTiles internal compression value: {compression}")

def read_pmtiles(path: Path) -> PmtilesParts:
    if not path.is_file(): raise SystemExit(f"PMTiles archive does not exist: {path}")
    total = path.stat().st_size
    with path.open("rb") as handle:
        header = bytearray(read_range(handle, 0, HEADER_SIZE, "header"))
        if header[:7] != PMTILES_MAGIC or header[7] != 3:
            raise SystemExit(f"Input must be a valid PMTiles v3 archive: {path}")
        root_offset, root_length = struct.unpack_from("<QQ", header, 8)
        metadata_offset, metadata_length = struct.unpack_from("<QQ", header, 24)
        leaf_offset, leaf_length = struct.unpack_from("<QQ", header, 40)
        tile_offset, tile_length = struct.unpack_from("<QQ", header, 56)
        for offset, length, label in ((root_offset, root_length, "root directory"), (metadata_offset, metadata_length, "metadata"), (leaf_offset, leaf_length, "leaf directories"), (tile_offset, tile_length, "tile data")):
            if offset > total or length > total - offset: raise SystemExit(f"PMTiles {label} range is outside the input archive.")
        internal_compression = header[97]
        metadata_bytes_value = decode_internal(read_range(handle, metadata_offset, metadata_length, "metadata"), internal_compression)
        metadata = json.loads(metadata_bytes_value.decode("utf-8"))
        if not isinstance(metadata, dict): raise SystemExit("PMTiles metadata must be a JSON object.")
        return PmtilesParts(header, read_range(handle, root_offset, root_length, "root directory"), read_range(handle, leaf_offset, leaf_length, "leaf directories"), read_range(handle, tile_offset, tile_length, "tile data"), metadata, internal_compression)

def metadata_bytes(value: dict[str, object]) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")

def build_container(args: argparse.Namespace) -> None:
    parts = read_pmtiles(args.pmtiles)
    if not args.graph.is_file() or args.graph.read_bytes()[:8] != ABM_MAGIC: raise SystemExit(f"Graph must be a valid ABTINMAP segment: {args.graph}")
    if not args.search_index.is_file(): raise SystemExit(f"Search index is missing: {args.search_index}")
    entry_sources: list[tuple[str, Path]] = [("search/places.sqlite", args.search_index)]
    for path, source in entry_sources:
        if not source.is_file(): raise SystemExit(f"Container entry is missing: {path} -> {source}")
    payloads = [("graph", args.graph.read_bytes())] + [(path, source.read_bytes()) for path, source in entry_sources]
    root_offset = HEADER_SIZE
    leaf_offset = root_offset + len(parts.root_directory)
    tile_offset = leaf_offset + len(parts.leaf_directories)
    cursor = tile_offset + len(parts.tile_data)
    graph_info: dict[str, object] | None = None
    entries: list[dict[str, object]] = []
    for name, payload in payloads:
        item = {"offset": cursor, "length": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        if name == "graph": graph_info = item
        else: entries.append({"path": name, **item})
        cursor += len(payload)
    total_tile_data = cursor - tile_offset
    metadata = dict(parts.metadata)
    metadata["abtin_container"] = {
        "version": 2,
        "region": args.region.upper(),
        "contracts": {"pmtiles_minzoom": 2, "pmtiles_maxzoom": 16, "app_overzoom_maxzoom": 20, "offline_search": "search/places.sqlite", "rendered_pois": False, "styles": "app_bundled"},
        "graph": graph_info,
        "entries": entries,
    }
    encoded_metadata = encode_internal(metadata_bytes(metadata), parts.internal_compression)
    metadata_offset = tile_offset + total_tile_data
    header = bytearray(parts.header)
    struct.pack_into("<QQ", header, 8, root_offset, len(parts.root_directory))
    struct.pack_into("<QQ", header, 24, metadata_offset, len(encoded_metadata))
    struct.pack_into("<QQ", header, 40, leaf_offset, len(parts.leaf_directories))
    struct.pack_into("<QQ", header, 56, tile_offset, total_tile_data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{args.output.name}.", suffix=".part", dir=args.output.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(header); output.write(parts.root_directory); output.write(parts.leaf_directories); output.write(parts.tile_data)
            for _, payload in payloads: output.write(payload)
            output.write(encoded_metadata); output.flush(); os.fsync(output.fileno())
        os.replace(temporary_name, args.output)
    finally:
        if os.path.exists(temporary_name): os.unlink(temporary_name)
    print(json.dumps({"container": str(args.output), "bytes": args.output.stat().st_size, "sha256": sha256(args.output), "pmtiles_payload_bytes": len(parts.tile_data), "graph_payload_bytes": args.graph.stat().st_size}, ensure_ascii=False))

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True); parser.add_argument("--pmtiles", type=Path, required=True); parser.add_argument("--graph", type=Path, required=True); parser.add_argument("--search-index", type=Path, required=True)
    # Kept as compatibility arguments for existing CI invocations. They are no longer embedded.
    parser.add_argument("--day-style", type=Path, required=True); parser.add_argument("--night-style", type=Path, required=True)
    parser.add_argument("--resource", action="append", default=[], help="Deprecated: resources are app-bundled and are not embedded.")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()

if __name__ == "__main__": build_container(parse_args())
