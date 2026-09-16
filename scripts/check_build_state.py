#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess, tempfile, urllib.request
from pathlib import Path


def gh(*args, check=True):
    return subprocess.run(['gh', *args], text=True, capture_output=True, check=check)


def latest_release_tag():
    r = gh('release', 'list', '--limit', '20', '--json', 'tagName,isDraft,isPrerelease,createdAt')
    rows = json.loads(r.stdout or '[]')
    rows = [x for x in rows if not x.get('isDraft') and not x.get('isPrerelease')]
    rows.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
    return rows[0]['tagName'] if rows else ''


def download_manifest(tag: str, dest: Path) -> dict:
    if not tag:
        return {}
    r = gh('release', 'download', tag, '--pattern', 'manifest.json', '--dir', str(dest), '--clobber', check=False)
    if r.returncode != 0 or not (dest / 'manifest.json').exists():
        return {}
    try:
        return json.loads((dest / 'manifest.json').read_text(encoding='utf-8'))
    except Exception:
        return {}


def remote_meta(url: str) -> dict:
    req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'AbtinMaps-ABM-Builder/1'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return {
                'etag': (r.headers.get('ETag') or '').strip(),
                'last_modified': (r.headers.get('Last-Modified') or '').strip(),
                'content_length': (r.headers.get('Content-Length') or '').strip(),
            }
    except Exception as e:
        return {'error': str(e)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--country', required=True)
    ap.add_argument('--region', default='')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()

    code = args.country.upper()
    countries = json.loads(Path('countries.json').read_text(encoding='utf-8'))
    cfg = countries[code]
    url = cfg['pbf_url']
    tag = latest_release_tag()

    with tempfile.TemporaryDirectory() as td:
        manifest = download_manifest(tag, Path(td))
    entries = manifest.get('countries', []) if isinstance(manifest, dict) else []

    if args.region == '__regions__':
        current = [e for e in entries if e.get('country_code') == code and e.get('code', '').startswith(code + '-')]
        # All configured regions must exist in the previous release.
        region_cfg = json.loads(Path(cfg['regions_config']).read_text(encoding='utf-8'))
        expected = {r['code'] for r in region_cfg.get('regions', [])}
        found = {e.get('code') for e in current}
        previous_entries = current
        has_previous = expected <= found and bool(expected)
    else:
        asset_code = args.region if args.region else code
        previous_entries = [e for e in entries if e.get('code') == asset_code]
        has_previous = bool(previous_entries)

    old_meta = (previous_entries[0].get('source', {}).get('http', {}) if previous_entries else {})
    meta = remote_meta(url)
    if meta.get('etag') and old_meta.get('etag'):
        remote_changed = meta['etag'] != old_meta['etag']
    elif meta.get('last_modified') and old_meta.get('last_modified'):
        remote_changed = meta['last_modified'] != old_meta['last_modified']
    else:
        # Old releases without HTTP source metadata are rebuilt once.
        remote_changed = not bool(old_meta)

    force = os.environ.get('FORCE_BUILD', '').lower() == 'true'
    needs_build = force or not has_previous or remote_changed
    state = {
        'needs_build': needs_build,
        'needs_delta': has_previous and needs_build,
        'previous_release_tag': tag,
        'previous_codes': sorted(e.get('code') for e in previous_entries if e.get('code')),
        'pbf_url': url,
        'remote': meta,
        'previous_source': old_meta,
    }
    args.output.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    out_path = Path(os.environ.get('GITHUB_OUTPUT', '/dev/null'))
    with out_path.open('a', encoding='utf-8') as out:
        out.write(f"needs_build={'true' if needs_build else 'false'}\n")
        out.write(f"needs_delta={'true' if state['needs_delta'] else 'false'}\n")
        out.write(f"previous_release_tag={tag}\n")
    print(json.dumps(state, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
