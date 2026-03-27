"""State machine for health tracking."""

from enum import IntEnum
from dataclasses import dataclass
import time


class CompanionState(IntEnum):
    DISCONNECTED = 0  # No FC connection or timed out
    HEALTHY = 1       # All metrics normal
    DEGRADED = 2      # Warning thresholds exceeded
    CRITICAL = 3      # Critical thresholds - failsafe may trigger


@dataclass
class StateTransition:
    from_state: CompanionState
    to_state: CompanionState
    timestamp: float
    reason: str


class StateMachine:
    def __init__(self):
        self._state = CompanionState.DISCONNECTED
        self._last_transition = None
        self._state_enter_time = time.monotonic()

    @property
    def state(self) -> CompanionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state != CompanionState.DISCONNECTED

    @property
    def is_healthy(self) -> bool:
        return self._state == CompanionState.HEALTHY

    def transition_to(self, new_state: CompanionState, reason: str = "") -> bool:
        if new_state == self._state:
            return False
        self._last_transition = StateTransition(self._state, new_state, time.monotonic(), reason)
        self._state = new_state
        self._state_enter_time = time.monotonic()
        return True

    def on_connect_success(self):
        self.transition_to(CompanionState.HEALTHY, "connected")

    def on_disconnect(self):
        self.transition_to(CompanionState.DISCONNECTED, "connection lost")

    def update_health(self, status_flags: int, cpu: int, memory: int, temp: int):
        """Update state based on metrics. Call after each successful send."""
        if not self.is_connected:
            return

        # Critical: overheating flag, or any metric > 95%
        is_critical = (status_flags & 0x02) != 0 or cpu > 95 or memory > 95 or temp > 900

        # Degraded: any warning flag, or metrics > 80%
        is_degraded = (status_flags & 0x0F) != 0 or cpu > 80 or memory > 80 or temp > 750

        if is_critical:
            self.transition_to(CompanionState.CRITICAL, "critical threshold")
        elif is_degraded:
            self.transition_to(CompanionState.DEGRADED, "elevated metrics")
        else:
            self.transition_to(CompanionState.HEALTHY, "normal")

    def get_status_string(self) -> str:
        return self._state.name
