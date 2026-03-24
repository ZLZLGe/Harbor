#!/usr/bin/env python3
"""
Tests for the async endpoint audit transfer task.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

WORKSPACE_DIR = Path(os.environ.get("TASK_WORKSPACE", "/root/workspace"))
sys.path.insert(0, str(WORKSPACE_DIR))

from endpoint_fixture import EndpointTarget, build_targets_from_manifest, percentile_95
from sequential_endpoint_audit import audit_endpoints_sequential


MANIFEST_PATH = WORKSPACE_DIR / "endpoint_manifest.json"


class InstrumentedHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address, handler_class, behaviors):
        super().__init__(server_address, handler_class)
        self.behaviors = behaviors
        self._lock = threading.Lock()
        self.active_requests = 0
        self.max_active_requests = 0

    def request_started(self) -> None:
        with self._lock:
            self.active_requests += 1
            if self.active_requests > self.max_active_requests:
                self.max_active_requests = self.active_requests

    def request_finished(self) -> None:
        with self._lock:
            self.active_requests -= 1

    def reset_stats(self) -> None:
        with self._lock:
            self.active_requests = 0
            self.max_active_requests = 0


class AuditRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        behavior = self.server.behaviors[self.path]
        self.server.request_started()
        try:
            time.sleep(behavior["delay_ms"] / 1000.0)
            body = behavior["body"]
            self.send_response(behavior["status"])
            self.send_header("Content-Type", behavior["content_type"])
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        finally:
            self.server.request_finished()

    def log_message(self, format: str, *args) -> None:
        return


@pytest.fixture()
def manifest_behaviors() -> dict[str, dict]:
    return {
        "/audit/catalog/health": {
            "status": 200,
            "delay_ms": 120,
            "content_type": "application/json",
            "body": json.dumps(
                {"service": "catalog", "status": "ok", "checked_at": "2026-03-22T10:00:00Z"}
            ).encode("utf-8"),
        },
        "/audit/billing/health": {
            "status": 200,
            "delay_ms": 90,
            "content_type": "application/json",
            "body": json.dumps(
                {"service": "billing", "status": "ok", "checked_at": "2026-03-22T10:00:01Z"}
            ).encode("utf-8"),
        },
        "/audit/identity/health": {
            "status": 200,
            "delay_ms": 180,
            "content_type": "application/json",
            "body": json.dumps(
                {"service": "identity", "status": "ok", "checked_at": "2026-03-22T10:00:02Z"}
            ).encode("utf-8"),
        },
        "/audit/ledger/schema": {
            "status": 200,
            "delay_ms": 110,
            "content_type": "application/json",
            "body": json.dumps({"service": "ledger", "status": "ok"}).encode("utf-8"),
        },
        "/audit/search/degraded": {
            "status": 200,
            "delay_ms": 140,
            "content_type": "application/json",
            "body": json.dumps(
                {"service": "search", "status": "degraded", "checked_at": "2026-03-22T10:00:04Z"}
            ).encode("utf-8"),
        },
        "/audit/dashboard/html": {
            "status": 503,
            "delay_ms": 70,
            "content_type": "text/html; charset=utf-8",
            "body": b"<html><body>maintenance</body></html>",
        },
        "/audit/webhook/invalid-json": {
            "status": 200,
            "delay_ms": 160,
            "content_type": "application/json",
            "body": b'{"service": "webhook", "status": "ok", "checked_at": ',
        },
        "/audit/scheduler/health": {
            "status": 200,
            "delay_ms": 100,
            "content_type": "application/json",
            "body": json.dumps(
                {"service": "scheduler", "status": "ok", "checked_at": "2026-03-22T10:00:07Z"}
            ).encode("utf-8"),
        },
    }


@pytest.fixture()
def server(manifest_behaviors):
    httpd = InstrumentedHTTPServer(("127.0.0.1", 0), AuditRequestHandler, manifest_behaviors)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{httpd.server_port}"
    try:
        yield httpd, base_url
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()


class TestAsyncAuditModule:
    def test_async_solution_exists(self) -> None:
        try:
            from async_endpoint_audit import (  # noqa: F401
                audit_endpoints_async,
                build_audit_report,
                run_audit_from_manifest,
            )
        except ImportError as exc:
            pytest.fail(f"Could not import async_endpoint_audit: {exc}")


class TestCorrectnessAndReporting:
    def test_manifest_results_preserve_order_and_summary(self, server) -> None:
        from async_endpoint_audit import audit_endpoints_async, build_audit_report

        httpd, base_url = server
        targets = build_targets_from_manifest(base_url=base_url, manifest_path=MANIFEST_PATH)

        audit_run = asyncio.run(audit_endpoints_async(targets, concurrency=3))
        report = build_audit_report(audit_run)

        assert [result.name for result in audit_run.results] == [target.name for target in targets]
        assert [result.status_code for result in audit_run.results] == [200, 200, 200, 200, 200, 503, 200, 200]
        assert [result.json_category for result in audit_run.results] == [
            "valid",
            "valid",
            "valid",
            "invalid",
            "invalid",
            "non_json",
            "invalid",
            "valid",
        ]

        assert report["requested_concurrency"] == 3
        assert report["total_targets"] == 8
        assert report["status_counts"] == {"200": 7, "503": 1}
        assert report["json_validation"] == {
            "valid": 4,
            "invalid": 3,
            "non_json": 1,
            "not_checked": 0,
        }
        assert report["passed_count"] == 5
        assert report["failed_count"] == 3
        assert [item["name"] for item in report["failures"]] == [
            "ledger-schema",
            "search-degraded",
            "webhook-invalid-json",
        ]
        assert httpd.max_active_requests <= 3

        latencies = [result.latency_ms for result in audit_run.results]
        assert report["latency_ms"]["min"] == pytest.approx(round(min(latencies), 3))
        assert report["latency_ms"]["max"] == pytest.approx(round(max(latencies), 3))
        assert report["latency_ms"]["avg"] == pytest.approx(round(sum(latencies) / len(latencies), 3))
        assert report["latency_ms"]["p95"] == pytest.approx(round(percentile_95(latencies), 3))
        assert report["slowest_targets"][0]["name"] == "identity-health"

    def test_manifest_runner_loads_targets_and_returns_report(self, server) -> None:
        from async_endpoint_audit import run_audit_from_manifest

        httpd, base_url = server
        httpd.reset_stats()

        report = asyncio.run(run_audit_from_manifest(base_url, manifest_path=str(MANIFEST_PATH), concurrency=4))

        assert report["requested_concurrency"] == 4
        assert report["total_targets"] == 8
        assert report["ordered_names"] == [
            "catalog-health",
            "billing-health",
            "identity-health",
            "ledger-schema",
            "search-degraded",
            "dashboard-html",
            "webhook-invalid-json",
            "scheduler-health",
        ]
        assert report["latency_ms"]["elapsed_total"] > 0
        assert httpd.max_active_requests <= 4


class TestPerformance:
    def test_async_audit_is_faster_than_sequential(self) -> None:
        from async_endpoint_audit import audit_endpoints_async

        behaviors: dict[str, dict] = {}
        targets: list[EndpointTarget] = []

        for index in range(24):
            path = f"/perf/service-{index}"
            behaviors[path] = {
                "status": 200,
                "delay_ms": 90,
                "content_type": "application/json",
                "body": json.dumps(
                    {
                        "service": f"perf-{index}",
                        "status": "ok",
                        "checked_at": f"2026-03-22T10:10:{index:02d}Z",
                    }
                ).encode("utf-8"),
            }
            targets.append(
                EndpointTarget(
                    name=f"perf-{index}",
                    url=path,
                    expected_status=200,
                    required_json_fields=("service", "status", "checked_at"),
                    expected_json_values={"service": f"perf-{index}", "status": "ok"},
                    timeout=1.5,
                )
            )

        httpd = InstrumentedHTTPServer(("127.0.0.1", 0), AuditRequestHandler, behaviors)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()

        base_url = f"http://127.0.0.1:{httpd.server_port}"
        bound_targets = [
            EndpointTarget(
                name=target.name,
                url=f"{base_url}{target.url}",
                expected_status=target.expected_status,
                required_json_fields=target.required_json_fields,
                expected_json_values=target.expected_json_values,
                timeout=target.timeout,
            )
            for target in targets
        ]

        try:
            sequential_run = audit_endpoints_sequential(bound_targets)
            httpd.reset_stats()
            async_run = asyncio.run(audit_endpoints_async(bound_targets, concurrency=6))
        finally:
            httpd.shutdown()
            thread.join(timeout=5)
            httpd.server_close()

        assert all(result.passed for result in async_run.results)
        assert [result.name for result in async_run.results] == [target.name for target in bound_targets]
        assert httpd.max_active_requests <= 6

        speedup = sequential_run.elapsed_time / async_run.elapsed_time
        print(f"\nSequential elapsed: {sequential_run.elapsed_time:.3f}s")
        print(f"Async elapsed:      {async_run.elapsed_time:.3f}s")
        print(f"Speedup:            {speedup:.2f}x")

        assert speedup >= 2.5, f"Insufficient speedup: {speedup:.2f}x"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
