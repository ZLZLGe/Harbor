from __future__ import annotations

from dataclasses import dataclass

from .failure_tracker import FailureTracker


@dataclass(frozen=True)
class AuthDecision:
    allowed: bool
    reason: str


class BastionAuthService:
    def __init__(
        self,
        credentials: dict[str, str],
        tracker: FailureTracker | None = None,
    ) -> None:
        self._credentials = credentials
        self._tracker = tracker or FailureTracker()

    def authenticate(
        self,
        *,
        connection_id: str,
        remote_addr: str,
        username: str,
        password: str,
        now: float,
    ) -> AuthDecision:
        if self._tracker.is_blocked(
            connection_id=connection_id,
            remote_addr=remote_addr,
            username=username,
            now=now,
        ):
            return AuthDecision(False, "blocked")

        if self._credentials.get(username) == password:
            self._tracker.register_success(
                connection_id=connection_id,
                remote_addr=remote_addr,
                username=username,
                now=now,
            )
            return AuthDecision(True, "authenticated")

        self._tracker.register_failure(
            connection_id=connection_id,
            remote_addr=remote_addr,
            username=username,
            now=now,
        )
        if self._tracker.is_blocked(
            connection_id=connection_id,
            remote_addr=remote_addr,
            username=username,
            now=now,
        ):
            return AuthDecision(False, "blocked")
        return AuthDecision(False, "invalid-credentials")

    def disconnect(self, connection_id: str) -> None:
        self._tracker.disconnect(connection_id)
