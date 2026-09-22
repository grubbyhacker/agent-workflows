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
    with:
      # Pin the exact gh-agent-broker source revision whose worker entrypoints
      # and CLI are baked into the image. Explicitly pinning this keeps worker
      # provenance attributable and lets it advance without a workflow edit.
      broker_revision: 12f5c77689c2a7cd24123420c4e579755e5eb20d
```

### `broker_revision` input

`broker_revision` is the exact `gh-agent-broker` source revision (40 lowercase
hex) baked into the agent image. It is validated fail-closed and defaults to the
reviewed pin, so existing `@v1` callers that omit it build exactly as before.
Prefer setting it explicitly: a caller that pins the revision it was reviewed
against cannot silently drift when the reviewed default later advances, and the
resulting image's `io.grubbyhacker.agent-image.broker-source-revision` label and
on-disk `broker-source-revision` are asserted against the pin before publish.

Callers must reference a major version such as `@v1`, not `@main`. The major
tag is a moving interface version: non-breaking updates advance it, while
breaking changes require a new major tag.

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

## Advancing the `v1` tag after a non-breaking change

Adding the optional, defaulted `broker_revision` input is interface-additive:
callers that omit it are unaffected, so this is a non-breaking update that
advances the existing `v1` tag in place rather than cutting a new major.

After this PR merges to `main`, an authorized maintainer advances the tag with
the repository's established process — the moving major tag is force-updated to
the merged `main` commit and pushed:

```sh
git fetch origin
git tag -f v1 origin/main
git push -f origin v1
```

Tag movement is a deliberate, human-gated release step: it is not performed by
this PR, by CI, or automatically on merge. Only once `v1` points at the merged
commit can a caller pin `broker_revision` and have `@v1` honor it.
