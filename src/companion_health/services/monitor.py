"""
Services monitor for tracking critical processes.

Uses psutil to check if named processes are running on the companion
computer. The result is packed into a uint32 bitmask where bit N
corresponds to service N in the configured list. This bitmask is sent
to ArduPilot as the services_status field in COMPANION_HEALTH, where
the FC compares it against CCH_SVC_MASK to detect critical failures.
"""

import logging
import shutil
import subprocess
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

# Use psutil if available, fall back to pgrep
try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False
    log.info("psutil not available, falling back to pgrep")


class ServicesMonitor:
    """Monitor critical services/processes on the companion computer.

    Checks if each configured process name is currently running and
    builds a bitmask reflecting live status. Supports up to 32 services
    limited by the uint32 bitmask in COMPANION_HEALTH.

    Example config (YAML):
        services:
          - mavproxy
          - camera_node
          - vision_pose

    Usage:
        monitor = ServicesMonitor(['mavproxy', 'camera_node'])
        status = monitor.get_status()  # Returns uint32 bitmask
    """

    MAX_SERVICES = 32  # Limited by uint32 bitmask

    def __init__(self, services: Optional[List[str]] = None) -> None:
        """Initialize services monitor.

        Args:
            services: List of process names to monitor (max 32).
                      Pass None or empty list to disable monitoring.
        """
        if services is None:
            services = []

        if len(services) > self.MAX_SERVICES:
            log.warning(
                "Too many services (%d), truncating to %d",
                len(services), self.MAX_SERVICES
            )
            services = services[:self.MAX_SERVICES]

        self.services = services
        self._last_status: Dict[str, bool] = {}
        self._has_pgrep = shutil.which('pgrep') is not None

        if self.services:
            log.info(
                "Monitoring %d services: %s",
                len(self.services), ', '.join(self.services)
            )

    def check_service(self, name: str) -> bool:
        """Check if a named process is currently running.

        Uses psutil.process_iter() if available, otherwise falls back
        to calling pgrep as a subprocess.

        Args:
            name: Process name to search for (matched against process
                  name and cmdline).

        Returns:
            True if at least one matching process is found.
        """
        if _HAS_PSUTIL:
            return self._check_psutil(name)
        return self._check_pgrep(name)

    def _check_psutil(self, name: str) -> bool:
        """Check for process using psutil."""
        name_lower = name.lower()
        try:
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    proc_name = (proc.info.get('name') or '').lower()
                    if name_lower == proc_name:
                        return True
                    # Also check if the name appears in the cmdline
                    # This catches "python3 mavproxy.py" style processes
                    cmdline = proc.info.get('cmdline') or []
                    for arg in cmdline:
                        if name_lower in arg.lower():
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except (psutil.Error, OSError) as e:
            log.debug("psutil error checking '%s': %s", name, e)
        return False

    def _check_pgrep(self, name: str) -> bool:
        """Check for process using pgrep subprocess call."""
        if not self._has_pgrep:
            log.debug("pgrep not found on system, cannot check '%s'", name)
            return False
        try:
            result = subprocess.run(
                ['pgrep', '-f', name],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            log.debug("pgrep timed out checking '%s'", name)
            return False
        except OSError as e:
            log.debug("pgrep error checking '%s': %s", name, e)
            return False

    def get_status(self) -> int:
        """Get services status as a uint32 bitmask.

        Bit N is set to 1 if service N (from the configured list) is
        currently running.

        Returns:
            uint32 bitmask. Returns 0 if no services are configured.
        """
        if not self.services:
            return 0

        status = 0
        for i, service in enumerate(self.services):
            running = self.check_service(service)
            if running:
                status |= (1 << i)
            self._last_status[service] = running
        return status

    def get_status_dict(self) -> Dict[str, bool]:
        """Get services status as a dictionary.

        Returns:
            Dict mapping service name to its running status.
        """
        self.get_status()
        return self._last_status.copy()

    def get_failed_services(self) -> List[str]:
        """Get list of services that are not currently running.

        Returns:
            List of service names that were not found.
        """
        self.get_status()
        return [name for name, running in self._last_status.items()
                if not running]

    def get_running_services(self) -> List[str]:
        """Get list of services that are currently running.

        Returns:
            List of service names that were found.
        """
        self.get_status()
        return [name for name, running in self._last_status.items()
                if running]
