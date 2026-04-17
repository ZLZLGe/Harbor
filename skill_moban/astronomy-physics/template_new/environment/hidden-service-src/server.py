#!/usr/bin/env python3
import csv
import hashlib
import json
import logging
import math
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 8124
TRACE_PATH = Path("/tmp/observatory_api_trace.jsonl")
LAST_AUDIT_PATH = Path("/tmp/observatory_last_audit.json")
CATALOG_PATH = Path("/app/data/target_catalog.json")
DATA_ROOT = Path("/app/data/targets")


def must_load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def manifests_for(snapshot_id: str) -> dict[str, dict]:
    return {
        "TIC-220039452": {
            "target_id": "TIC-220039452",
            "snapshot_id": snapshot_id,
            "rotation_scan_days": [5.5, 9.5],
            "search_period_days": [1.2, 8.5],
            "duration_search_hours": [1.5, 5.0],
            "flatten_window_cadences": 241,
            "eb_ratio_threshold": 1.60,
            "secondary_eclipse_snr_threshold": 6.0,
            "quarantine_windows_mjd": [
                [2154.732, 2154.804],
                [2164.418, 2164.492],
            ],
            "total_cadences": 16200,
        },
        "TIC-146712781": {
            "target_id": "TIC-146712781",
            "snapshot_id": snapshot_id,
            "rotation_scan_days": [6.0, 11.5],
            "search_period_days": [1.2, 8.5],
            "duration_search_hours": [2.0, 6.0],
            "flatten_window_cadences": 241,
            "eb_ratio_threshold": 1.60,
            "secondary_eclipse_snr_threshold": 6.0,
            "quarantine_windows_mjd": [
                [2158.110, 2158.175],
            ],
            "total_cadences": 16200,
        },
        "TIC-381920550": {
            "target_id": "TIC-381920550",
            "snapshot_id": snapshot_id,
            "rotation_scan_days": [4.5, 8.5],
            "search_period_days": [1.2, 8.5],
            "duration_search_hours": [2.0, 5.5],
            "flatten_window_cadences": 241,
            "eb_ratio_threshold": 1.60,
            "secondary_eclipse_snr_threshold": 6.0,
            "quarantine_windows_mjd": [
                [2149.230, 2149.278],
            ],
            "total_cadences": 16200,
        },
        "TIC-440119211": {
            "target_id": "TIC-440119211",
            "snapshot_id": snapshot_id,
            "rotation_scan_days": [7.0, 11.5],
            "search_period_days": [1.2, 8.5],
            "duration_search_hours": [2.0, 5.5],
            "flatten_window_cadences": 241,
            "eb_ratio_threshold": 1.60,
            "secondary_eclipse_snr_threshold": 6.0,
            "quarantine_windows_mjd": [
                [2156.201, 2156.285],
                [2167.184, 2167.252],
            ],
            "total_cadences": 16200,
        },
    }


def expectations() -> dict[str, dict]:
    return {
        "TIC-220039452": {
            "rotation_days": 7.376,
            "rotation_tol": 0.45,
            "period_days": 3.28471,
            "period_tol": 0.035,
            "epoch_mjd": 2145.4317,
            "epoch_tol": 0.09,
            "duration_hours_min": 2.0,
            "duration_hours_max": 4.2,
            "depth_ppm_min": 250.0,
            "depth_ppm_max": 1500.0,
            "min_transit_snr": 12.0,
            "min_transit_count": 6,
            "verdict": "planet_candidate",
            "max_odd_even_ratio": 1.55,
            "max_secondary_snr": 5.5,
        },
        "TIC-146712781": {
            "rotation_days": 8.908,
            "rotation_tol": 0.65,
            "period_days": 6.41260,
            "period_tol": 0.10,
            "epoch_mjd": 2146.0180,
            "epoch_tol": 0.12,
            "duration_hours_min": 3.0,
            "duration_hours_max": 5.5,
            "depth_ppm_min": 150.0,
            "depth_ppm_max": 5000.0,
            "min_transit_snr": 10.0,
            "min_transit_count": 3,
            "verdict": "eclipsing_binary",
            "min_odd_even_ratio": 1.60,
        },
        "TIC-381920550": {
            "rotation_days": 6.246,
            "rotation_tol": 0.55,
            "period_days": 4.88710,
            "period_tol": 0.10,
            "epoch_mjd": 2145.9820,
            "epoch_tol": 0.12,
            "duration_hours_min": 2.8,
            "duration_hours_max": 4.6,
            "depth_ppm_min": 400.0,
            "depth_ppm_max": 4000.0,
            "min_transit_snr": 10.0,
            "min_transit_count": 4,
            "verdict": "eclipsing_binary",
            "min_odd_even_ratio": 1.60,
            "min_secondary_snr": 6.0,
        },
        "TIC-440119211": {
            "rotation_days": 9.364,
            "rotation_tol": 0.70,
            "period_days": 5.78134,
            "period_tol": 0.04,
            "epoch_mjd": 2144.9321,
            "epoch_tol": 0.10,
            "duration_hours_min": 2.6,
            "duration_hours_max": 4.5,
            "depth_ppm_min": 300.0,
            "depth_ppm_max": 1800.0,
            "min_transit_snr": 12.0,
            "min_transit_count": 3,
            "verdict": "planet_candidate",
            "max_odd_even_ratio": 1.55,
            "max_secondary_snr": 5.5,
        },
    }


def load_counts(manifests: dict[str, dict]) -> dict[str, dict]:
    counts: dict[str, dict] = {}
    for target_id, manifest in manifests.items():
        total = 0
        quality_removed = 0
        quarantine_removed = 0
        quality_used = 0
        target_root = DATA_ROOT / target_id
        for path in sorted(target_root.glob("*.csv")):
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    total += 1
                    time_val = float(row["time_mjd"])
                    quality_flag = int(row["quality_flag"])
                    if quality_flag != 0:
                        quality_removed += 1
                        continue
                    in_quarantine = any(
                        lower <= time_val <= upper
                        for lower, upper in manifest["quarantine_windows_mjd"]
                    )
                    if in_quarantine:
                        quarantine_removed += 1
                    else:
                        quality_used += 1
        if total != manifest["total_cadences"]:
            raise RuntimeError(
                f"unexpected total cadences for {target_id}: got {total} want {manifest['total_cadences']}"
            )
        counts[target_id] = {
            "quality_removed": quality_removed,
            "quarantine_removed": quarantine_removed,
            "quality_used": quality_used,
        }
    return counts


def canonical_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonicalize_json(raw: bytes) -> bytes:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        return raw
    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def wrap_epoch_delta(epoch: float, reference: float, period: float) -> float:
    if period <= 0:
        return abs(epoch - reference)
    delta = math.fmod(epoch - reference, period)
    if delta < 0:
        delta += period
    return min(delta, period - delta)


def as_float(entry: dict, key: str) -> float:
    try:
        return float(entry.get(key, 0.0))
    except (TypeError, ValueError):
        return 0.0


def as_int(entry: dict, key: str) -> int:
    try:
        return int(entry.get(key, 0))
    except (TypeError, ValueError):
        return 0


def as_str(entry: dict, key: str) -> str:
    value = entry.get(key, "")
    return value if isinstance(value, str) else str(value)


class ObservatoryState:
    def __init__(self) -> None:
        self.catalog = must_load_catalog()
        snapshot_id = self.catalog["snapshot_id"]
        self.manifests = manifests_for(snapshot_id)
        self.expectations = expectations()
        self.counts = load_counts(self.manifests)
        self.trace_lock = threading.Lock()

    def write_trace(self, payload: dict) -> None:
        with self.trace_lock:
            with TRACE_PATH.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def validate_report(self, report: dict, raw: bytes) -> dict:
        problems: list[str] = []
        if report.get("snapshot_id") != self.catalog["snapshot_id"]:
            problems.append(f"snapshot_id mismatch: got {report.get('snapshot_id')}")

        entries = report.get("entries")
        if not isinstance(entries, list):
            entries = []
            problems.append("entries must be a list")

        if len(entries) != len(self.catalog["targets"]):
            problems.append(
                f"expected {len(self.catalog['targets'])} entries, got {len(entries)}"
            )

        target_seen: dict[str, bool] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                problems.append("entry is not a JSON object")
                continue
            target_id = as_str(entry, "target_id")
            target_seen[target_id] = True
            expectation = self.expectations.get(target_id)
            if expectation is None:
                problems.append(f"{target_id}: unknown target")
                continue

            manifest = self.manifests[target_id]
            counts = self.counts[target_id]

            if abs(as_float(entry, "rotation_alias_days") - expectation["rotation_days"]) > expectation["rotation_tol"]:
                problems.append(f"{target_id}: rotation_alias_days outside tolerance")
            if abs(as_float(entry, "transit_period_days") - expectation["period_days"]) > expectation["period_tol"]:
                problems.append(f"{target_id}: transit_period_days outside tolerance")
            if wrap_epoch_delta(
                as_float(entry, "transit_epoch_mjd"),
                expectation["epoch_mjd"],
                expectation["period_days"],
            ) > expectation["epoch_tol"]:
                problems.append(f"{target_id}: transit_epoch_mjd outside tolerance")
            duration_hours = as_float(entry, "duration_hours")
            if duration_hours < expectation["duration_hours_min"] or duration_hours > expectation["duration_hours_max"]:
                problems.append(f"{target_id}: duration_hours outside expected range")
            depth_ppm = as_float(entry, "depth_ppm")
            if depth_ppm < expectation["depth_ppm_min"] or depth_ppm > expectation["depth_ppm_max"]:
                problems.append(f"{target_id}: depth_ppm outside expected range")
            if as_float(entry, "transit_snr") < expectation["min_transit_snr"]:
                problems.append(f"{target_id}: transit_snr too low")
            if as_int(entry, "transit_count") < expectation["min_transit_count"]:
                problems.append(f"{target_id}: transit_count too low")
            if as_str(entry, "verdict") != expectation["verdict"]:
                problems.append(f"{target_id}: wrong verdict")
            if as_int(entry, "quality_points_removed") != counts["quality_removed"]:
                problems.append(f"{target_id}: quality_points_removed mismatch")
            if as_int(entry, "quarantine_points_removed") != counts["quarantine_removed"]:
                problems.append(f"{target_id}: quarantine_points_removed mismatch")
            if as_int(entry, "quality_points_used") != counts["quality_used"]:
                problems.append(f"{target_id}: quality_points_used mismatch")
            if (
                as_int(entry, "quality_points_used")
                + as_int(entry, "quality_points_removed")
                + as_int(entry, "quarantine_points_removed")
                != manifest["total_cadences"]
            ):
                problems.append(f"{target_id}: cadence accounting mismatch")
            if len(as_str(entry, "verdict_reason").strip()) < 40:
                problems.append(f"{target_id}: verdict_reason too short")

            odd_even = as_float(entry, "odd_even_depth_ratio")
            if expectation.get("max_odd_even_ratio", 0.0) > 0 and odd_even > expectation["max_odd_even_ratio"]:
                problems.append(f"{target_id}: odd_even_depth_ratio too large for planet candidate")
            if expectation.get("min_odd_even_ratio", 0.0) > 0 and odd_even < expectation["min_odd_even_ratio"]:
                problems.append(f"{target_id}: odd_even_depth_ratio too small for eclipsing binary")

            secondary_snr = as_float(entry, "secondary_eclipse_snr")
            if expectation.get("max_secondary_snr", 0.0) > 0 and secondary_snr > expectation["max_secondary_snr"]:
                problems.append(f"{target_id}: secondary_eclipse_snr too large for planet candidate")
            if expectation.get("min_secondary_snr", 0.0) > 0 and secondary_snr < expectation["min_secondary_snr"]:
                problems.append(f"{target_id}: secondary_eclipse_snr too small for eclipsing binary")

        for target in self.catalog["targets"]:
            target_id = target["target_id"]
            if not target_seen.get(target_id, False):
                problems.append(f"missing target {target_id}")

        accepted = not problems
        response = {
            "accepted": accepted,
            "accepted_targets": len(entries),
            "problems": problems,
            "snapshot_id": self.catalog["snapshot_id"],
            "status": "accepted" if accepted else "rejected",
        }

        payload_sha = canonical_sha256(canonicalize_json(raw))
        self.write_trace(
            {
                "event": "audit",
                "snapshot_id": self.catalog["snapshot_id"],
                "payload_sha256": payload_sha,
                "accepted": accepted,
            }
        )
        LAST_AUDIT_PATH.write_text(
            json.dumps(
                {
                    "payload_sha256": payload_sha,
                    "accepted": accepted,
                    "problems": problems,
                    "snapshot_id": self.catalog["snapshot_id"],
                    "status": response["status"],
                },
                indent=2,
                ensure_ascii=True,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return response


STATE = ObservatoryState()


class ObservatoryHandler(BaseHTTPRequestHandler):
    server_version = "observatory-api/1.0"

    def _write_json(self, status_code: int, payload: dict) -> None:
        encoded = json.dumps(payload, ensure_ascii=True).encode("utf-8") + b"\n"
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt: str, *args) -> None:
        logging.info("%s - %s", self.address_string(), fmt % args)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._write_json(200, {"ok": True})
            return
        if self.path == "/catalog":
            STATE.write_trace(
                {
                    "event": "catalog",
                    "snapshot_id": STATE.catalog["snapshot_id"],
                }
            )
            self._write_json(200, STATE.catalog)
            return
        if self.path.startswith("/manifest/"):
            target_id = self.path.split("/manifest/", 1)[1]
            manifest = STATE.manifests.get(target_id)
            if manifest is None:
                self._write_json(404, {"error": "unknown target"})
                return
            STATE.write_trace(
                {
                    "event": "manifest",
                    "snapshot_id": STATE.catalog["snapshot_id"],
                    "target_id": target_id,
                }
            )
            self._write_json(200, manifest)
            return
        self._write_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/audit":
            self._write_json(404, {"error": "not found"})
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length)
        try:
            report = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            self._write_json(400, {"error": str(exc)})
            return
        if not isinstance(report, dict):
            self._write_json(400, {"error": "report must be a JSON object"})
            return
        response = STATE.validate_report(report, raw)
        status_code = 200 if response["accepted"] else 422
        self._write_json(status_code, response)


def main() -> None:
    TRACE_PATH.unlink(missing_ok=True)
    LAST_AUDIT_PATH.unlink(missing_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), ObservatoryHandler)
    logging.info("observatory API listening on %s:%s", LISTEN_HOST, LISTEN_PORT)
    server.serve_forever()


if __name__ == "__main__":
    main()
