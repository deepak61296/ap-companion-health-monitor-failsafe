"""
Services monitor for tracking critical processes.

GSoC Week 1-2 implementation placeholder.

AP_FLAKE8_CLEAN
"""

import logging
from typing import Dict, List

log = logging.getLogger(__name__)


class ServicesMonitor:
    """Monitor critical services/processes on the companion computer.

    GSoC Implementation Plan:
    1. Load service list from config (list of process names)
    2. Check each service using pgrep
    3. Build services_status bitmask (bit N = service N running)
    4. Integrate with HealthMonitor.send_health()

    Example config:
        services:
          - mavproxy
          - camera_node
          - vision_pose

    Usage:
        monitor = ServicesMonitor(['mavproxy', 'camera_node'])
        status = monitor.get_status()  # Returns uint32 bitmask
    """

    MAX_SERVICES = 32  # Limited by uint32 bitmask

    def __init__(self, services: List[str]) -> None:
        """Initialize services monitor.

        Args:
            services: List of process names to monitor (max 32)
        """
        if len(services) > self.MAX_SERVICES:
            log.warning(
                "Too many services (%d), truncating to %d",
                len(services), self.MAX_SERVICES
            )
            services = services[:self.MAX_SERVICES]

        self.services = services
        self._last_status: Dict[str, bool] = {}

    def check_service(self, name: str) -> bool:
        """Check if a service/process is running.

        Args:
            name: Process name to check

        Returns:
            True if process is running, False otherwise

        TODO (GSoC Week 1-2): Implement using pgrep or psutil
        """
        # Placeholder - always returns True
        # GSoC: Replace with actual implementation
        return True

    def get_status(self) -> int:
        """Get services status as bitmask.

        Returns:
            uint32 bitmask where bit N = 1 if service N is running
        """
        status = 0
        for i, service in enumerate(self.services):
            if self.check_service(service):
                status |= (1 << i)
            self._last_status[service] = bool(status & (1 << i))
        return status

    def get_status_dict(self) -> Dict[str, bool]:
        """Get services status as dictionary.

        Returns:
            Dict mapping service name to running status
        """
        self.get_status()  # Update status
        return self._last_status.copy()

    def get_failed_services(self) -> List[str]:
        """Get list of services that are not running.

        Returns:
            List of failed service names
        """
        self.get_status()  # Update status
        return [name for name, running in self._last_status.items() if not running]
