#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    countries = json.loads(Path('countries.json').read_text(encoding='utf-8'))
    target = args.target.strip().upper()
    if target == 'ALL':
        codes = sorted(countries)
    elif target.startswith('ALL/'):
        codes = [target.split('/', 1)[1]]
    else:
        codes = [target]
    missing = [c for c in codes if c not in countries]
    if missing:
        raise SystemExit(f'Unknown country code(s): {", ".join(missing)}')
    matrix = []
    for code in codes:
        cfg = countries[code]
        matrix.append({
            'country': code,
            # Empty region means whole-country build. For a geographically
            # split country (currently US), the single matrix job builds all
            # configured regions so one country does not consume 5 runner jobs.
            'region': '__regions__' if cfg.get('regions_config') else '',
            'regions_config': cfg.get('regions_config', ''),
            'name_en': cfg.get('name_en', code),
        })
    args.output.write_text(json.dumps(matrix, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(args.output.read_text())

if __name__ == '__main__':
    main()
