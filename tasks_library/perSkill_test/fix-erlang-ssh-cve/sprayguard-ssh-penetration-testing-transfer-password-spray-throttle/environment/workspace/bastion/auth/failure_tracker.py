from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class FailureState:
    failed_at: deque[float] = field(default_factory=deque)
    blocked_until: float = 0.0


class FailureTracker:
    def __init__(
        self,
        *,
        max_failures: int = 3,
        window_seconds: float = 30.0,
        cooldown_seconds: float = 90.0,
    ) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self._states: dict[str, FailureState] = {}

    def is_blocked(
        self,
        *,
        connection_id: str,
        remote_addr: str,
        username: str,
        now: float,
    ) -> bool:
        state = self._get_state(connection_id)
        self._trim(state, now)
        return now < state.blocked_until

    def register_failure(
        self,
        *,
        connection_id: str,
        remote_addr: str,
        username: str,
        now: float,
    ) -> None:
        state = self._get_state(connection_id)
        self._trim(state, now)
        state.failed_at.append(now)
        if len(state.failed_at) >= self.max_failures:
            state.blocked_until = now + self.cooldown_seconds

    def register_success(
        self,
        *,
        connection_id: str,
        remote_addr: str,
        username: str,
        now: float,
    ) -> None:
        self._states.pop(connection_id, None)

    def disconnect(self, connection_id: str) -> None:
        self._states.pop(connection_id, None)

    def _get_state(self, key: str) -> FailureState:
        state = self._states.get(key)
        if state is None:
            state = FailureState()
            self._states[key] = state
        return state

    def _trim(self, state: FailureState, now: float) -> None:
        cutoff = now - self.window_seconds
        while state.failed_at and state.failed_at[0] < cutoff:
            state.failed_at.popleft()
