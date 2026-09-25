# Regional country builds / ساخت منطقه‌ای کشورها

The builder now treats first-level administrative regions as a generic country capability.

- A country with a curated `regions_config` uses that file.
- Otherwise the workflow generates an Admin-1 config from Natural Earth Admin-1 data published through DataHub.
- The generated config uses the real polygon extent to derive each region bounding box; the OSM regional build still preserves complete ways and uses a routing overlap corridor.
- Countries without Admin-1 records fall back to one country ABM.
- Region IDs prefer ISO-3166-2 and otherwise use deterministic name hashes.

Data source: Natural Earth Admin-1 via DataHub (`admin1.geojson`). The dataset contains first-order subdivisions such as states, provinces and departments worldwide.

The Flutter app consumes the `country_code`, `country_name_*`, `region_name_*`, `bbox`, and routing metadata from the release manifest, so the download UI has no Iran-only branch.
