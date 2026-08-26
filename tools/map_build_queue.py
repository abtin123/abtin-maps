#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persistent FIFO queue for GitHub Actions map batches.

Only one map batch is active. A successful map build dispatches the next batch,
so the scheduler never needs to remain alive for many hours.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


def load(path: Path) -> dict:
    if not path.exists():
        return {'schema': 1, 'active': None, 'pending': [], 'completed': []}
    return json.loads(path.read_text(encoding='utf-8'))


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def batches_from_files(files: list[Path]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for file in files:
        if not file.exists():
            continue
        for raw in file.read_text(encoding='utf-8').splitlines():
            batch = ','.join(part.strip().upper() for part in raw.split(',') if part.strip())
            if not batch or batch in seen:
                continue
            seen.add(batch)
            result.append(batch)
    return result


def emit_active(data: dict) -> None:
    active = data.get('active')
    if not active:
        print('has_active=false')
        return
    print('has_active=true')
    print(f"queue_id={data['queue_id']}")
    print(f"countries={active['countries']}")
    print(f"release_tag={data['release_tag']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--queue', type=Path, default=Path('tools/map_build_queue.json'))
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--init', action='store_true')
    action.add_argument('--complete', action='store_true')
    action.add_argument('--emit-active', action='store_true')
    parser.add_argument('--release-tag', default='maps-v3')
    parser.add_argument('--batch-file', type=Path, action='append', default=[])
    parser.add_argument('--mode', default='initial')
    parser.add_argument('--queue-id', default='')
    args = parser.parse_args()

    data = load(args.queue)
    if args.init:
        if data.get('active') or data.get('pending'):
            raise SystemExit('یک صف ساخت نقشه هنوز فعال است؛ صف جدید ساخته نشد.')
        batches = batches_from_files(args.batch_file)
        if not batches:
            # Even an empty run may establish source baselines. Persist an empty
            # queue so the caller can safely commit state without a missing file.
            data = {'schema': 1, 'active': None, 'pending': [], 'completed': []}
            save(args.queue, data)
            emit_active(data)
            return
        queue_id = args.queue_id or f"{args.mode}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
        data = {
            'schema': 1,
            'queue_id': queue_id,
            'mode': args.mode,
            'release_tag': args.release_tag,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'active': {'index': 1, 'countries': batches[0]},
            'pending': [{'index': index + 2, 'countries': batch} for index, batch in enumerate(batches[1:])],
            'completed': [],
        }
        save(args.queue, data)
        emit_active(data)
        return

    if args.complete:
        if not args.queue_id or data.get('queue_id') != args.queue_id:
            raise SystemExit('شناسهٔ صف با وضعیت فعلی یکی نیست؛ صف تغییر نکرد.')
        active = data.get('active')
        if not active:
            emit_active(data)
            return
        data.setdefault('completed', []).append({**active, 'completed_at': datetime.now(timezone.utc).isoformat()})
        pending = data.get('pending', [])
        data['active'] = pending.pop(0) if pending else None
        data['pending'] = pending
        save(args.queue, data)
        emit_active(data)
        return

    emit_active(data)


if __name__ == '__main__':
    main()
