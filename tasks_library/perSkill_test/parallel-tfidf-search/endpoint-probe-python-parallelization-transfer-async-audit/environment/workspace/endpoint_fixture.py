#!/usr/bin/env python3
"""
Shared data models and helpers for the endpoint audit task.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EndpointTarget:
    name: str
    url: str
    expected_status: int = 200
    required_json_fields: tuple[str, ...] = ()
    expected_json_values: dict[str, Any] = field(default_factory=dict)
    timeout: float = 1.5


@dataclass
class AuditResult:
    ordinal: int
    name: str
    url: str
    expected_status: int
    status_code: int | None
    latency_ms: float
    content_type: str
    response_bytes: int
    json_category: str
    missing_fields: tuple[str, ...]
    mismatched_values: dict[str, tuple[Any, Any]]
    passed: bool
    error: str | None = None


@dataclass
class AuditRun:
    results: list[AuditResult]
    elapsed_time: float
    requested_concurrency: int


def build_targets_from_manifest(
    base_url: str,
    manifest_path: str | Path = "/root/workspace/endpoint_manifest.json",
) -> list[EndpointTarget]:
    manifest = json.loads(Path(manifest_path).read_text())
    base = base_url.rstrip("/")
    targets: list[EndpointTarget] = []

    for item in manifest:
        targets.append(
            EndpointTarget(
                name=item["name"],
                url=f"{base}{item['path']}",
                expected_status=item.get("expected_status", 200),
                required_json_fields=tuple(item.get("required_json_fields", [])),
                expected_json_values=dict(item.get("expected_json_values", {})),
                timeout=float(item.get("timeout", 1.5)),
            )
        )

    return targets


def target_requires_json(target: EndpointTarget) -> bool:
    return bool(target.required_json_fields or target.expected_json_values)


def inspect_json_payload(
    target: EndpointTarget,
    content_type: str,
    body: bytes,
) -> tuple[str, tuple[str, ...], dict[str, tuple[Any, Any]]]:
    if "json" not in content_type.lower():
        return "non_json", (), {}

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "invalid", (), {}

    if not isinstance(payload, dict):
        return "invalid", tuple(sorted(set(target.required_json_fields))), {}

    missing_fields = {field_name for field_name in target.required_json_fields if field_name not in payload}
    mismatched_values: dict[str, tuple[Any, Any]] = {}

    for field_name, expected_value in target.expected_json_values.items():
        if field_name not in payload:
            missing_fields.add(field_name)
            continue
        actual_value = payload[field_name]
        if actual_value != expected_value:
            mismatched_values[field_name] = (actual_value, expected_value)

    category = "valid" if not missing_fields and not mismatched_values else "invalid"
    return category, tuple(sorted(missing_fields)), mismatched_values


def result_failure_reason(result: AuditResult) -> str:
    if result.error:
        return result.error

    parts: list[str] = []

    if result.status_code != result.expected_status:
        parts.append(f"expected status {result.expected_status}, got {result.status_code}")

    if result.json_category == "invalid":
        if result.missing_fields:
            parts.append(f"missing fields: {', '.join(result.missing_fields)}")
        if result.mismatched_values:
            mismatch_text = ", ".join(
                f"{key}={actual!r} expected {expected!r}"
                for key, (actual, expected) in sorted(result.mismatched_values.items())
            )
            parts.append(f"mismatched values: {mismatch_text}")
        if not result.missing_fields and not result.mismatched_values:
            parts.append("invalid JSON payload")

    return "; ".join(parts) if parts else "audit failed"


def percentile_95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return ordered[index]


def build_report(
    results: list[AuditResult],
    elapsed_time: float,
    requested_concurrency: int,
    slowest_count: int = 5,
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    json_validation = {
        "valid": 0,
        "invalid": 0,
        "non_json": 0,
        "not_checked": 0,
    }
    failures: list[dict[str, Any]] = []
    latencies = [result.latency_ms for result in results]

    for result in results:
        status_key = "error" if result.status_code is None else str(result.status_code)
        status_counts[status_key] = status_counts.get(status_key, 0) + 1
        json_validation[result.json_category] = json_validation.get(result.json_category, 0) + 1

        if not result.passed:
            failures.append(
                {
                    "name": result.name,
                    "status_code": result.status_code,
                    "reason": result_failure_reason(result),
                }
            )

    slowest_targets = [
        {
            "name": result.name,
            "status_code": result.status_code,
            "latency_ms": round(result.latency_ms, 3),
        }
        for result in sorted(results, key=lambda item: (-item.latency_ms, item.ordinal))[:slowest_count]
    ]

    return {
        "requested_concurrency": requested_concurrency,
        "total_targets": len(results),
        "passed_count": sum(1 for result in results if result.passed),
        "failed_count": sum(1 for result in results if not result.passed),
        "status_counts": status_counts,
        "json_validation": json_validation,
        "latency_ms": {
            "min": round(min(latencies), 3) if latencies else 0.0,
            "max": round(max(latencies), 3) if latencies else 0.0,
            "avg": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
            "p95": round(percentile_95(latencies), 3) if latencies else 0.0,
            "elapsed_total": round(elapsed_time * 1000.0, 3),
        },
        "ordered_names": [result.name for result in results],
        "slowest_targets": slowest_targets,
        "failures": failures,
    }
