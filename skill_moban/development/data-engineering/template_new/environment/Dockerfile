FROM clickhouse/clickhouse-server:25.3

ENV DEBIAN_FRONTEND=noninteractive
ENV CLICKHOUSE_USER=default
ENV CLICKHOUSE_PASSWORD=

WORKDIR /app/workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pytest ca-certificates procps gzip curl \
    && rm -rf /var/lib/apt/lists/*

COPY workspace /app/workspace

# Copy skills to agent-specific locations. The without-skill runtime removes
# environment/skills and these copy lines; no task files, tests, data, or
# dependencies differ between the two runtimes.
COPY skills /root/.codex/skills
COPY skills /root/.claude/skills
COPY skills /root/.agents/skills

RUN mkdir -p /logs/verifier /var/lib/clickhouse /var/log/clickhouse-server /tmp/clickhouse-wave \
    && chmod 755 /app/workspace/run.sh \
    && find /app/workspace/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/clickhouse-wave-data.sha256 \
    && chmod 644 /opt/clickhouse-wave-data.sha256

CMD ["/bin/bash"]
