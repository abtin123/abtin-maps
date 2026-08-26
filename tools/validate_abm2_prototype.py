"""اعتبارسنجی ساختاری container تک-tile prototype ABM2."""

import argparse
import struct
from pathlib import Path

import zstandard as zstd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    args = parser.parse_args()
    raw = Path(args.input).read_bytes()
    if len(raw) < 4352:
        raise SystemExit("container کوتاه‌تر از header + index است")
    if raw[:8] != b"ABTIN2\0\0":
        raise SystemExit("magic ABTIN2 معتبر نیست")
    major, minor, header_size = struct.unpack_from("<HHI", raw, 8)
    if (major, minor, header_size) != (2, 0, 256):
        raise SystemExit(f"header ناسازگار: major={major} minor={minor} bytes={header_size}")
    if raw[256:260] != b"IDX2":
        raise SystemExit("index IDX2 پیدا نشد")
    count = struct.unpack_from("<I", raw, 264)[0]
    if count != 1:
        raise SystemExit(f"prototype باید دقیقاً یک index entry داشته باشد: {count}")
    entry = struct.unpack_from("<QIHHQIIIQI", raw, 272)
    tile_key, layer_mask, _flags, _features, offset, stored, raw_bytes, _crc, _hash, _revision = entry
    if layer_mask != 1 or offset + stored > len(raw):
        raise SystemExit("index entry به chunk معتبر اشاره نمی‌کند")
    chunk = zstd.ZstdDecompressor().decompress(raw[offset:offset + stored])
    if len(chunk) != raw_bytes or chunk[:4] != b"VCH2":
        raise SystemExit("chunk VCH2 یا اندازهٔ decompressed معتبر نیست")
    chunk_key = struct.unpack_from("<Q", chunk, 8)[0]
    if chunk_key != tile_key:
        raise SystemExit("tile_key index و chunk یکسان نیست")
    print(f"PASS ABM2 prototype: tile_key={tile_key} stored={stored} raw={raw_bytes}")


if __name__ == "__main__":
    main()
