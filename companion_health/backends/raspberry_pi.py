"""Raspberry Pi backend with vcgencmd integration."""

import logging
import os
import subprocess
from typing import Optional

import psutil

from .base import MetricsBackend

log = logging.getLogger(__name__)

# vcgencmd paths
VCGENCMD_PATHS = [
    '/usr/bin/vcgencmd',
    '/opt/vc/bin/vcgencmd',
]


class RaspberryPiBackend(MetricsBackend):
    """Raspberry Pi optimized backend.

    Uses vcgencmd for accurate temperature and throttling status.
    Falls back to generic methods if vcgencmd is unavailable.
    """

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._vcgencmd_path: Optional[str] = None
        self._find_vcgencmd()

        # Initialize CPU measurement
        psutil.cpu_percent(interval=None)

        if self._vcgencmd_path:
            log.info("Using vcgencmd at %s", self._vcgencmd_path)
        else:
            log.warning("vcgencmd not found, using fallback methods")

    def _find_vcgencmd(self):
        """Find vcgencmd binary."""
        for path in VCGENCMD_PATHS:
            if os.path.exists(path) and os.access(path, os.X_OK):
                self._vcgencmd_path = path
                return

    def _run_vcgencmd(self, *args) -> Optional[str]:
        """Run vcgencmd with given arguments."""
        if not self._vcgencmd_path:
            return None
        try:
            result = subprocess.run(
                [self._vcgencmd_path] + list(args),
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def get_platform_name(self) -> str:
        return 'raspberry_pi'

    def get_cpu_load(self) -> int:
        try:
            return int(psutil.cpu_percent(interval=None))
        except Exception:
            return 0

    def get_memory_used(self) -> int:
        try:
            return int(psutil.virtual_memory().percent)
        except Exception:
            return 0

    def get_disk_used(self, path: str = '/') -> int:
        try:
            return int(psutil.disk_usage(path).percent)
        except Exception:
            return 0

    def get_temperature(self) -> int:
        """Get CPU temperature using vcgencmd or sysfs."""
        # Try vcgencmd first (most accurate on Pi)
        output = self._run_vcgencmd('measure_temp')
        if output:
            # Output format: "temp=45.0'C"
            try:
                temp_str = output.split('=')[1].replace("'C", "")
                return int(float(temp_str) * 10)
            except (IndexError, ValueError):
                pass

        # Fallback to sysfs
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                return int(f.read().strip()) // 100
        except Exception:
            pass

        if not self._temp_warning_logged:
            log.warning("No temperature sensor found")
            self._temp_warning_logged = True
        return 0

    def get_gpu_load(self) -> int:
        """Pi doesn't have a separate GPU load metric."""
        return 255  # Not available

    def get_throttle_status(self) -> int:
        """Get throttling status from vcgencmd.

        Returns bitmask:
        - Bit 0: Under-voltage detected
        - Bit 1: Arm frequency capped
        - Bit 2: Currently throttled
        - Bit 3: Soft temperature limit active
        """
        output = self._run_vcgencmd('get_throttled')
        if output:
            # Output format: "throttled=0x0"
            try:
                hex_str = output.split('=')[1]
                return int(hex_str, 16)
            except (IndexError, ValueError):
                pass
        return 0

    def get_status_flags(self, temperature: int, memory: int, disk: int) -> int:
        """Calculate status flags including Pi-specific throttling."""
        # Get base flags from parent
        flags = super().get_status_flags(temperature, memory, disk)

        # Add Pi-specific throttling detection
        throttle = self.get_throttle_status()
        if throttle & 0x4:  # Currently throttled
            flags |= 0x01  # FLAG_THROTTLED

        return flags
