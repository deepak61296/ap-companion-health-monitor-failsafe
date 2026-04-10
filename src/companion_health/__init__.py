"""
Companion Computer Health Monitor for ArduPilot.

Sends COMPANION_HEALTH MAVLink messages to the flight controller,
enabling failsafe actions when the companion computer fails.

AP_FLAKE8_CLEAN
"""

from .config import Config
from .monitor import HealthMonitor
from .state import CompanionState, StateMachine

__version__ = '0.1.0'
__all__ = ['Config', 'HealthMonitor', 'CompanionState', 'StateMachine']
