# Build pipeline notes

The official Geofabrik index used by the all-country builder is:

- https://download.geofabrik.de/index-v1.json

The index is a GeoJSON FeatureCollection. In the inspected snapshot it contained 555 features and 191 country-level records with `iso3166-1:alpha2`. Each record provides a country/region name, geometry, and a direct PBF URL under `urls.pbf`.

Large-country handling implemented in this project:

- Countries with at least three Geofabrik child regions are built from those child PBFs instead of the whole-country PBF.
- The United States is explicitly split into West, Central, East, and Alaska regional bbox builds because the Geofabrik index exposes the US as one country PBF rather than state-level children.
- Each regional build gets a distinct code such as `US-WEST` and is recorded as an independent manifest entry.
- A failed region is recorded in `build-report.json` and does not stop later regions.
- Existing archives are skipped when the local archive SHA-256 matches the previous manifest entry.

The correct application-language manifest is separate from map building:

- https://github.com/abtin123/Make-langueg/releases/download/langpacks-latest/manifest.json
