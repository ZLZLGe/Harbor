from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import duckdb
import pandas as pd
import requests


TASK_ROOT = Path("/app")
TESTS_ROOT = Path("/tests")
WORKSPACE_ROOT = Path("/app/workspace")
DATA_ROOT = WORKSPACE_ROOT / "data" / "raw"
OUTPUT_ROOT = Path("/app/output")
WAREHOUSE_PATH = OUTPUT_ROOT / "warehouse.duckdb"
BUNDLE_PATH = OUTPUT_ROOT / "publish_bundle.json"
RECEIPT_PATH = OUTPUT_ROOT / "publish_receipt.json"
TRACE_PATH = Path("/tmp/marketplace_audit_trace.jsonl")
LAST_PUBLISH_PATH = Path("/tmp/marketplace_last_publish.json")
API_URL = os.environ.get("PUBLISH_AUDIT_URL", "http://127.0.0.1:8331")
SERVICE_PATH = Path("/services/audit-service/server.pyc")
SERVICE_BINARY_PATH = Path("/services/audit-service/server.bin")

sys.path.insert(0, str(WORKSPACE_ROOT))


def ensure_service() -> None:
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            return
    except requests.RequestException:
        pass

    proc = subprocess.Popen(
        ["python3", str(SERVICE_PATH)],
        stdout=open("/tmp/marketplace-audit.log", "a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    for _ in range(40):
        try:
            response = requests.get(f"{API_URL}/health", timeout=5)
            if response.status_code == 200:
                return
        except requests.RequestException:
            time.sleep(0.5)
    proc.terminate()
    raise AssertionError("publish audit service did not start")


def canonical_json_sha(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_table(path: Path, table_name: str, order_by: list[str]) -> pd.DataFrame:
    with duckdb.connect(str(path), read_only=True) as conn:
        return conn.execute(
            f"SELECT * FROM {table_name} ORDER BY {', '.join(order_by)}"
        ).fetchdf()


def protected_file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return int(sock.getsockname()[1])


@contextmanager
def running_audit_service(data_root: Path, output_root: Path):
    port = _pick_free_port()
    trace_path = output_root / "audit-trace.jsonl"
    publish_path = output_root / "last-publish.json"
    log_path = output_root / "audit-service.log"
    output_root.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update(
        {
            "MARKETPLACE_DATA_ROOT": str(data_root),
            "MARKETPLACE_OUTPUT_ROOT": str(output_root),
            "MARKETPLACE_AUDIT_TRACE_PATH": str(trace_path),
            "MARKETPLACE_LAST_PUBLISH_PATH": str(publish_path),
            "MARKETPLACE_AUDIT_PORT": str(port),
        }
    )
    proc = subprocess.Popen(
        ["python3", str(SERVICE_PATH)],
        env=env,
        stdout=open(log_path, "a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    api_url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(80):
            try:
                response = requests.get(f"{api_url}/health", timeout=5)
                if response.status_code == 200:
                    yield {
                        "api_url": api_url,
                        "trace_path": trace_path,
                        "last_publish_path": publish_path,
                        "log_path": log_path,
                    }
                    break
            except requests.RequestException:
                time.sleep(0.25)
        else:
            raise AssertionError(f"temporary audit service did not start; see {log_path}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def build_and_publish(data_root: Path, warehouse_path: Path, api_url: str) -> tuple[dict, dict]:
    from marketplace_snapshot.pipeline import build_warehouse
    from marketplace_snapshot.publish import build_publish_bundle, publish_bundle

    build_warehouse(data_root=data_root, warehouse_path=warehouse_path)
    bundle = build_publish_bundle(warehouse_path=warehouse_path, api_url=api_url)
    receipt = publish_bundle(bundle, api_url=api_url)
    return bundle, receipt
