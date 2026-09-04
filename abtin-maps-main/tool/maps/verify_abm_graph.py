#!/usr/bin/env python3
"""Validate an ABTINMAP v2 graph segment created by build_abm_graph.py."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

import zstandard

MAGIC = b"ABTINMAP"
HEADER_SIZE = 128


def uvarint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if offset >= len(data) or shift > 63:
            raise ValueError("invalid uvarint")
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, offset
        shift += 7


def read_exact(handle: object, offset: int, length: int, label: str) -> bytes:
    handle.seek(offset)
    result = handle.read(length)
    if len(result) != length:
        raise ValueError(f"truncated {label}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("graph", type=Path)
    args = parser.parse_args()
    file_size = args.graph.stat().st_size
    if file_size < HEADER_SIZE:
        raise SystemExit("graph is shorter than ABM header")
    with args.graph.open("rb") as handle:
        header = read_exact(handle, 0, HEADER_SIZE, "header")
        if header[:8] != MAGIC:
            raise SystemExit("graph magic is not ABTINMAP")
        version = struct.unpack_from("<H", header, 8)[0]
        zoom = header[12]
        tile_count = struct.unpack_from("<I", header, 36)[0]
        index_offset = struct.unpack_from("<Q", header, 40)[0]
        index_comp = struct.unpack_from("<I", header, 48)[0]
        index_raw = struct.unpack_from("<I", header, 52)[0]
        strings_offset = struct.unpack_from("<Q", header, 56)[0]
        strings_comp = struct.unpack_from("<I", header, 64)[0]
        strings_raw = struct.unpack_from("<I", header, 68)[0]
        if version < 2 or not (5 <= zoom <= 14) or tile_count == 0:
            raise SystemExit("graph header version, zoom, or tile count is invalid")
        for offset, length, label in (
            (index_offset, index_comp, "index"),
            (strings_offset, strings_comp, "strings"),
        ):
            if offset > file_size or length > file_size - offset:
                raise SystemExit(f"{label} range is outside graph")
        decoder = zstandard.ZstdDecompressor()
        index = decoder.decompress(read_exact(handle, index_offset, index_comp, "index"), max_output_size=index_raw)
        strings = decoder.decompress(read_exact(handle, strings_offset, strings_comp, "strings"), max_output_size=strings_raw)
        if len(index) != index_raw or len(strings) != strings_raw:
            raise SystemExit("zstd uncompressed length does not match ABM header")
        string_count, string_offset = uvarint(strings, 0)
        for _ in range(string_count):
            length, string_offset = uvarint(strings, string_offset)
            string_offset += length
            if string_offset > len(strings):
                raise SystemExit("string table is truncated")
        if string_count != struct.unpack_from("<I", header, 72)[0]:
            raise SystemExit("string count does not match ABM header")
        cursor = 0
        previous_tile = 0
        previous_end = 0
        for _ in range(tile_count):
            tile_delta, cursor = uvarint(index, cursor)
            delta_offset, cursor = uvarint(index, cursor)
            compressed_length, cursor = uvarint(index, cursor)
            raw_length, cursor = uvarint(index, cursor)
            _, cursor = uvarint(index, cursor)
            current_tile = previous_tile + tile_delta
            absolute_offset = previous_end + delta_offset
            if current_tile <= previous_tile or absolute_offset > file_size or compressed_length > file_size - absolute_offset or raw_length == 0:
                raise SystemExit("ABM tile index is invalid")
            previous_tile = current_tile
            previous_end = absolute_offset + compressed_length
    print(
        f"Graph verified: {args.graph} | version={version} | zoom={zoom} | "
        f"tiles={tile_count} | strings={string_count}"
    )


if __name__ == "__main__":
    main()
