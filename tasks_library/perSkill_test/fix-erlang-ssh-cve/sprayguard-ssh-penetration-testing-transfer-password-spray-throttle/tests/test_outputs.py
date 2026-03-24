import os
import sys


PRIMARY_OUTPUT = "/app/workspace/bastion/auth/failure_tracker.py"

sys.path.insert(0, "/app/workspace")

from bastion.auth.failure_tracker import FailureTracker
from bastion.auth.service import BastionAuthService


def build_service() -> BastionAuthService:
    tracker = FailureTracker(max_failures=3, window_seconds=30.0, cooldown_seconds=90.0)
    credentials = {
        "alice": "amber-vault",
        "bob": "cinder-lake",
        "carol": "harbor-night",
        "diana": "quiet-signal",
    }
    return BastionAuthService(credentials, tracker)


def test_primary_output_file_exists() -> None:
    assert os.path.exists(PRIMARY_OUTPUT), f"missing primary output file: {PRIMARY_OUTPUT}"


def test_password_spray_is_blocked_across_reconnects() -> None:
    service = build_service()
    remote_addr = "203.0.113.44"

    first = service.authenticate(
        connection_id="conn-1",
        remote_addr=remote_addr,
        username="alice",
        password="Winter2026!",
        now=1000.0,
    )
    assert first.allowed is False
    assert first.reason == "invalid-credentials"
    service.disconnect("conn-1")

    second = service.authenticate(
        connection_id="conn-2",
        remote_addr=remote_addr,
        username="bob",
        password="Winter2026!",
        now=1005.0,
    )
    assert second.allowed is False
    assert second.reason == "invalid-credentials"
    service.disconnect("conn-2")

    third = service.authenticate(
        connection_id="conn-3",
        remote_addr=remote_addr,
        username="carol",
        password="Winter2026!",
        now=1010.0,
    )
    assert third.allowed is False
    assert third.reason == "blocked"
    service.disconnect("conn-3")

    blocked = service.authenticate(
        connection_id="conn-4",
        remote_addr=remote_addr,
        username="diana",
        password="quiet-signal",
        now=1012.0,
    )
    assert blocked.allowed is False
    assert blocked.reason == "blocked"


def test_lockout_is_scoped_to_the_attacking_source() -> None:
    service = build_service()
    attacker = "203.0.113.44"

    for index, username in enumerate(["alice", "bob", "carol"], start=1):
        service.authenticate(
            connection_id=f"spray-{index}",
            remote_addr=attacker,
            username=username,
            password="BadPassword!",
            now=2000.0 + index,
        )
        service.disconnect(f"spray-{index}")

    victim_path = service.authenticate(
        connection_id="legit-same-source",
        remote_addr=attacker,
        username="diana",
        password="quiet-signal",
        now=2005.0,
    )
    assert victim_path.allowed is False
    assert victim_path.reason == "blocked"

    other_source = service.authenticate(
        connection_id="legit-other-source",
        remote_addr="198.51.100.8",
        username="diana",
        password="quiet-signal",
        now=2005.0,
    )
    assert other_source.allowed is True
    assert other_source.reason == "authenticated"


def test_cooldown_allows_login_again() -> None:
    service = build_service()
    remote_addr = "203.0.113.44"

    for index, username in enumerate(["alice", "bob", "carol"], start=1):
        service.authenticate(
            connection_id=f"cooldown-{index}",
            remote_addr=remote_addr,
            username=username,
            password="BadPassword!",
            now=3000.0 + index,
        )
        service.disconnect(f"cooldown-{index}")

    blocked = service.authenticate(
        connection_id="cooldown-blocked",
        remote_addr=remote_addr,
        username="diana",
        password="quiet-signal",
        now=3005.0,
    )
    assert blocked.allowed is False
    assert blocked.reason == "blocked"

    allowed = service.authenticate(
        connection_id="cooldown-retry",
        remote_addr=remote_addr,
        username="diana",
        password="quiet-signal",
        now=3095.0,
    )
    assert allowed.allowed is True
    assert allowed.reason == "authenticated"
