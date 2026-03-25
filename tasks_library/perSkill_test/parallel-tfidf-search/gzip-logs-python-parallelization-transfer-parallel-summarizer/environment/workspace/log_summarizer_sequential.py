#!/usr/bin/env python3

from __future__ import annotations

import gzip
import json
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path


SIGNATURE_MODULUS = 1_000_000_007
SIGNATURE_ROUNDS = 24


@dataclass
class FileDigest:
    filename: str
    service: str
    shard: str
    record_count: int
    error_count: int
    total_latency_ms: int
    max_latency_ms: int
    total_bytes_out: int
    signature_accumulator: int
    top_error_code: str
    distinct_error_codes: int


@dataclass
class LogSummaryResult:
    file_digests: list[FileDigest]
    report: dict
    elapsed_time: float
    num_workers: int


def load_manifest(manifest_path: str | Path) -> dict:
    return json.loads(Path(manifest_path).read_text(encoding="utf-8"))


def parse_log_line(raw_line: str) -> dict:
    (
        timestamp,
        service,
        shard,
        host,
        status_text,
        error_code,
        latency_text,
        bytes_text,
        path,
        request_id,
        client_id,
    ) = raw_line.rstrip("\n").split("|")
    return {
        "timestamp": timestamp,
        "service": service,
        "shard": shard,
        "host": host,
        "status": int(status_text),
        "error_code": error_code,
        "latency_ms": int(latency_text),
        "bytes_out": int(bytes_text),
        "path": path,
        "request_id": request_id,
        "client_id": client_id,
    }


def stable_signature(*parts: str) -> int:
    value = 0
    joined = "|".join(parts)
    for round_index in range(SIGNATURE_ROUNDS):
        for character in joined:
            value = (value * 131 + ord(character) + round_index) % SIGNATURE_MODULUS
    return value


def summarize_single_gzip_file(log_dir: str | Path, entry: dict) -> dict:
    file_path = Path(log_dir) / entry["filename"]
    error_counts: Counter[str] = Counter()
    record_count = 0
    error_count = 0
    total_latency_ms = 0
    max_latency_ms = 0
    total_bytes_out = 0
    signature_accumulator = 0

    with gzip.open(file_path, "rt", encoding="utf-8") as handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue
            record = parse_log_line(raw_line)
            record_count += 1
            total_latency_ms += record["latency_ms"]
            total_bytes_out += record["bytes_out"]
            max_latency_ms = max(max_latency_ms, record["latency_ms"])
            signature_accumulator = (
                signature_accumulator
                + stable_signature(
                    record["path"],
                    record["request_id"],
                    record["client_id"],
                    record["host"],
                    str(record["status"]),
                )
            ) % SIGNATURE_MODULUS
            if record["error_code"] != "OK":
                error_count += 1
                error_counts[record["error_code"]] += 1

    top_error_code = "OK"
    if error_counts:
        top_error_code = sorted(error_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]

    digest = FileDigest(
        filename=entry["filename"],
        service=entry["service"],
        shard=entry["shard"],
        record_count=record_count,
        error_count=error_count,
        total_latency_ms=total_latency_ms,
        max_latency_ms=max_latency_ms,
        total_bytes_out=total_bytes_out,
        signature_accumulator=signature_accumulator,
        top_error_code=top_error_code,
        distinct_error_codes=len(error_counts),
    )
    return {
        "digest": digest,
        "error_counts": dict(error_counts),
    }


def build_report(manifest: dict, partial_results: list[dict]) -> dict:
    service_totals = {
        service: {
            "requests": 0,
            "errors": 0,
            "total_latency_ms": 0,
            "max_latency_ms": 0,
            "total_bytes_out": 0,
            "signature_accumulator": 0,
            "error_counts": Counter(),
        }
        for service in manifest["services"]
    }
    global_error_counts: Counter[str] = Counter()
    global_error_services: defaultdict[str, set[str]] = defaultdict(set)
    digests = [partial["digest"] for partial in partial_results]

    for partial in partial_results:
        digest = partial["digest"]
        totals = service_totals[digest.service]
        totals["requests"] += digest.record_count
        totals["errors"] += digest.error_count
        totals["total_latency_ms"] += digest.total_latency_ms
        totals["max_latency_ms"] = max(totals["max_latency_ms"], digest.max_latency_ms)
        totals["total_bytes_out"] += digest.total_bytes_out
        totals["signature_accumulator"] = (
            totals["signature_accumulator"] + digest.signature_accumulator
        ) % SIGNATURE_MODULUS

        for error_code, count in partial["error_counts"].items():
            totals["error_counts"][error_code] += count
            global_error_counts[error_code] += count
            global_error_services[error_code].add(digest.service)

    service_summary = []
    for service in manifest["services"]:
        totals = service_totals[service]
        average_latency = 0.0
        if totals["requests"]:
            average_latency = round(totals["total_latency_ms"] / totals["requests"], 3)

        top_error_code = "OK"
        if totals["error_counts"]:
            top_error_code = sorted(
                totals["error_counts"].items(),
                key=lambda item: (-item[1], item[0]),
            )[0][0]

        service_summary.append(
            {
                "service": service,
                "requests": totals["requests"],
                "errors": totals["errors"],
                "avg_latency_ms": average_latency,
                "max_latency_ms": totals["max_latency_ms"],
                "total_bytes_out": totals["total_bytes_out"],
                "top_error_code": top_error_code,
                "signature_accumulator": totals["signature_accumulator"],
            }
        )

    error_code_summary = [
        {
            "error_code": error_code,
            "count": count,
            "services": sorted(global_error_services[error_code]),
        }
        for error_code, count in sorted(global_error_counts.items(), key=lambda item: (-item[1], item[0]))
    ]

    hot_files = [
        {
            "filename": digest.filename,
            "service": digest.service,
            "error_count": digest.error_count,
            "max_latency_ms": digest.max_latency_ms,
            "signature_accumulator": digest.signature_accumulator,
        }
        for digest in sorted(
            digests,
            key=lambda item: (-item.error_count, -item.max_latency_ms, item.filename),
        )[:5]
    ]

    return {
        "dataset_id": manifest["dataset_id"],
        "file_count": len(digests),
        "record_count": sum(digest.record_count for digest in digests),
        "service_summary": service_summary,
        "error_code_summary": error_code_summary,
        "hot_files": hot_files,
    }


def summarize_gzip_logs_sequential(
    log_dir: str | Path = "/root/workspace/gzip_logs",
    manifest_path: str | Path = "/root/workspace/log_manifest.json",
) -> LogSummaryResult:
    manifest = load_manifest(manifest_path)
    start_time = time.perf_counter()

    partial_results = [
        summarize_single_gzip_file(log_dir, entry)
        for entry in manifest["files"]
    ]
    elapsed_time = time.perf_counter() - start_time

    return LogSummaryResult(
        file_digests=[partial["digest"] for partial in partial_results],
        report=build_report(manifest, partial_results),
        elapsed_time=elapsed_time,
        num_workers=1,
    )


def write_summary_report_sequential(
    log_dir: str | Path = "/root/workspace/gzip_logs",
    manifest_path: str | Path = "/root/workspace/log_manifest.json",
    output_path: str | Path = "/root/workspace/log_summary_report.json",
) -> dict:
    result = summarize_gzip_logs_sequential(log_dir=log_dir, manifest_path=manifest_path)
    Path(output_path).write_text(json.dumps(result.report, indent=2), encoding="utf-8")
    return result.report


def file_digests_as_dicts(file_digests: list[FileDigest]) -> list[dict]:
    return [asdict(file_digest) for file_digest in file_digests]


__all__ = [
    "FileDigest",
    "LogSummaryResult",
    "build_report",
    "file_digests_as_dicts",
    "load_manifest",
    "parse_log_line",
    "stable_signature",
    "summarize_gzip_logs_sequential",
    "summarize_single_gzip_file",
    "write_summary_report_sequential",
]
