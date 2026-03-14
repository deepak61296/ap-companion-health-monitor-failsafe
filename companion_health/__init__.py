"""
Companion Computer Health Monitoring for ArduPilot.

This package provides cross-platform health monitoring for companion
computers, sending COMPANION_HEALTH MAVLink messages to the flight controller.
"""

from .monitor import HealthMonitor
from .config import Config

__version__ = '0.2.0'
__all__ = ['HealthMonitor', 'Config']
