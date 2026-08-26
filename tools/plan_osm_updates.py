"""Plan initial and weekly map builds without rebuilding an unchanged country.

Inputs:
* the full Geofabrik country catalog;
* the current maps-v3 manifest (countries already published);
* persisted OSM source fingerprints (ETag + Last-Modified).

Outputs are comma-separated batches with at most 15 countries each, which keeps the
16-stage renderer matrix under GitHub's 256-job workflow limit.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path


def probe(code: str, url: str) -> tuple[str, dict[str, str] | None, str | None]:
    request = urllib.request.Request(url, method='HEAD')
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            last_modified = response.headers.get('Last-Modified') or ''
            try:
                last_modified = parsedate_to_datetime(last_modified).isoformat() if last_modified else ''
            except (TypeError, ValueError):
                pass
            return code, {
                'url': url,
                'etag': response.headers.get('ETag') or '',
                'last_modified': last_modified,
                'checked_at': datetime.now(timezone.utc).isoformat(),
            }, None
    except Exception as error:
        return code, None, str(error)


def fingerprint_changed(previous: dict[str, str], current: dict[str, str]) -> bool:
    previous_etag = previous.get('etag') or ''
    current_etag = current.get('etag') or ''
    if previous_etag and current_etag:
        return previous_etag != current_etag
    previous_lm = previous.get('last_modified') or ''
    current_lm = current.get('last_modified') or ''
    return bool(previous_lm and current_lm and previous_lm != current_lm)


def write_batches(path: Path, codes: list[str], size: int) -> None:
    batches = [','.join(codes[index:index + size]) for index in range(0, len(codes), size)]
    path.write_text('\n'.join(batches) + ('\n' if batches else ''), encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--countries', type=Path, default=Path('tools/countries.json'))
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--state', type=Path, default=Path('tools/osm_source_state.json'))
    parser.add_argument('--out-missing-batches', type=Path, required=True)
    parser.add_argument('--out-changed-batches', type=Path, required=True)
    parser.add_argument('--out-state', type=Path, required=True)
    parser.add_argument('--batch-size', type=int, default=15)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 15:
        raise SystemExit('batch-size باید بین 1 و 15 باشد')

    catalog = json.loads(args.countries.read_text(encoding='utf-8'))['countries']
    countries = {str(item['code']).upper(): item for item in catalog}
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    published = {str(item.get('code', '')).upper() for item in manifest.get('countries', [])}
    published.discard('')
    try:
        state = json.loads(args.state.read_text(encoding='utf-8'))
    except FileNotFoundError:
        state = {}

    fresh: dict[str, dict[str, str]] = {}
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, len(countries)))) as pool:
        futures = [pool.submit(probe, code, item['pbf_url']) for code, item in countries.items()]
        for future in as_completed(futures):
            code, metadata, error = future.result()
            if metadata is None:
                failures.append(f'{code}: {error}')
            else:
                fresh[code] = metadata

    missing = sorted(set(countries) - published)
    changed: list[str] = []
    next_state = dict(state)
    for code in sorted(published & set(countries)):
        current = fresh.get(code)
        previous = state.get(code)
        if current is None:
            continue  # unknown must never trigger an expensive rebuild
        if previous is None:
            next_state[code] = current
        elif fingerprint_changed(previous, current):
            changed.append(code)

    write_batches(args.out_missing_batches, missing, args.batch_size)
    write_batches(args.out_changed_batches, changed, args.batch_size)
    args.out_state.parent.mkdir(parents=True, exist_ok=True)
    args.out_state.write_text(json.dumps(next_state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    print(f'published={len(published)} missing={len(missing)} changed={len(changed)} baseline={len(next_state)}')
    if failures:
        print(f'::warning::{len(failures)} HEAD requests failed; existing countries were not rebuilt blindly.', file=sys.stderr)


if __name__ == '__main__':
    main()
