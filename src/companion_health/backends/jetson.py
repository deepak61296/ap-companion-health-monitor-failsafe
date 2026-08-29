"""
NVIDIA Jetson backend reading GPU load and thermal zones from sysfs.

Not complete: it has no unit tests of its own and the last on-device run
predates the current code. Raspberry Pi and generic Linux are the fully
supported backends; this one is kept working on a best-effort basis.
"""

import logging
import os

from typing import Optional

import psutil

from .base import MetricsBackend, TEMPERATURE_UNKNOWN

log = logging.getLogger(__name__)

# Jetson-specific paths
JETSON_GPU_LOAD_PATH = '/sys/devices/gpu.0/load'
JETSON_THERMAL_ZONES = [
    '/sys/devices/virtual/thermal/thermal_zone0/temp',  # CPU
    '/sys/devices/virtual/thermal/thermal_zone1/temp',  # GPU
    '/sys/devices/virtual/thermal/thermal_zone2/temp',  # AUX
]


class JetsonBackend(MetricsBackend):
    """NVIDIA Jetson optimized backend.

    Supports Jetson Nano, TX2, Xavier, and Orin series.
    Uses sysfs for GPU load and temperature.
    """

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._gpu_path: Optional[str] = None
        self._temp_path: Optional[str] = None
        self._jetson_model: Optional[str] = None

        self._detect_jetson()

        # Initialize CPU measurement
        psutil.cpu_percent(interval=None)

        log.info("Jetson model: %s", self._jetson_model or "unknown")

    def _detect_jetson(self):
        """Detect Jetson model and available sensors."""
        # Try to get model from /etc/nv_tegra_release
        if os.path.exists('/etc/nv_tegra_release'):
            try:
                with open('/etc/nv_tegra_release', 'r') as f:
                    content = f.read()
                    if 'R32' in content or 'R34' in content or 'R35' in content:
                        self._jetson_model = self._parse_jetson_model()
            except IOError:
                pass

        # Find GPU load path
        if os.path.exists(JETSON_GPU_LOAD_PATH):
            self._gpu_path = JETSON_GPU_LOAD_PATH
        else:
            # Try alternative paths for different Jetson models
            alt_paths = [
                '/sys/devices/platform/gpu.0/load',
                '/sys/devices/17000000.ga10b/load',  # Orin
                '/sys/devices/17000000.gp10b/load',  # Xavier
            ]
            for path in alt_paths:
                if os.path.exists(path):
                    self._gpu_path = path
                    break

        # Find best temperature sensor
        for path in JETSON_THERMAL_ZONES:
            if os.path.exists(path):
                self._temp_path = path
                break

    def _parse_jetson_model(self) -> str:
        """Try to determine Jetson model."""
        try:
            # Check device tree
            if os.path.exists('/proc/device-tree/model'):
                with open('/proc/device-tree/model', 'r') as f:
                    model = f.read().strip('\x00')
                    if 'Nano' in model:
                        return 'Jetson Nano'
                    elif 'Xavier' in model:
                        return 'Jetson Xavier'
                    elif 'Orin' in model:
                        return 'Jetson Orin'
                    elif 'TX2' in model:
                        return 'Jetson TX2'
                    return model
        except IOError:
            pass
        return 'Jetson'

    def get_platform_name(self) -> str:
        return 'jetson'

    def get_cpu_load(self) -> int:
        try:
            return int(psutil.cpu_percent(interval=None))
        except (OSError, ValueError):
            return 0

    def get_memory_used(self) -> int:
        try:
            return int(psutil.virtual_memory().percent)
        except (OSError, AttributeError):
            return 0

    def get_disk_used(self, path: str = '/') -> int:
        try:
            return int(psutil.disk_usage(path).percent)
        except (OSError, AttributeError):
            return 0

    def get_temperature(self) -> int:
        """Get CPU/SoC temperature from sysfs."""
        if self._temp_path:
            try:
                with open(self._temp_path, 'r') as f:
                    # Value is in millidegrees
                    temp_milli = int(f.read().strip())
                    return temp_milli // 10  # Convert to centidegrees
            except (IOError, ValueError):
                pass

        # Fallback: try all thermal zones and take highest
        max_temp = None
        for path in JETSON_THERMAL_ZONES:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        temp = int(f.read().strip()) // 10
                        max_temp = temp if max_temp is None else max(max_temp, temp)
                except (IOError, ValueError):
                    continue

        if max_temp is not None:
            return max_temp

        if not self._temp_warning_logged:
            log.warning("No temperature sensor found")
            self._temp_warning_logged = True
        return TEMPERATURE_UNKNOWN

    def get_gpu_load(self) -> int:
        """Get GPU load from sysfs."""
        if self._gpu_path:
            try:
                with open(self._gpu_path, 'r') as f:
                    # Value is 0-1000 (permille)
                    load = int(f.read().strip())
                    return load // 10  # Convert to percentage
            except (IOError, ValueError):
                pass

        return 255  # Not available
