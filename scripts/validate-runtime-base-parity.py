#!/usr/bin/env python3
"""Assert the shared runtime base and the inline agent-image base agree.

`runtime-base/Dockerfile` is a standalone, reviewable definition of the bounded
agent runtime. `.github/workflows/publish-agent-image.yml` still generates its own
inline copy of that same base so existing callers keep working unchanged.

Two definitions of one runtime is a drift hazard, so every security-relevant pin
must match exactly:

  * the pinned gh-agent-broker source revision;
  * the Debian and mise base image digests;
  * the Codex version and both architecture checksums;
  * the apt package set;
  * the absence of forbidden clients.

This check is offline: it reads the two files and compares them. It does not build
an image or reach a registry.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_DOCKERFILE = REPO_ROOT / "runtime-base" / "Dockerfile"
AGENT_IMAGE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "publish-agent-image.yml"

FORBIDDEN_CLIENTS = ("gh", "tofu", "opentofu", "ansible", "doppler", "ssh", "scp", "sftp")

PATTERNS: dict[str, re.Pattern[str]] = {
    "broker revision": re.compile(r"BROKER_REVISION=([0-9a-f]{40})"),
    "debian base digest": re.compile(r"debian:trixie-slim@(sha256:[0-9a-f]{64})"),
    "mise base digest": re.compile(r"ghcr\.io/jdx/mise:[0-9.]+@(sha256:[0-9a-f]{64})"),
    "codex version": re.compile(r"CODEX_VERSION=([0-9]+\.[0-9]+\.[0-9]+)"),
    "codex amd64 checksum": re.compile(r"codex_arch=x64;[^;]*;\s*codex_sha512=([0-9a-f]{128})"),
    "codex arm64 checksum": re.compile(r"codex_arch=arm64;[^;]*;\s*codex_sha512=([0-9a-f]{128})"),
    "apt packages": re.compile(r"apt-get install -y --no-install-recommends ([a-z0-9 .+-]+?) &&"),
}


def collect(name: str, pattern: re.Pattern[str], text: str, source: str, errors: list[str]) -> set[str]:
    found = {match.group(1).strip() for match in pattern.finditer(text)}
    if not found:
        errors.append(f"{source}: could not find {name}; the parity check cannot be trusted")
    return found


def main() -> int:
    errors: list[str] = []

    for path in (BASE_DOCKERFILE, AGENT_IMAGE_WORKFLOW):
        if not path.is_file():
            print(f"missing required file: {path}", file=sys.stderr)
            return 1

    base_text = BASE_DOCKERFILE.read_text(encoding="utf-8")
    workflow_text = AGENT_IMAGE_WORKFLOW.read_text(encoding="utf-8")

    for name, pattern in PATTERNS.items():
        base_values = collect(name, pattern, base_text, "runtime-base/Dockerfile", errors)
        workflow_values = collect(name, pattern, workflow_text, "publish-agent-image.yml", errors)
        if not base_values or not workflow_values:
            continue
        if base_values != workflow_values:
            errors.append(
                f"{name} differs between the shared runtime base and the inline "
                f"agent-image base: base={sorted(base_values)} "
                f"inline={sorted(workflow_values)}. One runtime, one set of pins — "
                "update both or migrate the inline base onto the shared one."
            )

    # The base must never install a client that would let an agent bypass the broker.
    apt_line = re.search(r"apt-get install -y --no-install-recommends ([a-z0-9 .+-]+?) &&", base_text)
    if apt_line:
        packages = apt_line.group(1).split()
        for package in packages:
            if package.startswith(FORBIDDEN_CLIENTS):
                errors.append(
                    f"runtime-base/Dockerfile installs forbidden client package "
                    f"'{package}'. Agents reach GitHub only through the broker."
                )

    if errors:
        print("Runtime base parity check failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(
        "Runtime base parity check passed "
        f"({len(PATTERNS)} pinned properties match between the shared base and the "
        "inline agent-image base)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
