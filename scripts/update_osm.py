#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, urllib.request
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--country', required=True)
    ap.add_argument('--region', default='')
    args = ap.parse_args()
    cfg = json.loads(Path('countries.json').read_text(encoding='utf-8'))[args.country.upper()]
    url = cfg['pbf_url']
    Path('source').mkdir(exist_ok=True)
    out = Path('source') / f"{args.country.upper()}.osm.pbf"
    req = urllib.request.Request(url, headers={'User-Agent': 'AbtinMaps-ABM-Builder/1'})
    with urllib.request.urlopen(req, timeout=120) as r:
        etag = r.headers.get('ETag', '')
        last_modified = r.headers.get('Last-Modified', '')
        total = int(r.headers.get('Content-Length', '0') or 0)
        with out.open('wb') as f:
            done = 0
            while True:
                block = r.read(8 * 1024 * 1024)
                if not block:
                    break
                f.write(block)
                done += len(block)
                if total:
                    print(f'OSM download: {done}/{total} bytes ({done/total:.1%})')
    Path('source/source-meta.json').write_text(json.dumps({
        'url': url, 'etag': etag, 'last_modified': last_modified, 'size': out.stat().st_size
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Downloaded {url} -> {out} ({out.stat().st_size} bytes)')

if __name__ == '__main__':
    main()
