# Build-script verification report

Date: 2026-09-03

## Automated checks completed in this environment

- Python compilation for all `tool/maps/*.py`: PASS
- Bash syntax for all `tool/maps/*.sh`: PASS
- JSON parsing for repository JSON files: PASS
- YAML parsing for `tool/maps/abtin_basemap.yml`: PASS
- Zoom contract: PASS — vector source range is z2 through z20
- Day/night style contract: PASS — source z2-z20, POI z12, buildings z14, major roads z8, local roads z14
- Synthetic `.abm` pack + strict container verifier: PASS
  - graph segment embedded
  - day/night styles embedded
  - offline FTS5 search index embedded and queried
  - all glyph resources embedded
  - POI sprite resources embedded
  - region code validated
- Regional catalog logic: PASS — countries with Geofabrik regional children remain split into separate ABMs; US remains split into explicit regional ABMs

## Full real-map build limitation

A full real-world Planetiler build cannot be executed in this development sandbox because Docker, the Planetiler image, `pmtiles`, and multi-gigabyte OSM PBF extracts are not available here. Therefore no claim is made that every live Geofabrik country extract was rendered in this sandbox.

The production build workflow still performs the real sequence: download/checksum the PBF, optionally clip a large-country region, generate PMTiles, cluster/verify PMTiles, build the routing graph, build the offline POI/search index, pack everything into one `.abm`, and run the strict container verifier.
