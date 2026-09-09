# Abtin Maps ABM builder (tile-free)

Builds `.abm` country archives for the Abtin Maps offline vector map engine.
An `.abm` file is a plain zip containing **only**:

```
metadata.json
vector/{roads,buildings,landuse,water,boundaries,places,terrain}.bin
poi/poi.sqlite
search/search.sqlite
routing/graph.bin
```

No tiles, no PMTiles/MBTiles, no style/color data. `metadata.json` carries
`"tiles": false`, `"style": "external"` and a `bbox` — `create_abm.py`
refuses to package (and `verify_abm.py` refuses to accept) anything that
doesn't hold, so a build can't silently regress into shipping a tile
container again.

## Basic build

```
pip install -r requirements.txt
python build_abm.py path/to/country.osm.pbf --country IR --output dist/IR.abm
```

Test locally without `osmium` using a `.jsonl` fixture (see
`sample/mini_country.jsonl` for the record shape):

```
python build_abm.py sample/mini_country.jsonl --country IR --output /tmp/IR.abm
```

## Large countries: real geographic regions

Countries too big for one archive (or one release asset) are split by
**bbox, not by bytes** — `--regions` clips the OSM dataset into named
regions *before* extraction/routing/search are built, so `US-NE.abm` and
`US-SW.abm` are genuinely separate, independently downloadable maps of
different parts of the country, not two arbitrary halves of the same file.

```
python build_abm.py us.osm.pbf --country US --regions regions/US.json --output dist/
```

See `sample/regions/US.json` for the config format: a country name plus a
list of `{code, name_fa, name_en, bbox}` regions. Adjacent regions'
bboxes are expected to overlap slightly at the edges — a road or building
that straddles the line is kept in both neighboring archives rather than
being cut in half.

This is unrelated to `packaging/split_abm.py`, which only exists to chop
an *already-built* single `.abm` into `.partNNN` byte chunks when it is
still over a hosting size cap (e.g. GitHub Release's ~2 GiB asset limit) —
it has no geography awareness at all and is a fallback of last resort, not
a substitute for `--regions`.

## Weekly updates → delta patches

`.github/workflows/weekly-build.yml` rebuilds each configured country from
its latest OSM extract every week. `packaging/create_patch.py` diffs the
new archive against the previous release in 4 MiB chunks and publishes
only the chunks that changed, plus a small JSON manifest describing them.
The app only applies a patch when the currently-installed archive's SHA-256
matches the patch's declared base — otherwise it must fall back to a full
re-download.

## Release manifest

`packaging/build_release_manifest.py` is the step that ties everything
together into the single `manifest.json` the app actually downloads and
parses (`MapCatalogService` / `MapRegion.fromJson`). Run it last, after
building and (if needed) splitting/patching every country for the release:

```
python packaging/build_release_manifest.py dist \
    --release-tag maps-v4 --names names.json --output dist/manifest.json
```

It reads each `dist/CC.abm`'s own `metadata.json` for `bbox` and (for a
region) its parent country info, folds in `dist/CC-parts/manifest.json`
and `dist/CC-patch/patch-descriptor.json` when present, and looks up
display names for ordinary (non-region) countries from `names.json`.

## Pipeline

```
build_abm.py
  └─ extractors/loader.py     OSM (.pbf via osmium, or .jsonl for tests) → Dataset
       └─ clip_dataset()      bbox clip for --regions (geographic split)
  └─ extractors/*.py          Dataset → Road/Building/Landuse/Water/Boundary/Place records
  └─ search/create_search_db.py   FTS5 + RTree search.sqlite, Persian-aware normalization
  └─ routing/graph_builder.py     routing/graph.bin (nodes, edges, turn restrictions)
  └─ packaging/create_abm.py      zips it all up, writes metadata.json (incl. bbox), verifies
  └─ packaging/split_abm.py       (only if over hosting size cap) byte-split into parts
  └─ packaging/create_patch.py    (only if a previous release exists) delta patch
  └─ packaging/build_release_manifest.py   assembles dist/manifest.json for the app
```

## Tests

No network is required; `tests/test_pipeline.py` uses the `.jsonl` fixtures
under `sample/`. Run with `pytest`, or execute the pipeline functions
directly if `pytest` isn't installed in your environment.
