#!/usr/bin/env python3
"""Merge independent map chunk outputs into one release directory."""
from __future__ import annotations
import argparse, json, shutil
from pathlib import Path

MAX_RELEASE_ASSET_BYTES = 2 * 1024**3

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--previous', type=Path)
    parser.add_argument('--release-tag', required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    entries = {}
    if args.previous and args.previous.is_file():
        data = json.loads(args.previous.read_text(encoding='utf-8'))
        for item in data.get('countries', []):
            if isinstance(item, dict) and item.get('code'):
                entries[str(item['code']).upper()] = item
    successes, failures = [], []
    for report_path in sorted(args.input_root.glob('*/build-report.json')):
        report = json.loads(report_path.read_text(encoding='utf-8'))
        successes.extend(report.get('successes', []))
        failures.extend(report.get('failures', []))
    for manifest_path in sorted(args.input_root.glob('*/manifest.json')):
        data = json.loads(manifest_path.read_text(encoding='utf-8'))
        for item in data.get('countries', []):
            if not isinstance(item, dict) or not item.get('code'):
                continue
            code = str(item['code']).upper()
            archive = args.input_root / manifest_path.parent.name / f'{code}.abm'
            # New files produced by a chunk override an older entry. Existing
            # files remain represented by the previous release manifest.
            if archive.is_file():
                if archive.stat().st_size >= MAX_RELEASE_ASSET_BYTES:
                    failures.append({'code': code, 'error': 'archive is at or above GitHub 2 GiB release-asset limit'})
                    continue
                shutil.copy2(archive, args.output / archive.name)
                entries[code] = item
    if len(entries) > 998:
        raise SystemExit(f'Release would exceed 1000 assets: {len(entries)} map entries plus manifest/report')
    manifest = {'schema_version': 4, 'release_tag': args.release_tag, 'countries': [entries[k] for k in sorted(entries)]}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report = {'release_tag': args.release_tag, 'success_count': len(successes), 'failure_count': len(failures), 'successes': successes, 'failures': failures}
    (args.output / 'build-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Merged map chunks: countries={len(entries)} successes={len(successes)} failures={len(failures)}')
    return 0

if __name__ == '__main__': raise SystemExit(main())
