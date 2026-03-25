#!/usr/bin/env python3

from __future__ import annotations

import gzip
import json
import random
from pathlib import Path


SERVICES = {
    "auth": {
        "paths": ["/login", "/logout", "/mfa/check", "/session/refresh"],
        "error_codes": ["AUTH_TIMEOUT", "TOKEN_EXPIRED", "MFA_BACKEND_503"],
        "ok_statuses": [200, 204],
        "error_statuses": [401, 429, 503],
        "latency_base": 34,
        "bytes_base": 820,
    },
    "billing": {
        "paths": ["/invoice/create", "/invoice/pay", "/ledger/export", "/refund"],
        "error_codes": ["CARD_DECLINED", "LEDGER_LOCKED", "GATEWAY_502"],
        "ok_statuses": [200, 201],
        "error_statuses": [402, 409, 502],
        "latency_base": 47,
        "bytes_base": 940,
    },
    "gateway": {
        "paths": ["/edge/route", "/edge/health", "/edge/cache", "/edge/retry"],
        "error_codes": ["UPSTREAM_TIMEOUT", "EDGE_OVERLOAD", "DNS_MISS"],
        "ok_statuses": [200, 202],
        "error_statuses": [429, 502, 504],
        "latency_base": 29,
        "bytes_base": 760,
    },
    "inventory": {
        "paths": ["/stock/check", "/stock/move", "/warehouse/sync", "/reservation"],
        "error_codes": ["SKU_LOCKED", "BIN_STALE", "SYNC_LAG"],
        "ok_statuses": [200, 204],
        "error_statuses": [409, 423, 504],
        "latency_base": 39,
        "bytes_base": 880,
    },
    "search": {
        "paths": ["/query", "/suggest", "/facet", "/reindex"],
        "error_codes": ["INDEX_STALE", "CACHE_FRAGMENTED", "QUERY_BUDGET"],
        "ok_statuses": [200, 206],
        "error_statuses": [429, 500, 503],
        "latency_base": 31,
        "bytes_base": 790,
    },
    "worker": {
        "paths": ["/job/pull", "/job/ack", "/job/requeue", "/job/drain"],
        "error_codes": ["QUEUE_BACKPRESSURE", "JOB_POISONED", "BROKER_IO"],
        "ok_statuses": [200, 202],
        "error_statuses": [409, 429, 500],
        "latency_base": 44,
        "bytes_base": 910,
    },
}

SHARDS = ["zone-a", "zone-b", "zone-c", "zone-d"]
HOSTS = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
RECORDS_PER_FILE = 920
FILE_COUNT = 18


def build_line(service: str, shard: str, file_index: int, line_index: int, rng: random.Random) -> str:
    config = SERVICES[service]
    minute = (file_index * 7 + line_index // 46) % 60
    second = (line_index * 13 + file_index) % 60
    timestamp = f"2026-02-18T11:{minute:02d}:{second:02d}Z"
    host = f"{service}-{HOSTS[(file_index + line_index) % len(HOSTS)]}"
    path = config["paths"][(line_index + file_index) % len(config["paths"])]

    error_cycle = (line_index + file_index * 3) % 19
    burst = 1 if (line_index // 57 + file_index) % 5 == 0 else 0
    if error_cycle in (0, 1, 2 + burst):
        error_code = config["error_codes"][(line_index + file_index) % len(config["error_codes"])]
        status = config["error_statuses"][(line_index + file_index * 2) % len(config["error_statuses"])]
        latency_ms = config["latency_base"] + 90 + (line_index % 43) * 3 + file_index * 2
    else:
        error_code = "OK"
        status = config["ok_statuses"][(line_index + file_index) % len(config["ok_statuses"])]
        latency_ms = config["latency_base"] + (line_index % 27) * 2 + (file_index % 5)

    bytes_out = config["bytes_base"] + (line_index * 17 + file_index * 29) % 1400
    request_id = f"{service[:3]}-{file_index:02d}-{line_index:05d}"
    client_id = f"acct-{rng.randint(1000, 9999)}"

    return "|".join(
        [
            timestamp,
            service,
            shard,
            host,
            str(status),
            error_code,
            str(latency_ms),
            str(bytes_out),
            path,
            request_id,
            client_id,
        ]
    )


def build_assets(workspace_root: Path) -> None:
    rng = random.Random(20260325)
    gzip_dir = workspace_root / "gzip_logs"
    gzip_dir.mkdir(parents=True, exist_ok=True)

    service_names = list(SERVICES)
    manifest_files = []

    for file_index in range(FILE_COUNT):
        service = service_names[file_index % len(service_names)]
        shard = SHARDS[file_index % len(SHARDS)]
        filename = f"{file_index:02d}_{service}_{shard}.log.gz"
        output_path = gzip_dir / filename

        with gzip.open(output_path, "wt", encoding="utf-8") as handle:
            for line_index in range(RECORDS_PER_FILE + (file_index % 4) * 20):
                handle.write(build_line(service, shard, file_index, line_index, rng))
                handle.write("\n")

        manifest_files.append(
            {
                "filename": filename,
                "service": service,
                "shard": shard,
            }
        )

    manifest = {
        "dataset_id": "edge-ops-2026-02-18",
        "services": service_names,
        "files": manifest_files,
    }
    (workspace_root / "log_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    build_assets(Path("/root/workspace"))
