"""Split a release manifest into per-country fragments for merge_manifests.py."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--out-dir', required=True, type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.input.read_text(encoding='utf-8'))
    countries = manifest.get('countries', [])
    if not isinstance(countries, list):
        raise SystemExit('manifest.countries باید یک list باشد')

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for country in countries:
        code = str(country.get('code', '')).strip().upper()
        if not code:
            raise SystemExit('یک country در manifest فاقد code است')
        target = args.out_dir / f'manifest-{code}.json'
        target.write_text(
            json.dumps(country, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )

    print(f'{len(countries)} manifest fragment written to {args.out_dir}')


if __name__ == '__main__':
    main()
