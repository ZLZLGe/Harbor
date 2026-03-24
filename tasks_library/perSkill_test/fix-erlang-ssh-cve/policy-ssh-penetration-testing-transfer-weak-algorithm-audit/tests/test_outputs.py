import os
import sys


PRIMARY_OUTPUT = "/app/workspace/policy/renderers/sshd_policy.py"
SITE_POLICY = "/app/workspace/policy/assets/site_policy.json"

sys.path.insert(0, "/app/workspace")

from policy.renderers.sshd_policy import build_audit_report, load_site_policy


def _find_entry(report: dict, kind: str, algorithm: str) -> dict:
    for item in report["findings"]:
        if item["kind"] == kind and item["algorithm"] == algorithm:
            return item
    raise AssertionError(f"missing finding for {kind}:{algorithm}")


def _parse_directive(config: str, directive: str) -> list[str]:
    prefix = f"{directive} "
    for line in config.splitlines():
        if line.startswith(prefix):
            return [part for part in line[len(prefix) :].split(",") if part]
    raise AssertionError(f"missing directive {directive}")


def test_primary_output_file_exists() -> None:
    assert os.path.exists(PRIMARY_OUTPUT), f"missing primary output file: {PRIMARY_OUTPUT}"


def test_weak_algorithms_are_marked_non_compliant() -> None:
    report = build_audit_report(SITE_POLICY)

    weak_cases = [
        ("kex", "diffie-hellman-group14-sha1"),
        ("kex", "diffie-hellman-group1-sha1"),
        ("ciphers", "aes256-cbc"),
        ("ciphers", "3des-cbc"),
        ("macs", "hmac-sha1"),
        ("macs", "hmac-md5"),
    ]
    for kind, algorithm in weak_cases:
        entry = _find_entry(report, kind, algorithm)
        assert entry["compliant"] is False, f"{kind}:{algorithm} should be blocked, got {entry}"


def test_rendered_config_keeps_modern_compatibility() -> None:
    policy = load_site_policy(SITE_POLICY)
    report = build_audit_report(SITE_POLICY)
    config = report["config"]

    assert f"Port {policy['service']['port']}" in config
    assert f"ListenAddress {policy['service']['listen_address']}" in config

    kex_algorithms = _parse_directive(config, "KexAlgorithms")
    cipher_algorithms = _parse_directive(config, "Ciphers")
    mac_algorithms = _parse_directive(config, "MACs")

    assert "curve25519-sha256" in kex_algorithms
    assert "diffie-hellman-group14-sha256" in kex_algorithms
    assert "chacha20-poly1305@openssh.com" in cipher_algorithms
    assert "aes128-ctr" in cipher_algorithms
    assert "aes256-gcm@openssh.com" in cipher_algorithms
    assert "hmac-sha2-256" in mac_algorithms
    assert "hmac-sha2-512-etm@openssh.com" in mac_algorithms


def test_rendered_config_drops_weak_algorithm_entries() -> None:
    config = build_audit_report(SITE_POLICY)["config"]
    kex_algorithms = _parse_directive(config, "KexAlgorithms")
    cipher_algorithms = _parse_directive(config, "Ciphers")
    mac_algorithms = _parse_directive(config, "MACs")

    assert "diffie-hellman-group14-sha1" not in kex_algorithms
    assert "diffie-hellman-group1-sha1" not in kex_algorithms
    assert "aes256-cbc" not in cipher_algorithms
    assert "3des-cbc" not in cipher_algorithms
    assert "hmac-sha1" not in mac_algorithms
    assert "hmac-md5" not in mac_algorithms
