"""NVIDIA Jetson backend with tegrastats integration."""

import logging
import os
import re
import subprocess
from typing import Dict, Optional

import psutil

from .base import MetricsBackend

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
            except Exception:
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
        except Exception:
            pass
        return 'Jetson'

    def get_platform_name(self) -> str:
        return 'jetson'

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
        """Get CPU/SoC temperature from sysfs."""
        if self._temp_path:
            try:
                with open(self._temp_path, 'r') as f:
                    # Value is in millidegrees
                    temp_milli = int(f.read().strip())
                    return temp_milli // 100  # Convert to decidegrees
            except Exception:
                pass

        # Fallback: try all thermal zones and take highest
        max_temp = 0
        for path in JETSON_THERMAL_ZONES:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        temp = int(f.read().strip()) // 100
                        max_temp = max(max_temp, temp)
                except Exception:
                    continue

        if max_temp > 0:
            return max_temp

        if not self._temp_warning_logged:
            log.warning("No temperature sensor found")
            self._temp_warning_logged = True
        return 0

    def get_gpu_load(self) -> int:
        """Get GPU load from sysfs."""
        if self._gpu_path:
            try:
                with open(self._gpu_path, 'r') as f:
                    # Value is 0-1000 (permille)
                    load = int(f.read().strip())
                    return load // 10  # Convert to percentage
            except Exception:
                pass

        return 255  # Not available

    def get_power_mode(self) -> Optional[str]:
        """Get current NVP model power mode."""
        try:
            result = subprocess.run(
                ['nvpmodel', '-q'],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                # Parse output for mode name
                for line in result.stdout.split('\n'):
                    if 'NV Power Mode' in line:
                        return line.split(':')[-1].strip()
        except Exception:
            pass
        return None

    def get_jetson_stats(self) -> Dict[str, int]:
        """Get additional Jetson-specific stats.

        Returns dict with available stats like:
        - gpu_freq: GPU frequency in MHz
        - emc_freq: Memory controller frequency
        - power: Power consumption in mW
        """
        stats = {}

        # GPU frequency
        gpu_freq_path = '/sys/devices/gpu.0/devfreq/57000000.gpu/cur_freq'
        if os.path.exists(gpu_freq_path):
            try:
                with open(gpu_freq_path, 'r') as f:
                    stats['gpu_freq'] = int(f.read().strip()) // 1000000  # Hz to MHz
            except Exception:
                pass

        # Try to get power from INA sensors (varies by model)
        power_paths = [
            '/sys/bus/i2c/drivers/ina3221x/6-0040/iio:device0/in_power0_input',
            '/sys/bus/i2c/drivers/ina3221x/0-0040/iio:device0/in_power0_input',
        ]
        for path in power_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        stats['power'] = int(f.read().strip())  # mW
                        break
                except Exception:
                    continue

        return stats
