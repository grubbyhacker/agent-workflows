# Agent runtime base

Stage 2 of the agent platform coupling work. The cross-repo architecture lives in
`agent-infra-docs/design/agent-platform-coupling.md` and is authoritative; this note
records only what is true of `agent-workflows`.

If implementation shows the architecture is wrong, the correction lands in
`agent-infra-docs` first and this note follows.

## Why a base image exists

The design requires each agent to ship as a **dedicated** artifact rather than reusing
a service image, so that publishing an agent does not depend on a service release. That
needs a shared bounded runtime to derive from.

The reusable `publish-agent-image.yml` could not provide one: it generates a complete
caller-specific image and publishes only `ghcr.io/<owner>/<repository>-agent`. There was
no separately versioned base to build on.

`runtime-base/Dockerfile` is that base, published as
`ghcr.io/<owner>/agent-runtime-base`. It carries the broker CLI, the worker entrypoints,
Codex, mise, and a minimal shell toolchain — and deliberately **no** repository
dependencies and **no** agent code.

## What it does not change

Nothing consumes the base yet. `publish-agent-image.yml` is untouched, so existing
callers (`repository-agent-fixture`, `thoughts`) keep building exactly as before and the
`@v1` interface is unchanged.

This is the design's declaration-first rule: publish the artifact, verify it, and let
consumers migrate afterwards.

## Versioning

Same scheme as the agent images, for consistency rather than novelty:

- `sha-<commit>` — immutable, one per commit of this repository;
- `main` — moving convenience tag on the default branch;
- semver when a version tag is pushed.

**Consumers pin the immutable coordinate**
`ghcr.io/<owner>/agent-runtime-base:sha-<commit>@sha256:<digest>`. The publish workflow
prints that coordinate in its step summary. Digest-only consumption is what the design
requires of anything that resolves a release, and the same discipline applies here.

Note that `@v1` on the reusable *workflow* and the image's tags are different things:
the workflow tag is a moving interface version, while an image coordinate is pinned.

## The parity hazard, and the check that guards it

Factoring the base out created two definitions of one runtime: the standalone
`runtime-base/Dockerfile`, and the inline copy that `publish-agent-image.yml` still
generates for existing callers.

`scripts/validate-runtime-base-parity.py` fails if they disagree on any
security-relevant pin: the gh-agent-broker source revision, the Debian and mise base
image digests, the Codex version and both architecture checksums, and the apt package
set. It also refuses forbidden client packages in the base.

It is offline — it compares two files and never builds an image or reaches a registry —
so drift is caught in a pull request rather than in a publish. It runs in `ci.yml` on
every pull request and push, and again inside the publish workflow before any build.

The duplication is temporary. When callers derive from the published base, the inline
copy and this check both go away.

## Verification on publish

Before anything is pushed, the workflow builds for amd64 and asserts:

- the image's broker-source-revision label and on-disk file match the pinned revision;
- the Codex version label matches the pin;
- every required entrypoint exists and is executable;
- the base carries **no** dependency manifest and `/workspace` is empty, so agent
  content cannot leak into the shared base;
- no forbidden client (`gh`, `ssh`, `ansible`, `doppler`, `tofu`, …) is present, by
  command lookup, package query, and a `PATH` sweep.

Only then is the multi-platform image published.
