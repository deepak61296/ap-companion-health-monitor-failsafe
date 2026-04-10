"""
State machine for companion health tracking.

AP_FLAKE8_CLEAN
"""

import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

from .mavlink import STATUS_FLAG_OVERHEATING


class CompanionState(IntEnum):
    """Health states matching FC-side AP_CompanionHealth::State."""
    DISCONNECTED = 0  # No FC connection or timed out
    HEALTHY = 1       # All metrics normal
    DEGRADED = 2      # Warning thresholds exceeded
    CRITICAL = 3      # Critical thresholds, failsafe may trigger


@dataclass
class StateTransition:
    """Record of a state transition."""
    from_state: CompanionState
    to_state: CompanionState
    timestamp: float
    reason: str


class StateMachine:
    """Tracks companion computer health state."""

    # Thresholds for state transitions
    CPU_WARN_PCT = 80
    CPU_CRIT_PCT = 95
    MEM_WARN_PCT = 80
    MEM_CRIT_PCT = 95
    TEMP_WARN_CDEG = 750   # 75.0C
    TEMP_CRIT_CDEG = 900   # 90.0C

    def __init__(self) -> None:
        self._state = CompanionState.DISCONNECTED
        self._last_transition: Optional[StateTransition] = None
        self._state_enter_time = time.monotonic()

    @property
    def state(self) -> CompanionState:
        """Current health state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """True if connected to FC."""
        return self._state != CompanionState.DISCONNECTED

    @property
    def is_healthy(self) -> bool:
        """True if in HEALTHY state."""
        return self._state == CompanionState.HEALTHY

    @property
    def last_transition(self) -> Optional[StateTransition]:
        """Most recent state transition."""
        return self._last_transition

    @property
    def time_in_state_s(self) -> float:
        """Seconds since entering current state."""
        return time.monotonic() - self._state_enter_time

    def transition_to(self, new_state: CompanionState, reason: str = "") -> bool:
        """Transition to a new state.

        Args:
            new_state: Target state
            reason: Human-readable reason for transition

        Returns:
            True if state changed, False if already in target state
        """
        if new_state == self._state:
            return False

        self._last_transition = StateTransition(
            self._state, new_state, time.monotonic(), reason
        )
        self._state = new_state
        self._state_enter_time = time.monotonic()
        return True

    def on_connect_success(self) -> None:
        """Called when MAVLink connection established."""
        self.transition_to(CompanionState.HEALTHY, "connected")

    def on_disconnect(self) -> None:
        """Called when MAVLink connection lost."""
        self.transition_to(CompanionState.DISCONNECTED, "connection lost")

    def update_health(
        self,
        status_flags: int,
        cpu_pct: int,
        memory_pct: int,
        temp_cdeg: int
    ) -> None:
        """Update state based on current metrics.

        Args:
            status_flags: Bitmask of warning flags
            cpu_pct: CPU usage 0-100%
            memory_pct: Memory usage 0-100%
            temp_cdeg: Temperature in decidegrees (450 = 45.0C)
        """
        if not self.is_connected:
            return

        # Critical: overheating flag, or any metric > 95%
        is_critical = (
            (status_flags & STATUS_FLAG_OVERHEATING) != 0
            or cpu_pct > self.CPU_CRIT_PCT
            or memory_pct > self.MEM_CRIT_PCT
            or temp_cdeg > self.TEMP_CRIT_CDEG
        )

        # Degraded: any warning flag, or metrics > 80%
        is_degraded = (
            (status_flags & 0x0F) != 0
            or cpu_pct > self.CPU_WARN_PCT
            or memory_pct > self.MEM_WARN_PCT
            or temp_cdeg > self.TEMP_WARN_CDEG
        )

        if is_critical:
            self.transition_to(CompanionState.CRITICAL, "critical threshold")
        elif is_degraded:
            self.transition_to(CompanionState.DEGRADED, "elevated metrics")
        else:
            self.transition_to(CompanionState.HEALTHY, "normal")

    def get_status_string(self) -> str:
        """Return current state name."""
        return self._state.name
