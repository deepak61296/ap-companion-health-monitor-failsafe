"""Abstract base class for platform-specific metric collection."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class HealthMetrics:
    """Container for all health metrics."""
    cpu_load: int           # 0-100%
    memory_used: int        # 0-100%
    disk_used: int          # 0-100%
    temperature: int        # Celsius * 10 (e.g., 450 = 45.0C)
    gpu_load: int           # 0-100%, or 255 if unavailable
    status_flags: int       # Bitmask of status flags


# Status flag bit positions
FLAG_THROTTLED = 0x01
FLAG_OVERHEATING = 0x02
FLAG_LOW_MEMORY = 0x04
FLAG_LOW_DISK = 0x08


class MetricsBackend(ABC):
    """Abstract base class for platform-specific metric collection.

    Subclasses implement platform-specific methods for collecting
    CPU, memory, disk, temperature, and GPU metrics.
    """

    def __init__(self, config: Optional[dict] = None):
        """Initialize backend with optional configuration.

        Args:
            config: Optional dict with threshold configuration
        """
        self.config = config or {}
        self._temp_warning_logged = False

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
        """Return board temperature in celsius * 10, or 0 if unavailable."""
        ...

    @abstractmethod
    def get_gpu_load(self) -> int:
        """Return GPU load percentage (0-100), or 255 if unavailable."""
        ...

    @abstractmethod
    def get_platform_name(self) -> str:
        """Return human-readable platform name."""
        ...

    def get_status_flags(self, temperature: int, memory: int, disk: int) -> int:
        """Calculate status flags based on current metrics.

        Args:
            temperature: Temperature in decidegrees (celsius * 10)
            memory: Memory usage percentage
            disk: Disk usage percentage

        Returns:
            Bitmask of status flags
        """
        thresholds = self.config.get('thresholds', {})
        temp_throttle = thresholds.get('temp_throttle', 80.0)
        temp_overheat = thresholds.get('temp_overheat', 85.0)
        memory_low = thresholds.get('memory_low', 90)
        disk_low = thresholds.get('disk_low', 95)

        flags = 0
        temp_celsius = temperature / 10.0

        if temp_celsius > temp_throttle:
            flags |= FLAG_THROTTLED
        if temp_celsius > temp_overheat:
            flags |= FLAG_OVERHEATING
        if memory > memory_low:
            flags |= FLAG_LOW_MEMORY
        if disk > disk_low:
            flags |= FLAG_LOW_DISK

        return flags

    def collect_all(self, disk_path: str = '/') -> HealthMetrics:
        """Collect all health metrics in one call.

        Args:
            disk_path: Path to monitor for disk usage

        Returns:
            HealthMetrics dataclass with all metrics
        """
        cpu = self.get_cpu_load()
        memory = self.get_memory_used()
        disk = self.get_disk_used(disk_path)
        temp = self.get_temperature()
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
