#!/usr/bin/env python3
"""
Sequential baseline implementation for endpoint auditing.
"""

from __future__ import annotations

import time
from urllib import error, request

from endpoint_fixture import (
    AuditResult,
    AuditRun,
    EndpointTarget,
    build_report,
    build_targets_from_manifest,
    inspect_json_payload,
    target_requires_json,
)


def fetch_endpoint(target: EndpointTarget, ordinal: int = 0) -> AuditResult:
    started_at = time.perf_counter()
    req = request.Request(target.url, method="GET", headers={"User-Agent": "endpoint-audit/1.0"})

    try:
        with request.urlopen(req, timeout=target.timeout) as response:
            status_code = response.getcode()
            content_type = response.headers.get("Content-Type", "")
            body = response.read()
    except error.HTTPError as exc:
        status_code = exc.code
        content_type = exc.headers.get("Content-Type", "")
        body = exc.read()
    except (error.URLError, TimeoutError, OSError) as exc:
        latency_ms = (time.perf_counter() - started_at) * 1000.0
        return AuditResult(
            ordinal=ordinal,
            name=target.name,
            url=target.url,
            expected_status=target.expected_status,
            status_code=None,
            latency_ms=latency_ms,
            content_type="",
            response_bytes=0,
            json_category="not_checked",
            missing_fields=(),
            mismatched_values={},
            passed=False,
            error=str(exc),
        )

    latency_ms = (time.perf_counter() - started_at) * 1000.0
    json_category, missing_fields, mismatched_values = inspect_json_payload(target, content_type, body)

    if target_requires_json(target):
        payload_ok = json_category == "valid"
    else:
        payload_ok = json_category in {"valid", "non_json"}

    return AuditResult(
        ordinal=ordinal,
        name=target.name,
        url=target.url,
        expected_status=target.expected_status,
        status_code=status_code,
        latency_ms=latency_ms,
        content_type=content_type,
        response_bytes=len(body),
        json_category=json_category,
        missing_fields=missing_fields,
        mismatched_values=mismatched_values,
        passed=(status_code == target.expected_status) and payload_ok,
    )


def audit_endpoints_sequential(targets: list[EndpointTarget]) -> AuditRun:
    started_at = time.perf_counter()
    results = [fetch_endpoint(target, ordinal=index) for index, target in enumerate(targets)]
    return AuditRun(
        results=results,
        elapsed_time=time.perf_counter() - started_at,
        requested_concurrency=1,
    )


def build_audit_report_sequential(audit_run: AuditRun) -> dict:
    return build_report(
        audit_run.results,
        elapsed_time=audit_run.elapsed_time,
        requested_concurrency=audit_run.requested_concurrency,
    )


def run_audit_from_manifest_sequential(
    base_url: str,
    manifest_path: str = "/root/workspace/endpoint_manifest.json",
) -> dict:
    targets = build_targets_from_manifest(base_url=base_url, manifest_path=manifest_path)
    run = audit_endpoints_sequential(targets)
    return build_audit_report_sequential(run)
