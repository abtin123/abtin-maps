# Build-script verification report

Date: 2026-09-01

## Automated checks completed in this environment

- Python compilation for all `tool/maps/*.py`: PASS
- Bash syntax for all `tool/maps/*.sh`: PASS
- JSON parsing for repository JSON files: PASS
- YAML parsing for workflow files: PASS
- Style contract: PASS
  - vector source maxzoom 16
  - major road labels z8
  - local road labels z14
  - buildings z14
  - POI z12
- Regional catalog expansion with a synthetic north/east/west fixture: PASS
- Source-signature unchanged skip path: PASS
- Block patch generation: PASS
- Block patch reconstruction against target bytes: PASS
- Synthetic ABM packer + strict container verifier: PASS
  - graph segment detected
  - all style/resource entries detected
  - FTS5 search index detected and queried
  - style zoom contract validated

## Checks that cannot be executed here

A real Planetiler country build cannot be executed in this sandbox because Docker, the Planetiler image, `pmtiles`, and a real multi-gigabyte OSM PBF are not available. The GitHub Actions workflow installs those dependencies and performs the full build/verify sequence on Ubuntu runners.

Likewise, the actual weekly OSM update requires access to Geofabrik's live PBF and MD5 endpoints. The pipeline uses the published `.osm.pbf.md5` sidecar to decide whether an extract changed.

No claim is made here that a full country map was rendered successfully in this sandbox.
