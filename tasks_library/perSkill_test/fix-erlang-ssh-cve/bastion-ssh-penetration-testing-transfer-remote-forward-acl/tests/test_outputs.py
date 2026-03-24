import json
import os
import subprocess

import pytest


PRIMARY_OUTPUT = "/app/workspace/src/forwarding/remote_acl.rs"
POLICY_PATH = "/app/workspace/assets/forwarding_policy.json"
BIN_PATH = "/app/workspace/target/debug/acl_probe"

_BUILT = False


def _build_binary() -> None:
    global _BUILT
    if _BUILT:
        return

    proc = subprocess.run(
        ["bash", "-lc", "cd /app/workspace && cargo build --quiet --bin acl_probe"],
        capture_output=True,
        text=True,
        check=False,
        timeout=240,
    )
    assert proc.returncode == 0, (
        "failed to build acl_probe\n"
        f"stdout:\n{proc.stdout}\n"
        f"stderr:\n{proc.stderr}\n"
    )
    _BUILT = True


@pytest.fixture(scope="session", autouse=True)
def _build_once() -> None:
    _build_binary()


def run_case(case_name: str) -> dict:
    request_path = f"/app/workspace/assets/requests/{case_name}.json"
    proc = subprocess.run(
        [BIN_PATH, POLICY_PATH, request_path],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert proc.returncode == 0, (
        f"acl_probe exited with {proc.returncode}\n"
        f"stdout:\n{proc.stdout}\n"
        f"stderr:\n{proc.stderr}\n"
    )
    return json.loads(proc.stdout)


def test_primary_output_file_exists() -> None:
    assert os.path.exists(PRIMARY_OUTPUT), f"missing primary output file: {PRIMARY_OUTPUT}"


def test_allowed_maintenance_tunnels_survive() -> None:
    db = run_case("allowed_db_tunnel")
    metrics = run_case("allowed_metrics_ipv6")

    assert db == {"allowed": True, "reason": "allowed"}
    assert metrics == {"allowed": True, "reason": "allowed"}


def test_public_bind_hosts_are_rejected() -> None:
    public_bind = run_case("blocked_public_bind")
    wildcard_bind = run_case("blocked_wildcard_bind")

    assert public_bind == {"allowed": False, "reason": "bind-host-not-allowed"}
    assert wildcard_bind == {"allowed": False, "reason": "bind-host-not-allowed"}


def test_non_loopback_targets_are_rejected() -> None:
    result = run_case("blocked_internal_target")
    assert result == {"allowed": False, "reason": "target-must-be-loopback"}


def test_unlisted_target_ports_are_rejected() -> None:
    result = run_case("blocked_unlisted_target_port")
    assert result == {"allowed": False, "reason": "target-port-not-allowed"}


def test_unknown_principals_are_rejected() -> None:
    result = run_case("blocked_unknown_principal")
    assert result == {"allowed": False, "reason": "principal-not-allowed"}
