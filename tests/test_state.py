"""Tests for the state machine."""

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
        sm.update_health(status_flags=0, cpu=30, memory=40, temp=450)
        assert sm.state == CompanionState.HEALTHY

    def test_health_update_degraded_cpu(self):
        sm = StateMachine()
        sm.on_connect_success()
        sm.update_health(status_flags=0, cpu=85, memory=40, temp=450)
        assert sm.state == CompanionState.DEGRADED

    def test_health_update_degraded_memory(self):
        sm = StateMachine()
        sm.on_connect_success()
        sm.update_health(status_flags=0, cpu=30, memory=85, temp=450)
        assert sm.state == CompanionState.DEGRADED

    def test_health_update_degraded_temp(self):
        sm = StateMachine()
        sm.on_connect_success()
        sm.update_health(status_flags=0, cpu=30, memory=40, temp=780)
        assert sm.state == CompanionState.DEGRADED

    def test_health_update_degraded_flags(self):
        sm = StateMachine()
        sm.on_connect_success()
        sm.update_health(status_flags=0x01, cpu=30, memory=40, temp=450)
        assert sm.state == CompanionState.DEGRADED

    def test_health_update_critical_cpu(self):
        sm = StateMachine()
        sm.on_connect_success()
        sm.update_health(status_flags=0, cpu=98, memory=40, temp=450)
        assert sm.state == CompanionState.CRITICAL

    def test_health_update_critical_temp(self):
        sm = StateMachine()
        sm.on_connect_success()
        sm.update_health(status_flags=0, cpu=30, memory=40, temp=920)
        assert sm.state == CompanionState.CRITICAL

    def test_health_update_critical_flag(self):
        sm = StateMachine()
        sm.on_connect_success()
        sm.update_health(status_flags=0x02, cpu=30, memory=40, temp=450)
        assert sm.state == CompanionState.CRITICAL

    def test_health_update_requires_connection(self):
        sm = StateMachine()
        sm.update_health(status_flags=0, cpu=30, memory=40, temp=450)
        assert sm.state == CompanionState.DISCONNECTED

    def test_transition_returns_false_for_same_state(self):
        sm = StateMachine()
        assert sm.transition_to(CompanionState.DISCONNECTED) is False

    def test_status_string(self):
        sm = StateMachine()
        assert sm.get_status_string() == "DISCONNECTED"
        sm.on_connect_success()
        assert sm.get_status_string() == "HEALTHY"
