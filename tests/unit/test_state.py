"""
Tests for the state machine.

AP_FLAKE8_CLEAN
"""

import pytest

from companion_health.state import CompanionState, StateMachine


class TestCompanionState:
    def test_state_values(self):
        assert CompanionState.DISCONNECTED == 0
        assert CompanionState.HEALTHY == 1
        assert CompanionState.DEGRADED == 2
        assert CompanionState.CRITICAL == 3

    def test_state_ordering(self):
        assert CompanionState.DISCONNECTED < CompanionState.HEALTHY
        assert CompanionState.HEALTHY < CompanionState.DEGRADED
        assert CompanionState.DEGRADED < CompanionState.CRITICAL


class TestStateMachine:
    def test_initial_state(self):
        sm = StateMachine()
        assert sm.state == CompanionState.DISCONNECTED
        assert not sm.is_connected
        assert not sm.is_healthy

    def test_connect_success(self):
        sm = StateMachine()
        sm.on_connect_success()
        assert sm.state == CompanionState.HEALTHY
        assert sm.is_connected
        assert sm.is_healthy

    def test_disconnect(self):
        sm = StateMachine()
        sm.on_connect_success()
        sm.on_disconnect()
        assert sm.state == CompanionState.DISCONNECTED
        assert not sm.is_connected

    def test_health_update_healthy(self):
        sm = StateMachine()
        sm.on_connect_success()
        sm.update_health(status_flags=0, cpu_pct=30, memory_pct=40, temp_cdeg=450)
        assert sm.state == CompanionState.HEALTHY

    def test_health_update_degraded_cpu(self):
        sm = StateMachine()
        sm.on_connect_success()
        sm.update_health(status_flags=0, cpu_pct=85, memory_pct=40, temp_cdeg=450)
        assert sm.state == CompanionState.DEGRADED

    def test_health_update_degraded_memory(self):
        sm = StateMachine()
        sm.on_connect_success()
        sm.update_health(status_flags=0, cpu_pct=30, memory_pct=85, temp_cdeg=450)
        assert sm.state == CompanionState.DEGRADED

    def test_health_update_degraded_temp(self):
        sm = StateMachine()
        sm.on_connect_success()
        sm.update_health(status_flags=0, cpu_pct=30, memory_pct=40, temp_cdeg=780)
        assert sm.state == CompanionState.DEGRADED

    def test_health_update_degraded_flags(self):
        sm = StateMachine()
        sm.on_connect_success()
        sm.update_health(status_flags=0x01, cpu_pct=30, memory_pct=40, temp_cdeg=450)
        assert sm.state == CompanionState.DEGRADED

    def test_health_update_critical_cpu(self):
        sm = StateMachine()
        sm.on_connect_success()
        sm.update_health(status_flags=0, cpu_pct=98, memory_pct=40, temp_cdeg=450)
        assert sm.state == CompanionState.CRITICAL

    def test_health_update_critical_temp(self):
        sm = StateMachine()
        sm.on_connect_success()
        sm.update_health(status_flags=0, cpu_pct=30, memory_pct=40, temp_cdeg=920)
        assert sm.state == CompanionState.CRITICAL

    def test_health_update_critical_flag(self):
        sm = StateMachine()
        sm.on_connect_success()
        # 0x02 = STATUS_FLAG_OVERHEATING
        sm.update_health(status_flags=0x02, cpu_pct=30, memory_pct=40, temp_cdeg=450)
        assert sm.state == CompanionState.CRITICAL

    def test_health_update_requires_connection(self):
        sm = StateMachine()
        sm.update_health(status_flags=0, cpu_pct=30, memory_pct=40, temp_cdeg=450)
        assert sm.state == CompanionState.DISCONNECTED

    def test_transition_returns_false_for_same_state(self):
        sm = StateMachine()
        assert sm.transition_to(CompanionState.DISCONNECTED) is False

    def test_status_string(self):
        sm = StateMachine()
        assert sm.get_status_string() == "DISCONNECTED"
        sm.on_connect_success()
        assert sm.get_status_string() == "HEALTHY"

    def test_time_in_state(self):
        sm = StateMachine()
        assert sm.time_in_state_s >= 0
        sm.on_connect_success()
        assert sm.time_in_state_s >= 0

    def test_last_transition(self):
        sm = StateMachine()
        assert sm.last_transition is None
        sm.on_connect_success()
        assert sm.last_transition is not None
        assert sm.last_transition.from_state == CompanionState.DISCONNECTED
        assert sm.last_transition.to_state == CompanionState.HEALTHY
