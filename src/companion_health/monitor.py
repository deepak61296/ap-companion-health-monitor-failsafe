"""
Main health monitor implementation.

AP_FLAKE8_CLEAN
"""

import logging
import os
import time
from typing import Optional

# Must set MAVLINK20 before importing mavutil
os.environ['MAVLINK20'] = '1'

from pymavlink import mavutil

from .backends import MetricsBackend, detect_backend
from .config import Config
from .mavlink import (
    COMPANION_HEALTH_CRC_EXTRA,
    MAV_AUTOPILOT_INVALID,
    MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
    MAV_STATE_ACTIVE,
    MAV_TYPE_ONBOARD_CONTROLLER,
    MAVLINK_MSG_ID_COMPANION_HEALTH,
    send_companion_health_raw,
)
from .state import CompanionState, StateMachine

log = logging.getLogger(__name__)


class HealthMonitor:
    """Monitors companion computer health and sends MAVLink messages."""

    def __init__(
        self,
        config: Config,
        backend: Optional[MetricsBackend] = None
    ) -> None:
        """Initialize the health monitor.

        Args:
            config: Configuration object
            backend: Optional metrics backend (auto-detected if not provided)
        """
        self.config = config
        self.mav: Optional[mavutil.mavfile] = None
        self.watchdog_seq = 0
        self.running = False
        self.state_machine = StateMachine()
        self._last_metrics = None

        # Set up backend with threshold config
        if backend is None:
            backend = self._create_backend()
        self.backend = backend

        log.info("Using %s backend", self.backend.get_platform_name())

    def _create_backend(self) -> MetricsBackend:
        """Create appropriate backend based on config."""
        backend_config = {'thresholds': self.config.get_thresholds_dict()}

        if self.config.platform:
            # Explicitly configured platform
            platform = self.config.platform.lower()
            if platform == 'jetson':
                from .backends.jetson import JetsonBackend
                return JetsonBackend(backend_config)
            elif platform == 'raspberry_pi':
                from .backends.raspberry_pi import RaspberryPiBackend
                return RaspberryPiBackend(backend_config)
            elif platform == 'generic':
                from .backends.generic import GenericBackend
                return GenericBackend(backend_config)
            else:
                log.warning("Unknown platform '%s', using auto-detect", platform)

        # Auto-detect platform
        backend = detect_backend()
        backend.config = backend_config
        return backend

    @property
    def state(self) -> CompanionState:
        """Current connection/health state."""
        return self.state_machine.state

    def connect(self) -> bool:
        """Establish MAVLink connection.

        Returns:
            True if connection successful, False otherwise
        """
        device = self.config.connection.device
        log.info("Connecting to %s", device)

        try:
            self.mav = mavutil.mavlink_connection(
                device,
                baud=self.config.connection.baud,
                source_system=self.config.connection.source_system,
                source_component=self.config.connection.source_component,
                dialect='ardupilotmega'
            )
            self.state_machine.on_connect_success()
            log.info("Connected successfully (state: %s)", self.state.name)
            return True
        except Exception as e:
            log.error("Failed to connect: %s", e)
            return False

    def send_heartbeat(self) -> bool:
        """Send HEARTBEAT message to establish MAVLink connection."""
        if not self.mav:
            return False
        try:
            self.mav.mav.heartbeat_send(
                MAV_TYPE_ONBOARD_CONTROLLER,
                MAV_AUTOPILOT_INVALID,
                MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                0,
                MAV_STATE_ACTIVE
            )
            return True
        except Exception as e:
            log.error("Failed to send heartbeat: %s", e)
            return False

    def send_health(self) -> bool:
        """Collect metrics and send COMPANION_HEALTH message.

        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.mav:
            return False

        # Collect all metrics
        metrics = self.backend.collect_all(self.config.monitoring.disk_path)
        self._last_metrics = metrics

        # Update state machine based on health
        self.state_machine.update_health(
            metrics.status_flags,
            metrics.cpu_load,
            metrics.memory_used,
            metrics.temperature
        )

        try:
            # Try native method first, fall back to raw packet
            if hasattr(self.mav.mav, 'companion_health_send'):
                self.mav.mav.companion_health_send(
                    services_status=0,
                    watchdog_seq=self.watchdog_seq,
                    temperature=metrics.temperature,
                    cpu_load=metrics.cpu_load,
                    memory_used=metrics.memory_used,
                    disk_used=metrics.disk_used,
                    gpu_load=metrics.gpu_load,
                    status_flags=metrics.status_flags
                )
            else:
                send_companion_health_raw(
                    self.mav,
                    services_status=0,
                    watchdog_seq=self.watchdog_seq,
                    temperature=metrics.temperature,
                    cpu_load=metrics.cpu_load,
                    memory_used=metrics.memory_used,
                    disk_used=metrics.disk_used,
                    gpu_load=metrics.gpu_load,
                    status_flags=metrics.status_flags
                )
            self.watchdog_seq = (self.watchdog_seq + 1) % 65536

            log.debug(
                "Sent [%s]: cpu=%d%% mem=%d%% disk=%d%% temp=%.1fC gpu=%s flags=0x%02x seq=%d",
                self.state.name,
                metrics.cpu_load,
                metrics.memory_used,
                metrics.disk_used,
                metrics.temperature / 10.0,
                'N/A' if metrics.gpu_load == 255 else f'{metrics.gpu_load}%',
                metrics.status_flags,
                self.watchdog_seq
            )
            return True
        except Exception as e:
            log.error("Failed to send message: %s", e)
            self.state_machine.on_disconnect()
            return False

    def run(self) -> int:
        """Main loop: send health messages at configured rate.

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        if not self.connect():
            return 1

        interval_s = 1.0 / self.config.monitoring.rate_hz
        self.running = True

        log.info("Sending COMPANION_HEALTH at %.1f Hz", self.config.monitoring.rate_hz)

        while self.running:
            start = time.monotonic()
            self.send_heartbeat()
            self.send_health()
            elapsed = time.monotonic() - start
            sleep_time = max(0, interval_s - elapsed)
            time.sleep(sleep_time)

        log.info("Stopped")
        return 0

    def stop(self) -> None:
        """Signal the main loop to stop."""
        self.running = False
