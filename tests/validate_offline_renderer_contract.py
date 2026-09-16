import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
assert not (ROOT/'assets/styles'/'offline_day.json').exists()
assert not (ROOT/'assets/styles'/'offline_night.json').exists()
assets=(ROOT/'lib/abtinmap/abm_style_assets.dart').read_text()
assert 'https://tiles.openfreemap.org/styles/liberty' in assets
assert 'https://tiles.openfreemap.org/styles/dark' in assets
assert 'abm-roads' in assets and 'abm-poi' in assets
assert 'abtin_maps_exact_online_style' in assets
r=(ROOT/'lib/map_engine/abm_reader.dart').read_text(); b=(ROOT/'lib/map_engine/abm_geojson_bridge.dart').read_text(); p=(ROOT/'lib/map_engine/abm_poi_reader.dart').read_text(); v=(ROOT/'lib/features/map/presentation/online_map_view.dart').read_text()
assert '_AbmArchiveWorker' in r and '_readIndexedChunk' in r and 'index.select' in r
assert "'poi': 'abm-poi'" in b and '_isReverseOneway' in b
assert 'poi/poi.sqlite' in p
assert "sourceLayer:'poi'" in v and 'addCircleLayer' in v
print('OK')
