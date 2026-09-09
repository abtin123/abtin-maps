# GitHub Actions build troubleshooting

The build workflow now treats a cancelled/terminated country build separately
from the release manifest. A manifest is generated only when at least one
completed `.abm` artifact exists, and publication is blocked when no completed
artifact exists.

A log line such as:

    The runner has received a shutdown signal

is not a Python routing exception. It means the GitHub Actions runner itself
was stopped or the job was cancelled. Increasing Python timeouts cannot prevent
that external shutdown. The workflow is configured with a long job timeout and
`fail-fast: false`; if a runner is externally cancelled, the manifest job will
no longer fail with a misleading `No .abm files found directly under dist`.
