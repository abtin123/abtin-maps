# GitHub limits used by the map pipeline

The pipeline keeps one independent release asset per country/region map (or per part for an oversized ABM), plus manifest/report and optional update patches.

- GitHub Releases supports up to 1,000 assets per release.
- Each release asset must remain below 2 GiB.
- GitHub-hosted runner jobs have a six-hour maximum runtime.
- GitHub Actions supports far more than the 64-map build matrix used here.

The workflow uses 64 parallel build chunks so a slow/large extract does not block all other extracts. A final merge job refuses to publish unless every entry in the authoritative catalog is present and its OSM source signature matches the current catalog.

For a single ABM that would exceed the per-asset limit, `split_abm.py` creates byte-identical `XX.abm.part0`, `XX.abm.part1`, ... files. The Flutter client already supports concatenating these parts and validates the SHA-256 of the resulting full ABM.

Update patches are generated only for changed single-file ABMs and only when the block patch is smaller than the full map. If the release asset count would exceed GitHub's 1,000-asset limit, the workflow fails instead of silently dropping maps or patches; the release must then be moved to object storage/a dedicated patch release rather than publishing an incomplete map set.
