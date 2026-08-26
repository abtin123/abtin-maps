#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Store ETag/Last-Modified metadata for countries successfully published."""
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
    except Exception as error:  # network errors must not overwrite a valid state
        return code, None, str(error)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--countries', type=Path, default=Path('tools/countries.json'))
    parser.add_argument('--state', type=Path, default=Path('tools/osm_source_state.json'))
    parser.add_argument('--codes', required=True, help='Comma-separated country codes published in this run')
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()

    requested = {item.strip().upper() for item in args.codes.split(',') if item.strip()}
    if not requested:
        raise SystemExit('حداقل یک کد کشور لازم است')
    countries = json.loads(args.countries.read_text(encoding='utf-8'))['countries']
    by_code = {str(item['code']).upper(): item for item in countries}
    missing = sorted(requested - by_code.keys())
    if missing:
        raise SystemExit(f'کد ناشناخته: {", ".join(missing)}')

    try:
        state = json.loads(args.state.read_text(encoding='utf-8'))
    except FileNotFoundError:
        state = {}

    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, len(requested)))) as pool:
        futures = [pool.submit(probe, code, by_code[code]['pbf_url']) for code in sorted(requested)]
        for future in as_completed(futures):
            code, metadata, error = future.result()
            if metadata is None:
                failures.append(f'{code}: {error}')
                continue
            state[code] = metadata
            print(f'{code}: fingerprint ثبت شد')

    args.state.parent.mkdir(parents=True, exist_ok=True)
    args.state.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if failures:
        for failure in failures:
            print(f'::warning::{failure}', file=sys.stderr)
        raise SystemExit('ثبت fingerprint همهٔ منابع موفق نبود؛ state موجود حفظ شد.')


if __name__ == '__main__':
    main()
