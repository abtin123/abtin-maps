import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STYLE = ROOT / 'assets/styles/abtin_unified_style.json'
SPRITE = ROOT / 'assets/sprites/abtin.json'
SPRITE2 = ROOT / 'assets/sprites/abtin@2x.json'
STYLE_ASSETS = (ROOT / 'lib/abtinmap/abm_style_assets.dart').read_text(encoding='utf-8')
MAP_VIEW = (ROOT / 'lib/features/map/presentation/online_map_view.dart').read_text(encoding='utf-8')
PROVIDERS = (ROOT / 'lib/shared/providers/abtinmap_providers.dart').read_text(encoding='utf-8')
BUILDER = (ROOT / 'packaging/create_abm.py').read_text(encoding='utf-8')

style = json.loads(STYLE.read_text(encoding='utf-8'))
sprite = json.loads(SPRITE.read_text(encoding='utf-8'))
sprite2 = json.loads(SPRITE2.read_text(encoding='utf-8'))

assert style['version'] == 8
assert style['sprite'] == '__ABTIN_LOCAL_SPRITE__'
assert style['glyphs'] == '__ABTIN_LOCAL_GLYPHS__'
assert len(style['layers']) >= 100
assert {'openmaptiles', 'ne2_shaded', 'abm-poi', 'world-countries'} <= set(style['sources'])
assert 'abtin-gulf-label' in style['sources']
assert any(layer.get('id') == 'abtin_gulf_persian_fixed_label' and layer.get('layout', {}).get('text-field') == 'خلیج فارس' for layer in style['layers'])
for layer in style['layers']:
    if layer.get('id') in {'water_name_point_label', 'water_name_line_label'}:
        assert layer.get('layout', {}).get('text-field', [])[0] == 'case'

# Every concrete local icon referenced by the style must exist in both atlases.
for layer in style['layers']:
    image = layer.get('layout', {}).get('icon-image')
    refs = []
    if isinstance(image, str):
        refs = [image]
    elif isinstance(image, list):
        refs = [x for x in image if isinstance(x, str) and x.startswith(('abm-', 'circle_', 'road_', 'airport_'))]
    for ref in refs:
        assert ref in sprite, (layer['id'], ref)
        assert ref in sprite2, (layer['id'], ref)

# The application must never fall back to downloading a provider Style.
assert 'styles/liberty' not in STYLE_ASSETS
assert 'styles/dark' not in STYLE_ASSETS
assert 'styles/liberty' not in MAP_VIEW
assert 'styles/dark' not in MAP_VIEW
assert 'Unified local MapLibre style was not resolved' in MAP_VIEW

# Online keeps network data; offline derives ABM GeoJSON sources from the same style.
assert '_configureOnlineSources' in STYLE_ASSETS
assert '_configureOfflineSources' in STYLE_ASSETS
assert "'transportation': 'abm-roads'" in STYLE_ASSETS
assert "'poi': 'abm-poi'" in STYLE_ASSETS

# Routing readiness is based on graph contents, not merely graph.sqlite existence.
assert 'SELECT COUNT(*) AS c FROM nodes' in PROVIDERS
assert 'SELECT COUNT(*) AS c FROM edges' in PROVIDERS
assert 'routingGraphReady' in PROVIDERS
assert 'routing graph is empty' in BUILDER or 'routing graph is empty' in BUILDER.lower()

print('OK: unified MapLibre style / local sprite / ABM routing contracts')
