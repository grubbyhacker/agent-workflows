# Shared agent runtime base image.
#
# This is the bounded runtime every repository agent and domain agent derives
# from: the broker CLI, the worker entrypoints, Codex, mise, and a minimal shell
# toolchain. It carries no repository dependencies and no agent code.
#
# Every pin here is duplicated in the inline Dockerfile that
# .github/workflows/publish-agent-image.yml generates. That duplication is
# deliberate while callers migrate, and
# scripts/validate-runtime-base-parity.py fails CI if the two ever disagree.
#
# Forbidden clients (gh, ssh, ansible, doppler, tofu) must never be installed
# here. An agent reaches GitHub only through the broker.

ARG BROKER_REVISION=12f5c77689c2a7cd24123420c4e579755e5eb20d

FROM --platform=$BUILDPLATFORM golang:1.26.6 AS broker-source
ARG TARGETOS
ARG TARGETARCH
ARG BROKER_REVISION
RUN git init /src && git -C /src remote add origin https://github.com/grubbyhacker/gh-agent-broker.git && git -C /src fetch --depth 1 origin "$BROKER_REVISION" && git -C /src checkout --detach FETCH_HEAD && test "$(git -C /src rev-parse HEAD)" = "$BROKER_REVISION"
RUN test -s /src/workers/repo-task/worker.sh && test -s /src/workers/codex-repo-prep/worker.sh && test -s /src/workers/codex-repo-task/worker.sh && test -s /src/workers/codex-delivery/worker.sh && test -s /src/workers/codex-recovery-validation/worker.sh && test -s /src/workers/result.sh && cd /src && mkdir -p /out && CGO_ENABLED=0 GOOS="$TARGETOS" GOARCH="$TARGETARCH" go build -o /out/gh-agent-broker-cli ./cmd/gh-agent-broker && git rev-parse HEAD > /out/broker-source-revision

FROM ghcr.io/jdx/mise:2026.7.15@sha256:e62097049bfc980de5d9a25fbe16431e24c1e7713b3f77b18c04f81c25239953 AS mise

FROM debian:trixie-slim@sha256:020c0d20b9880058cbe785a9db107156c3c75c2ac944a6aa7ab59f2add76a7bd
ARG BROKER_REVISION
ENV MISE_DATA_DIR=/opt/mise MISE_CONFIG_DIR=/opt/mise MISE_CACHE_DIR=/opt/mise/cache PATH=/opt/mise/shims:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin
RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates curl fd-find git jq ripgrep tar && rm -rf /var/lib/apt/lists/* && ln -s /usr/bin/fdfind /usr/local/bin/fd
COPY --from=mise /usr/local/bin/mise /usr/local/bin/mise
COPY --from=broker-source /out/gh-agent-broker-cli /usr/local/bin/gh-agent-broker-cli
COPY --from=broker-source /out/broker-source-revision /usr/local/share/agent-image/broker-source-revision
COPY --from=broker-source /src/workers/repo-task/worker.sh /usr/local/bin/agent-repo-task-worker
COPY --from=broker-source /src/workers/codex-repo-prep/worker.sh /usr/local/bin/agent-codex-repo-prep-worker
COPY --from=broker-source /src/workers/codex-repo-task/worker.sh /usr/local/bin/agent-codex-repo-task-worker
COPY --from=broker-source /src/workers/codex-delivery/worker.sh /usr/local/bin/agent-codex-delivery-worker
COPY --from=broker-source /src/workers/codex-recovery-validation/worker.sh /usr/local/bin/agent-codex-recovery-validation-worker
COPY --from=broker-source /src/workers/result.sh /usr/local/lib/agent-worker-result.sh
ARG TARGETARCH
ARG CODEX_VERSION=0.146.0
RUN case "$TARGETARCH" in amd64) codex_arch=x64; codex_target=x86_64-unknown-linux-musl; codex_sha512=7ecc2fc86a6b00f08c88e12e7bfecc28c93ba428e1f6464825f257e62f5ab667e798661b602714859b041fd2c43f4fb4b79c723ea0db7cd5d8ecd4b1215b97c4 ;; arm64) codex_arch=arm64; codex_target=aarch64-unknown-linux-musl; codex_sha512=aa2603c649041675c6ee3a1a7495ba43e5dc8320d70a919da5af6793f73e8b4804a26babd63edb1efc75d8d7d658217fcbc4eaae2e9acbe14bb82d8c8dd7a1b4 ;; *) printf "Unsupported Codex architecture: %s\n" "$TARGETARCH" >&2; exit 1 ;; esac && curl -fsSL "https://registry.npmjs.org/@openai/codex/-/codex-${CODEX_VERSION}-linux-${codex_arch}.tgz" -o /tmp/codex.tgz && printf "%s  /tmp/codex.tgz\n" "$codex_sha512" | sha512sum -c - && install -d /tmp/codex /opt/codex && tar -xzf /tmp/codex.tgz -C /tmp/codex --strip-components=1 && cp -a "/tmp/codex/vendor/${codex_target}/." /opt/codex/ && ln -s /opt/codex/bin/codex /usr/local/bin/codex && rm -rf /tmp/codex /tmp/codex.tgz
RUN chmod 0755 /usr/local/bin/mise /usr/local/bin/gh-agent-broker-cli /usr/local/bin/agent-repo-task-worker /usr/local/bin/agent-codex-repo-prep-worker /usr/local/bin/agent-codex-repo-task-worker /usr/local/bin/agent-codex-delivery-worker /usr/local/bin/agent-codex-recovery-validation-worker /usr/local/lib/agent-worker-result.sh /usr/local/bin/codex && test "$(cat /usr/local/share/agent-image/broker-source-revision)" = "$BROKER_REVISION" && test -x /usr/local/bin/gh-agent-broker-cli && test -x /usr/local/bin/agent-repo-task-worker && test -x /usr/local/bin/agent-codex-repo-prep-worker && test -x /usr/local/bin/agent-codex-repo-task-worker && test -x /usr/local/bin/agent-codex-delivery-worker && test -x /usr/local/bin/agent-codex-recovery-validation-worker && test -x /usr/local/lib/agent-worker-result.sh
WORKDIR /workspace
LABEL io.grubbyhacker.agent-image.broker-source-revision=$BROKER_REVISION
LABEL io.grubbyhacker.agent-runtime-base.codex-version=$CODEX_VERSION
CMD ["bash"]
