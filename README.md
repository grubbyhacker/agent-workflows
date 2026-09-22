# agent-workflows

This public repository publishes reusable GitHub Actions workflows for
`grubbyhacker` repositories.

It is separate from the private `vps-ops` repository because public
repositories cannot call reusable workflows stored in private repositories.

## Agent image workflow

To publish a repository agent image, keep its toolchain in a root `mise.toml`
and dependencies in a supported lockfile. Add a caller workflow with
`permissions: { contents: read, packages: write }` that invokes
`grubbyhacker/agent-workflows/.github/workflows/publish-agent-image.yml@v1`.
No Dockerfile or repository-specific image recipe is needed. The image is
pushed as `ghcr.io/<owner>/<repository>-agent` with `sha-<commit>`, `main`,
and semver tags when applicable.

The published image is the reviewed repository-worker runtime. It contains the
broker-pinned preparation, Codex execution, delivery, and recovery-validation
entrypoints plus their shell, Git, Codex, mise, and repository-declared runtime
dependencies. Consumers must deploy the immutable
`ghcr.io/<owner>/<repository>-agent:sha-<commit>@sha256:<digest>` coordinate;
the broker service image and its legacy implementation-worker image are not
repository-worker runtimes.

```yaml
jobs:
  publish-agent-image:
    permissions:
      contents: read
      packages: write
    uses: grubbyhacker/agent-workflows/.github/workflows/publish-agent-image.yml@v1
```

Callers must reference a major version such as `@v1`, not `@main`. The major
tag is a moving interface version: non-breaking updates advance it, while
breaking changes require a new major tag such as `v2`.

## Agent runtime base

`runtime-base/Dockerfile` is the shared bounded runtime that agent images derive
from. It is published as `ghcr.io/<owner>/agent-runtime-base` with `sha-<commit>`,
`main`, and semver tags, and it contains the broker CLI, the worker entrypoints,
Codex, mise, and a minimal shell toolchain — no repository dependencies and no
agent code.

Consumers pin the immutable coordinate
`ghcr.io/<owner>/agent-runtime-base:sha-<commit>@sha256:<digest>`, which the
publish workflow prints in its run summary.

It exists so that a specialised agent can ship as its own artifact, on its own
release cadence, without reusing a service image. `publish-agent-image.yml` is
unchanged and still generates its own equivalent base inline, so existing callers
are unaffected; `scripts/validate-runtime-base-parity.py` fails CI if the two
definitions ever disagree on a pinned property.

See `docs/agent-platform/runtime-base.md`.
