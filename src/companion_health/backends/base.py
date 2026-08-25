"""
Abstract base class for platform-specific metric collection.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

import collections

from ..mavlink import (
    STATUS_FLAG_LOW_DISK,
    STATUS_FLAG_LOW_MEMORY,
    STATUS_FLAG_OVERHEATING,
    STATUS_FLAG_THROTTLED,
    TEMPERATURE_UNKNOWN,
)


@dataclass
class HealthMetrics:
    """Container for all health metrics."""
    cpu_load: int           # 0-100%
    memory_used: int        # 0-100%
    disk_used: int          # 0-100%
    temperature: int        # Celsius * 100 (e.g., 4500 = 45.0C), TEMPERATURE_UNKNOWN if unavailable
    gpu_load: int           # 0-100%, or 255 if unavailable
    status_flags: int       # Bitmask of status flags


class MetricsBackend(ABC):
    """Abstract base class for platform-specific metric collection.

    Subclasses implement platform-specific methods for collecting
    CPU, memory, disk, temperature, and GPU metrics.
    """

    # Default thresholds
    DEFAULT_TEMP_THROTTLE_C = 80.0
    DEFAULT_TEMP_OVERHEAT_C = 85.0
    DEFAULT_MEMORY_LOW_PCT = 90
    DEFAULT_DISK_LOW_PCT = 95

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize backend with optional configuration.

        Args:
            config: Optional dict with threshold configuration
        """
        self.config = config or {}
        self._temp_warning_logged = False
        self._cpu_history = collections.deque(maxlen=5)
        self._temp_history = collections.deque(maxlen=5)

    @abstractmethod
    def get_cpu_load(self) -> int:
        """Return CPU load percentage (0-100)."""
        ...

    @abstractmethod
    def get_memory_used(self) -> int:
        """Return memory usage percentage (0-100)."""
        ...

    @abstractmethod
    def get_disk_used(self, path: str = '/') -> int:
        """Return disk usage percentage (0-100) for the given path."""
        ...

    @abstractmethod
    def get_temperature(self) -> int:
        """Return board temperature in centidegrees (celsius * 100).

        Returns TEMPERATURE_UNKNOWN if no temperature sensor is available.
        """
        ...

    @abstractmethod
    def get_gpu_load(self) -> int:
        """Return GPU load percentage (0-100), or 255 if unavailable."""
        ...

    @abstractmethod
    def get_platform_name(self) -> str:
        """Return human-readable platform name."""
        ...

    def get_status_flags(
        self,
        temp_cdeg: int,
        memory_pct: int,
        disk_pct: int
    ) -> int:
        """Calculate status flags based on current metrics.

        Args:
            temp_cdeg: Temperature in centidegrees (celsius * 100)
            memory_pct: Memory usage percentage
            disk_pct: Disk usage percentage

        Returns:
            Bitmask of status flags
        """
        thresholds = self.config.get('thresholds', {})
        temp_throttle = thresholds.get('temp_throttle', self.DEFAULT_TEMP_THROTTLE_C)
        temp_overheat = thresholds.get('temp_overheat', self.DEFAULT_TEMP_OVERHEAT_C)
        memory_low = thresholds.get('memory_low', self.DEFAULT_MEMORY_LOW_PCT)
        disk_low = thresholds.get('disk_low', self.DEFAULT_DISK_LOW_PCT)

        flags = 0

        # an unknown temperature must not look like an overheat
        if temp_cdeg != TEMPERATURE_UNKNOWN:
            temp_c = temp_cdeg / 100.0
            if temp_c > temp_throttle:
                flags |= STATUS_FLAG_THROTTLED
            if temp_c > temp_overheat:
                flags |= STATUS_FLAG_OVERHEATING
        if memory_pct > memory_low:
            flags |= STATUS_FLAG_LOW_MEMORY
        if disk_pct > disk_low:
            flags |= STATUS_FLAG_LOW_DISK

        return flags

    def collect_all(self, disk_path: str = '/') -> HealthMetrics:
        """Collect all health metrics in one call.

        Args:
            disk_path: Path to monitor for disk usage

        Returns:
            HealthMetrics dataclass with all metrics
        """
        raw_cpu = self.get_cpu_load()
        self._cpu_history.append(raw_cpu)
        cpu = int(sum(self._cpu_history) / len(self._cpu_history))

        memory = self.get_memory_used()
        disk = self.get_disk_used(disk_path)

        raw_temp = self.get_temperature()
        if raw_temp != TEMPERATURE_UNKNOWN:
            self._temp_history.append(raw_temp)
            temp = int(sum(self._temp_history) / len(self._temp_history))
        else:
            # drop stale samples so a recovered sensor is not averaged with them
            self._temp_history.clear()
            temp = TEMPERATURE_UNKNOWN

        gpu = self.get_gpu_load()
        flags = self.get_status_flags(temp, memory, disk)

        return HealthMetrics(
            cpu_load=cpu,
            memory_used=memory,
            disk_used=disk,
            temperature=temp,
            gpu_load=gpu,
            status_flags=flags
        )
