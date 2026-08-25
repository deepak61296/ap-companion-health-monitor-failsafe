"""
Main health monitor implementation.
"""

import logging
import os
import struct
import time
from typing import Optional

# Must set MAVLINK20 before importing mavutil
os.environ['MAVLINK20'] = '1'

from pymavlink import mavutil

from .backends import MetricsBackend, detect_backend
from .config import Config
from .services import ServicesMonitor
from .mavlink import (
    MAV_AUTOPILOT_INVALID,
    MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
    MAV_STATE_ACTIVE,
    MAV_TYPE_ONBOARD_CONTROLLER,
    TEMPERATURE_MAX,
    TEMPERATURE_MIN,
    TEMPERATURE_UNKNOWN,
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
        self.services_monitor = ServicesMonitor(self.config.services)

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
        except IOError as e:
            log.error("Failed to connect (IOError): %s", e)
            return False
        except ValueError as e:
            log.error("Failed to connect (Invalid parameters): %s", e)
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
        except IOError as e:
            log.error("Failed to send heartbeat (IOError): %s", e)
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

        services_status = self.services_monitor.get_status()

        # clamp so a misreporting sensor cannot overflow the int16 field
        temperature = metrics.temperature
        if temperature != TEMPERATURE_UNKNOWN:
            temperature = max(TEMPERATURE_MIN, min(TEMPERATURE_MAX, temperature))

        try:
            # Try native method first, fall back to raw packet
            if hasattr(self.mav.mav, 'companion_health_send'):
                self.mav.mav.companion_health_send(
                    services_status=services_status,
                    watchdog_seq=self.watchdog_seq,
                    temperature=temperature,
                    cpu_load=metrics.cpu_load,
                    memory_used=metrics.memory_used,
                    disk_used=metrics.disk_used,
                    gpu_load=metrics.gpu_load,
                    status_flags=metrics.status_flags
                )
            else:
                send_companion_health_raw(
                    self.mav,
                    services_status=services_status,
                    watchdog_seq=self.watchdog_seq,
                    temperature=temperature,
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
                temperature / 100.0,
                'N/A' if metrics.gpu_load == 255 else f'{metrics.gpu_load}%',
                metrics.status_flags,
                self.watchdog_seq
            )
            return True
        except IOError as e:
            log.error("Failed to send message (IOError): %s", e)
            self.state_machine.on_disconnect()
            return False
        except AttributeError as e:
            log.error("Failed to send message (AttributeError): %s", e)
            self.state_machine.on_disconnect()
            return False
        except struct.error as e:
            # a metric outside its field range would otherwise kill the loop
            log.error("Failed to pack message: %s", e)
            return False

    def run(self) -> int:
        """Main loop: send health messages at configured rate.

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        self.running = True
        interval_s = 1.0 / self.config.monitoring.rate_hz
        log.info("Starting health monitor main loop (rate: %.1f Hz)", self.config.monitoring.rate_hz)

        backoff_s = 1.0
        max_backoff_s = 30.0

        while self.running:
            if not self.mav:
                # Try to connect
                if self.connect():
                    # Reset backoff on successful connection
                    backoff_s = 1.0
                else:
                    log.warning("Connection attempt failed. Retrying in %.1f seconds...", backoff_s)
                    # Sleep with checks for self.running
                    sleep_start = time.monotonic()
                    while self.running and (time.monotonic() - sleep_start < backoff_s):
                        time.sleep(0.1)
                    # Exponential backoff
                    backoff_s = min(max_backoff_s, backoff_s * 2.0)
                    continue

            # Connected - pulse health & heartbeat
            start = time.monotonic()
            heartbeat_ok = self.send_heartbeat()
            health_ok = self.send_health()

            # If either failed, mark as disconnected so we trigger reconnection next iteration
            if not heartbeat_ok or not health_ok:
                log.error("Telemetry link dropped. Scheduling reconnect...")
                if self.mav:
                    try:
                        self.mav.close()
                    except (IOError, OSError) as e:
                        log.debug("Error closing link: %s", e)
                self.mav = None
                self.state_machine.on_disconnect()
                # Wait briefly before first reconnect attempt
                time.sleep(1.0)
                backoff_s = 1.0
                continue

            elapsed = time.monotonic() - start
            sleep_time = max(0, interval_s - elapsed)
            time.sleep(sleep_time)

        # Cleanup on stop
        if self.mav:
            try:
                self.mav.close()
            except (IOError, OSError) as e:
                log.debug("Error closing link: %s", e)
            self.mav = None

        log.info("Stopped")
        return 0

    def stop(self) -> None:
        """Signal the main loop to stop."""
        self.running = False
