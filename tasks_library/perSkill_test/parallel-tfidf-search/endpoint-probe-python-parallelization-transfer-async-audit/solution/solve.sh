#!/bin/bash
set -euo pipefail

cat > /root/workspace/async_endpoint_audit.py <<'PYTHON_EOF'
#!/usr/bin/env python3
"""
Bounded-concurrency asynchronous endpoint audit implementation.
"""

from __future__ import annotations

import asyncio
import time

from endpoint_fixture import AuditRun, EndpointTarget, build_report, build_targets_from_manifest
from sequential_endpoint_audit import fetch_endpoint


async def audit_endpoints_async(targets: list[EndpointTarget], concurrency: int = 8) -> AuditRun:
    if concurrency < 1:
        raise ValueError("concurrency must be at least 1")

    semaphore = asyncio.Semaphore(concurrency)
    ordered_results = [None] * len(targets)
    started_at = time.perf_counter()

    async def worker(index: int, target: EndpointTarget) -> None:
        async with semaphore:
            ordered_results[index] = await asyncio.to_thread(fetch_endpoint, target, index)

    await asyncio.gather(*(worker(index, target) for index, target in enumerate(targets)))

    return AuditRun(
        results=list(ordered_results),
        elapsed_time=time.perf_counter() - started_at,
        requested_concurrency=concurrency,
    )


def build_audit_report(audit_run: AuditRun) -> dict:
    return build_report(
        audit_run.results,
        elapsed_time=audit_run.elapsed_time,
        requested_concurrency=audit_run.requested_concurrency,
    )


async def run_audit_from_manifest(
    base_url: str,
    manifest_path: str = "/root/workspace/endpoint_manifest.json",
    concurrency: int = 8,
) -> dict:
    targets = build_targets_from_manifest(base_url=base_url, manifest_path=manifest_path)
    audit_run = await audit_endpoints_async(targets, concurrency=concurrency)
    return build_audit_report(audit_run)
PYTHON_EOF

chmod +x /root/workspace/async_endpoint_audit.py
