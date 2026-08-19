#!/usr/bin/env python3
import sqlite3
import tempfile
from pathlib import Path

from PIL import Image

from rendered_tile_builder import build_atlas, build_preview


with tempfile.TemporaryDirectory(prefix='abtin-atlas-test-') as raw:
    root = Path(raw)
    base = root / 'tiles' / '5' / '16'
    poi = root / 'poi' / '50' / '5' / '16'
    base.mkdir(parents=True)
    poi.mkdir(parents=True)
    Image.new('RGBA', (512, 512), '#17212B').save(base / '12.webp', 'WEBP', quality=64)
    Image.new('RGBA', (512, 512), '#F6A623').save(poi / '12.webp', 'WEBP', quality=64)
    target = root / 'IR.amap'
    preview = root / 'IR.preview.webp'
    assert build_preview(root, preview, 5) == preview
    assert preview.stat().st_size > 0
    max_zoom, base_count, poi_count, _ = build_atlas(
        root, target, 'IR', 5, 5, [44.0, 25.0, 64.0, 40.0], 1)
    db = sqlite3.connect(target)
    assert db.execute("SELECT value FROM metadata WHERE name='format'").fetchone()[0] == 'ABTIN_RENDERED_ATLAS/1'
    assert db.execute('SELECT COUNT(*) FROM tiles').fetchone()[0] == 1
    assert db.execute('SELECT COUNT(*) FROM poi_tiles').fetchone()[0] == 1
    assert max_zoom == 5 and base_count == 1 and poi_count == 1
    db.close()
print('rendered_atlas_fixture_ok')
