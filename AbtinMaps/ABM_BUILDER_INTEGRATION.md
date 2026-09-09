# ABM Builder ↔ App integration

The app now consumes the same tile-free `.abm` format produced by `tool/abm_builder`.

## Build a real map

Install the builder dependencies, then run:

```bash
pip install -r tool/abm_builder/requirements.txt
python tool/build_bundled_abm.py path/to/country.osm.pbf --country IR
```

The resulting `assets/maps/IR.abm` is the exact output of `build_abm.py`.
`bundled_manifest.json` is regenerated with its SHA-256.

For a large country, pass the builder's regional config with `--regions`.
The release workflow can still publish the same `.abm` files separately.

## Runtime path

1. App startup reads `assets/maps/bundled_manifest.json`.
2. Each generated `.abm` is installed into the normal ABM storage directory.
3. `AbmReader` opens that file.
4. The existing vector renderer, offline search and ABM routing read the same archive.
5. There is no second raster/tile fallback for the bundled map.

The repository includes a small `US.abm` generated from `tool/abm_builder/sample/us_mini.jsonl` as an end-to-end test fixture. It is intentionally a miniature fixture, not a production US map. Replace it by running `tool/build_bundled_abm.py` with a real OSM PBF before a production build.
