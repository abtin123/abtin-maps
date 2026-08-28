# GitHub limits used by the map pipeline

The official GitHub Releases documentation says a release can have up to 1,000 release assets, each release file must be under 2 GiB, and there is no stated total release-size or bandwidth limit. Source: https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases

The official GitHub Actions limits documentation says a workflow run can contain at most 256 matrix jobs, while a GitHub-hosted runner job can run for at most 6 hours. A workflow file must be no larger than 500 KB. Source: https://docs.github.com/en/actions/reference/limits

Design implications for this repository:

The pipeline uses one sequential job rather than a matrix, so it is not blocked by the 256-job matrix limit. The job timeout is set to 360 minutes, matching the six-hour GitHub-hosted runner limit; setting a larger timeout would not make a hosted job run longer. Each country or regional part is uploaded as one independent `.abm` release asset and must remain below 2 GiB. The final manifest and build report are also separate release assets.

With roughly 393 discovered country/region entries, the release remains below the 1,000-asset limit if every entry succeeds, plus the manifest and report. If a future catalog exceeds 998 map assets, the workflow must split releases/tags or use object storage. If a single country/region exceeds 2 GiB, it must be subdivided into more regional `.abm` files before upload; GitHub Release cannot accept that single archive.
