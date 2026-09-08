#!/usr/bin/env python3
"""Validate Abtin vector-map zoom contract."""
from pathlib import Path
import re, sys
cfg = Path(__file__).with_name('abtin_basemap.yml').read_text(encoding='utf-8')
errors=[]
if not re.search(r'maxzoom:\s*16', cfg): errors.append('tile-pyramid maxzoom must be 16')
if not re.search(r'- id: buildings[\s\S]*?min_zoom:\s*14', cfg): errors.append('buildings must start at z14')
if not re.search(r'- id: pois[\s\S]*?min_zoom:\s*12', cfg): errors.append('POI must start at z12')
if errors:
    print('\n'.join(errors)); sys.exit(1)
print('Vector data contract OK: z2-z16, app overzoom z18')
