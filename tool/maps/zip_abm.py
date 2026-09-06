#!/usr/bin/env python3
"""Create a deterministic maximum-compression ZIP distribution of one ABM."""
from __future__ import annotations
import argparse, hashlib, os, tempfile, zipfile
from pathlib import Path

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if not a.input.is_file():
        raise SystemExit(f"ABM not found: {a.input}")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="." + a.output.name + ".", suffix=".part", dir=a.output.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as z:
            info = zipfile.ZipInfo(a.input.name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            with a.input.open("rb") as src, z.open(info, "w", force_zip64=True) as dst:
                for chunk in iter(lambda: src.read(8 * 1024 * 1024), b""):
                    dst.write(chunk)
        os.replace(tmp, a.output)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    raw = a.input.stat().st_size
    packed = a.output.stat().st_size
    print(f"Compressed {a.input.name}: {raw} -> {packed} bytes ({packed / raw * 100:.1f}%)")
    print(f"SHA256 ABM: {sha256(a.input)}")
    print(f"SHA256 ZIP: {sha256(a.output)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
