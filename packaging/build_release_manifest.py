#!/usr/bin/env python3
"""Assemble the single release-level manifest.json that the Abtin Maps app
downloads and parses (MapCatalogService / MapRegion.fromJson in
lib/features/offline_maps/data/map_catalog.dart).

This is the missing link between the three things the rest of this builder
already produces per country/region:

  dist/CC.abm                 - from build_abm.py (whole country or one region)
  dist/CC-parts/manifest.json - from packaging/split_abm.py (only for archives
                                 over the ~1.8 GiB hosting cap; real byte chunks,
                                 NOT geography - see build_abm.py --regions for
                                 an actual geographic split)
  dist/CC-patch/patch-descriptor.json - from packaging/create_patch.py (only
                                 when a previous release of the same code exists)

Nothing before this script ever emitted the single `countries: [...]`
manifest.json the app fetches from the GitHub release, so previously the
app had no supported way to discover what's downloadable at all. This
script scans a `dist/` directory built by the pipeline above and writes
that manifest.

Country display names (name_fa/name_en, used for entries that are NOT a
geographic region - see build_abm.py --regions for those, which already
carry their own names in metadata.json) come from a small --names JSON
file: {"IR": {"name_fa": "ایران", "name_en": "Iran"}, ...}. A code missing
from that file falls back to using the code itself as its name, so the
build never fails silently - it just produces an ugly (and easy to spot)
entry.

Deliberately NOT emitted: any `vector_map` / PMTiles field. Older releases
of this app expected `.abm` to be a PMTiles v3 container with extra data
appended; that is no longer true (see metadata.json "version": 2 and
"tiles": false; ABM_DIR is pure vector/poi/search/routing, see build_abm.py).
The app itself still needs a matching update - it currently assumes the
old container shape - see the accompanying app-fix instructions.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, zipfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read_abm_metadata(abm_path: Path) -> dict:
    with zipfile.ZipFile(abm_path) as z:
        return json.loads(z.read('metadata.json'))


def build_entry(code: str, dist: Path, names: dict) -> dict | None:
    abm_path = dist / f'{code}.abm'
    if not abm_path.exists():
        return None
    meta = read_abm_metadata(abm_path)
    bbox = meta.get('bbox')
    if not bbox:
        raise SystemExit(f'{abm_path} has no bbox in metadata.json - rebuild with the current build_abm.py')
    region = meta.get('region')

    parts_dir = dist / f'{code}-parts'
    parts_manifest = parts_dir / 'manifest.json'
    if parts_manifest.exists():
        parts_data = json.loads(parts_manifest.read_text(encoding='utf-8'))
        files = [{'name': p['name'], 'size': p['size'], 'sha256': p['sha256']} for p in parts_data['parts']]
        total_size = parts_data['size']
        whole_file_sha256 = parts_data['sha256']
    else:
        files = [{'name': abm_path.name, 'size': abm_path.stat().st_size, 'sha256': sha256_file(abm_path)}]
        total_size = abm_path.stat().st_size
        whole_file_sha256 = files[0]['sha256']

    patch_descriptor_path = dist / f'{code}-patch' / 'patch-descriptor.json'
    patch = None
    if patch_descriptor_path.exists():
        pd = json.loads(patch_descriptor_path.read_text(encoding='utf-8'))
        patch = {
            'base_sha256': pd['base_sha256'],
            'manifest_file': pd['manifest_file'],
            'bin_file': pd['bin_file'],
            'size': pd['size'],
            'sha256': pd['sha256'],
        }

    if region is not None:
        entry = {
            'code': code,
            'name_fa': region['name_fa'],
            'name_en': region['name_en'],
            'country_code': region['country_code'],
            'country_name_fa': region.get('country_name_fa', ''),
            'country_name_en': region.get('country_name_en', ''),
            'region_name_fa': region['name_fa'],
            'region_name_en': region['name_en'],
        }
    else:
        display = names.get(code, {})
        name_fa = display.get('name_fa', code)
        name_en = display.get('name_en', code)
        entry = {
            'code': code,
            'name_fa': name_fa,
            'name_en': name_en,
            'country_code': code,
            'country_name_fa': name_fa,
            'country_name_en': name_en,
            'region_name_fa': name_fa,
            'region_name_en': name_en,
        }

    entry.update({
        'bbox': list(bbox),
        'sha256': whole_file_sha256,
        'files': files,
        'total_size': total_size,
        'source': {
            'provider': 'Geofabrik / OpenStreetMap',
            'url': names.get(code, {}).get('pbf_url', ''),
            'attribution': 'Map data from OpenStreetMap, ODbL 1.0',
            'license_url': 'https://opendatacommons.org/licenses/odbl/1.0/',
            'copyright_url': 'https://www.openstreetmap.org/copyright',
        },
    })
    if patch is not None:
        entry['patch'] = patch
    return entry


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('dist', type=Path, help='Directory containing built CC.abm / CC-parts / CC-patch trees')
    ap.add_argument('--release-tag', required=True)
    ap.add_argument('--names', type=Path, default=None,
                     help='JSON file of {"CODE": {"name_fa": "...", "name_en": "..."}} '
                          'for whole-country (non-region) entries')
    ap.add_argument('-o', '--output', type=Path, required=True)
    args = ap.parse_args()

    names = json.loads(args.names.read_text(encoding='utf-8')) if args.names else {}
    codes = sorted(p.stem for p in args.dist.glob('*.abm'))
    if not codes:
        raise SystemExit(f'No .abm files found directly under {args.dist}')

    countries = []
    for code in codes:
        entry = build_entry(code, args.dist, names)
        if entry:
            countries.append(entry)

    manifest = {
        'release_tag': args.release_tag,
        'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'countries': countries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {args.output} with {len(countries)} entries')


if __name__ == '__main__':
    main()
