# ABM indexed engine update — 2026-09-12

This builder keeps **ABM** as the only map container and keeps the existing `ABMV1` vector record stream.

## What changed

- Every vector layer now gets a compact `vector/<layer>.idx` geographic index.
- The index uses 0.5° cells and stores record byte ranges, so the app can select only records intersecting the visible area.
- Vector `.bin` and `.idx` members are stored (not DEFLATE-compressed) inside the ABM so the app can seek directly into the original `.abm` file. This does **not** create tiles or a second map package format.
- A disk-backed `routing/routing.sqlite` is emitted with indexed `nodes`/`edges` access and a 0.25° node grid. `routing/graph.bin` is retained for backward compatibility.
- New metadata advertises `vector_index: ABMIDX1` while retaining `format: ABM` and `version: 2`.
- The verifier rejects incomplete index sets and requires the indexed routing database for new indexed builds.

## Compatibility

Older ABMs without `.idx` members continue to work through the app's sequential ABMV1 fallback. Older ABMs without `routing/routing.sqlite` continue to use `routing/graph.bin`.

## Validation

`python -m compileall -q .` and the builder test suite pass locally in this environment. A sample ABM was built and verified with 19 members, including all six vector indexes and `routing/routing.sqlite`.
