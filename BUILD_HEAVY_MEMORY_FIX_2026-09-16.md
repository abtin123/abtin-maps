# Heavy PBF Build / GitHub Runner Memory Fix — 2026-09-16

Applied to the ABM build pipeline for large country extracts such as Iran.

## Changes

- `build_abm.py`
  - Extracts each vector layer one at a time instead of keeping all extracted
    feature lists in RAM simultaneously.
  - Builds POI/search inputs one list at a time and releases them before routing.
  - Derives the published bbox from the vector chunk indexes rather than
    retaining extracted geometry solely for bbox calculation.
  - Explicitly releases the materialized source `Dataset` and runs Python GC
    before the streamed PBF routing phase.
  - Keeps the existing streamed `build_graph_from_pbf()` routing path.

- `abm_builder/core.py`
  - `write_spatial_chunks()` now flushes a geographic cell as soon as its
    chunk reaches the configured size instead of retaining every feature in
    every cell until the entire layer is finished.
  - Chunk bounding boxes remain localized to their geographic cell.

## Validation

- Python syntax checks passed for the modified builder/core/routing modules.
- A complete ABM build from `sample/mini_country.jsonl` passed and produced a
  non-empty routing graph.
- Existing `validate_unified_map_contract.py` passed.
- The existing `validate_offline_renderer_contract.py` still fails because the
  current project does not contain the exact OpenFreeMap Liberty URL expected
  by that pre-existing test; this change did not modify the app renderer/style.
