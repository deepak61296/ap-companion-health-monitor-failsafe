"""
Generic Linux backend using psutil for cross-platform metrics.

AP_FLAKE8_CLEAN
"""

import logging
import os
import subprocess
from typing import Any, Dict, List, Optional

import psutil

from .base import MetricsBackend

log = logging.getLogger(__name__)

# Temperature sensor paths to try (in order of preference)
TEMP_SENSOR_PATHS: List[str] = [
    '/sys/class/thermal/thermal_zone0/temp',
    '/sys/class/thermal/thermal_zone1/temp',
    '/sys/class/hwmon/hwmon0/temp1_input',
    '/sys/class/hwmon/hwmon1/temp1_input',
]


class GenericBackend(MetricsBackend):
    """Generic Linux backend using psutil.

    Works on most Linux systems including x86, ARM, and embedded.
    Uses psutil for CPU/memory/disk and sysfs for temperature.
    Supports NVIDIA GPUs via nvidia-smi.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config)
        self._temp_sensor_path: Optional[str] = None
        self._has_nvidia_smi: Optional[bool] = None

        # Initialize CPU measurement (first call returns 0)
        psutil.cpu_percent(interval=None)

    def get_platform_name(self) -> str:
        return 'generic'

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
        """Return temperature in decidegrees (celsius * 10)."""
        # Try cached sensor path first
        if self._temp_sensor_path:
            try:
                with open(self._temp_sensor_path, 'r') as f:
                    temp_milli = int(f.read().strip())
                    return temp_milli // 100
            except (IOError, ValueError):
                self._temp_sensor_path = None

        # Try to find a working sensor
        for path in TEMP_SENSOR_PATHS:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        temp_milli = int(f.read().strip())
                        self._temp_sensor_path = path
                        return temp_milli // 100
                except (IOError, ValueError):
                    continue

        # Try psutil sensors as fallback
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        return int(entries[0].current * 10)
        except Exception:
            pass

        if not self._temp_warning_logged:
            log.warning("No temperature sensor found, reporting 0")
            self._temp_warning_logged = True
        return 0

    def get_gpu_load(self) -> int:
        """Return GPU load, or 255 if unavailable."""
        # Check for nvidia-smi (cache result)
        if self._has_nvidia_smi is None:
            self._has_nvidia_smi = self._check_nvidia_smi()

        if self._has_nvidia_smi:
            try:
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=utilization.gpu',
                     '--format=csv,noheader,nounits'],
                    capture_output=True, text=True, timeout=1
                )
                if result.returncode == 0:
                    return int(result.stdout.strip().split('\n')[0])
            except Exception:
                pass

        # Check for Jetson-style GPU load
        tegra_path = '/sys/devices/gpu.0/load'
        if os.path.exists(tegra_path):
            try:
                with open(tegra_path, 'r') as f:
                    return int(f.read().strip()) // 10
            except Exception:
                pass

        return 255

    def _check_nvidia_smi(self) -> bool:
        """Check if nvidia-smi is available."""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--version'],
                capture_output=True, timeout=2
            )
            return result.returncode == 0
        except Exception:
            return False
