#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from packaging.create_abm import verify_abm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--country', required=True)
    ap.add_argument('--region', default='')
    ap.add_argument('--output-dir', type=Path, default=Path('release'))
    args = ap.parse_args()
    dist = args.output_dir
    if args.region == '__regions__':
        paths = sorted(dist.glob(f'{args.country.upper()}-*.abm'))
    elif args.region:
        paths = [dist / f'{args.region}.abm']
    else:
        paths = [dist / f'{args.country.upper()}.abm']
    if not paths or not all(p.exists() for p in paths):
        raise SystemExit(f'No expected ABM output found: {paths}')
    for p in paths:
        result = verify_abm(p)
        print(f'VALID {p}: {result["files"]} files, routing={result["metadata"].get("routing")}, bbox={result["metadata"].get("bbox")}')

if __name__ == '__main__':
    main()
