#!/usr/bin/env python3
"""Build an ABM with the project's ABM Builder and stage it as an app asset.

Usage:
  python tool/build_bundled_abm.py input.osm.pbf --country IR
  python tool/build_bundled_abm.py sample/us_mini.jsonl --country US
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tool" / "abm_builder"
ASSETS = ROOT / "assets" / "maps"

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--country", required=True)
    ap.add_argument("--regions", type=Path)
    args = ap.parse_args()

    ASSETS.mkdir(parents=True, exist_ok=True)
    out = ASSETS / f"{args.country.upper()}.abm"
    cmd = [sys.executable, str(BUILDER / "build_abm.py"), str(args.input),
           "--country", args.country.upper(), "--output", str(out)]
    if args.regions:
        cmd += ["--regions", str(args.regions)]
    subprocess.run(cmd, cwd=ROOT, check=True)

    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    manifest = {"schema": 1, "maps": [{
        "id": args.country.upper(),
        "asset": f"assets/maps/{out.name}",
        "version": digest,
    }]}
    (ASSETS / "bundled_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Bundled ABM: {out}")
    print(f"SHA-256: {digest}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
