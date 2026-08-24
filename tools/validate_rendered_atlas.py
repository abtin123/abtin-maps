#!/usr/bin/env python3
import sqlite3
import tempfile
from pathlib import Path

try:
    from PIL import Image
except ImportError as error:
    raise SystemExit(
        "Install renderer dependencies before validating the atlas: "
        "python -m pip install -r requirements-renderer.txt"
    ) from error

from rendered_tile_builder import build_atlas, build_preview
from raster_primitives import RenderHandler, TileStore


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

    # خروجی تبدیل موازی باید همان ساختار WebP قابل خواندن را نگه دارد.
    rendered_root = root / 'parallel'
    store = TileStore(rendered_root, 11, 11, max_open_tiles=32)
    store.draw_line([(44.0, 25.0), (44.2, 25.2)], '#FFFFFF', 3)
    store.draw_poi(44.1, 25.1, 50, '#F6A623')
    produced = store.finalize_webp(quality=64, method=3, workers=2)
    assert produced >= 2
    assert not list(rendered_root.rglob('*.png'))
    assert all(path.stat().st_size > 0 for path in rendered_root.rglob('*.webp'))

    # نقشهٔ پایه سبک است: POI و ساختمان تا زمانی‌که کاربر صریحاً بخواهد
    # در رستر bake نمی‌شوند؛ دادهٔ POI در لایهٔ قابل‌کنترل اپ باقی می‌ماند.
    handler = RenderHandler(store)
    assert handler.include_poi_tiles is False
    assert handler.include_buildings is False

source = (Path(__file__).parent / 'raster_primitives.py').read_text(encoding='utf-8')
builder = (Path(__file__).parent / 'rendered_tile_builder.py').read_text(encoding='utf-8')
repo_root = Path(__file__).parents[1]
workflow = (repo_root / '.github/workflows/build-abtin-map.yml').read_text(encoding='utf-8')
country_builder = (Path(__file__).parent / 'build_country_package.py').read_text(encoding='utf-8')
assert '"residential": 12' in source and '"service": 13' in source
assert 'default=14' in source and 'default=14' in builder
assert 'overzoom_max' in source and 'overzoom_max' in builder
assert 'parser.add_argument("--include-poi-tiles"' in builder
assert 'parser.add_argument("--include-buildings"' in builder
assert 'build_country_package.py' in workflow
assert '"--building-min-zoom", "16"' in country_builder
assert '"--workers", str(int(profile.get("render_workers", 4)))' in country_builder
assert '"--webp-quality", str(int(profile.get("webp_quality", 60)))' in country_builder
assert '"--webp-method", str(int(profile.get("webp_method", 1)))' in country_builder
assert '"--max-open-tiles", str(int(profile.get("max_open_tiles", 512)))' in country_builder
assert 'WebP progress:' in source and 'chunksize=64' in source
print('rendered_atlas_fixture_ok')
