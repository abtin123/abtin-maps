#!/usr/bin/env python3
"""Per-archive release prep, run right after build_abm.py:

  * fetch the previously published CODE from the release (whole file, or its parts)
  * create patches old -> new and keep the smallest one, only if it is clearly smaller than the
    full file:
      - logical patch (row-level, ABTINMAP-LOGICAL-PATCH/1): ships only changed rows/tiles; apps
        that do not know it ignore it and download the full file
      - chunk patch (byte-level, ABTINMAP-CHUNK-PATCH/1|2): kept for already shipped apps
  * split the archive into byte parts when it exceeds the release asset cap
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from release_packaging.create_patch import create_patch, member_report, sha256  # noqa: E402
from release_packaging.logical_patch import apply_logical_patch, create_logical_patch  # noqa: E402
from release_packaging.split_abm import split_file  # noqa: E402

# A patch is only published when it is clearly smaller than the full archive. At 0.8-0.9 the
# client downloads almost the whole file anyway but also needs the old file, an extra
# apply/verify step and extra release assets; the full file is the better deal there.
PATCH_MAX_RATIO = 0.6


def fetch_previous(code: str, prev_manifest: Path, tag: str, work: Path) -> Path | None:
    if not prev_manifest.exists():
        return None
    entry = next((c for c in json.loads(prev_manifest.read_text(encoding='utf-8')).get('countries', [])
                  if c.get('code') == code), None)
    if not entry or not entry.get('files') or not entry.get('sha256'):
        return None
    work.mkdir(parents=True, exist_ok=True)
    base = work / f'{code}.base'
    try:
        with base.open('wb') as out:
            for f in entry['files']:
                subprocess.run(['gh', 'release', 'download', tag, '--pattern', f['name'],
                                '--dir', str(work), '--clobber'], check=True)
                part = work / f['name']
                with part.open('rb') as src:
                    shutil.copyfileobj(src, out, 1024 * 1024)
                part.unlink()
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f'{code}: previous release not downloadable ({exc}); no patch')
        base.unlink(missing_ok=True)
        return None
    if sha256(base) != entry['sha256']:
        print(f'{code}: downloaded base does not match published sha256; no patch')
        base.unlink(missing_ok=True)
        return None
    return base


def build_candidates(base: Path, abm: Path, code: str, work: Path) -> list[tuple[int, str, Path]]:
    """Create every patch flavour into ``work/<kind>`` -> [(size, kind, dir)], smallest first."""
    found = []
    for kind, make in (('logical', create_logical_patch), ('chunk', create_patch)):
        out = work / kind
        try:
            manifest_path, patch = make(base, abm, code, out)
            if kind == 'logical':
                # never publish a logical patch that this very builder cannot replay: the reference
                # apply checks the SHA-256 of the resolved content against the target's
                verified = work / 'verify' / f'{code}.abm'
                verified.parent.mkdir(parents=True, exist_ok=True)
                apply_logical_patch(base, json.loads(manifest_path.read_text(encoding='utf-8')),
                                    patch, verified)
                shutil.rmtree(verified.parent, ignore_errors=True)
        except Exception as exc:  # noqa: BLE001 - a failed flavour must not fail the release
            print(f'{code}: {kind} patch not usable ({type(exc).__name__}: {exc})')
            shutil.rmtree(out, ignore_errors=True)
            continue
        found.append((patch.stat().st_size, kind, out))
    return sorted(found)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('code')
    ap.add_argument('--dist', type=Path, required=True)
    ap.add_argument('--previous-manifest', type=Path, required=True)
    ap.add_argument('--release-tag', required=True)
    ap.add_argument('--patch-max-ratio', type=float, default=PATCH_MAX_RATIO,
                    help='publish a patch only if patch_size < ratio * full_size (default %(default)s)')
    ap.add_argument('--max-asset-bytes', type=int, default=int(1.8 * 1024 ** 3))
    ap.add_argument('--work', type=Path, default=Path('base-work'))
    args = ap.parse_args()

    abm = args.dist / f'{args.code}.abm'
    size = abm.stat().st_size

    base = fetch_previous(args.code, args.previous_manifest, args.release_tag, args.work)
    if base is not None:
        if sha256(base) == sha256(abm):
            print(f'{args.code}: unchanged since last release; no patch')
        else:
            out = args.dist / f'{args.code}-patch'
            work = args.work / f'{args.code}-candidates'
            shutil.rmtree(work, ignore_errors=True)
            candidates = build_candidates(base, abm, args.code, work)
            detail = ', '.join(f"{m['name']}: {m['reused_ratio']:.0%} byte-reused"
                               for m in member_report(base, abm) if m['size'] >= 1024 * 1024)
            summary = ', '.join(f'{k}={sz} B ({sz / size:.0%})' for sz, k, _ in candidates) or 'none'
            if not candidates or candidates[0][0] / size >= args.patch_max_ratio:
                print(f'{args.code}: best patch not below {args.patch_max_ratio:.0%} of full {size} B '
                      f'[{summary}] [{detail}]; dropped, clients get the full file')
            else:
                psize, kind, src = candidates[0]
                shutil.rmtree(out, ignore_errors=True)
                shutil.move(str(src), str(out))
                print(f'{args.code}: publishing {kind} patch {psize} B = {psize / size:.0%} of full '
                      f'{size} B [{summary}] [{detail}]')
            shutil.rmtree(work, ignore_errors=True)
        base.unlink(missing_ok=True)

    if size > args.max_asset_bytes:
        parts_dir = args.dist / f'{args.code}-parts'
        parts = split_file(abm, parts_dir, args.max_asset_bytes / 1024 ** 3)
        print(f'{args.code}: {size} B over cap, split into {len(parts)} parts')


if __name__ == '__main__':
    main()
