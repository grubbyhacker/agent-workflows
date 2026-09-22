# Agent Instructions

This repository is **PUBLIC**. No secrets, hostnames, IP addresses, or private
paths may ever appear in it.

The reusable workflow is a versioned interface consumed by other repositories.
Breaking changes require a new major tag rather than an edit in place.

Design notes for the agent platform live in `docs/agent-platform/`. The cross-repo
architecture they implement is `agent-infra-docs/design/agent-platform-coupling.md`
and takes precedence: if implementation shows the architecture is wrong, correct it
there first, then update the note here.

`runtime-base/Dockerfile` and the inline base that `publish-agent-image.yml`
generates are two definitions of one runtime. `scripts/validate-runtime-base-parity.py`
fails CI when their pins disagree — change both, or migrate the inline base onto the
shared one.
