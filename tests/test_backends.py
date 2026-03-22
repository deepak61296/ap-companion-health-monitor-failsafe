"""Tests for metric collection backends."""

import pytest
from companion_health.backends.base import HealthMetrics, MetricsBackend, FLAG_THROTTLED, FLAG_OVERHEATING, FLAG_LOW_MEMORY, FLAG_LOW_DISK
from companion_health.backends.generic import GenericBackend


class TestHealthMetrics:
    """Test HealthMetrics dataclass."""

    def test_create_metrics(self):
        """Can create HealthMetrics with all fields."""
        m = HealthMetrics(
            cpu_load=50,
            memory_used=60,
            disk_used=70,
            temperature=450,
            gpu_load=255,
            status_flags=0
        )
        assert m.cpu_load == 50
        assert m.memory_used == 60
        assert m.disk_used == 70
        assert m.temperature == 450
        assert m.gpu_load == 255
        assert m.status_flags == 0


class TestStatusFlags:
    """Test status flag constants."""

    def test_flag_values(self):
        """Flags have expected bit positions."""
        assert FLAG_THROTTLED == 0x01
        assert FLAG_OVERHEATING == 0x02
        assert FLAG_LOW_MEMORY == 0x04
        assert FLAG_LOW_DISK == 0x08

    def test_flags_are_distinct(self):
        """All flags can be combined."""
        combined = FLAG_THROTTLED | FLAG_OVERHEATING | FLAG_LOW_MEMORY | FLAG_LOW_DISK
        assert combined == 0x0F


class TestGenericBackend:
    """Test GenericBackend metric collection."""

    def test_get_cpu_load(self):
        """CPU load returns 0-100 range."""
        backend = GenericBackend()
        cpu = backend.get_cpu_load()
        assert 0 <= cpu <= 100

    def test_get_memory_used(self):
        """Memory usage returns 0-100 range."""
        backend = GenericBackend()
        mem = backend.get_memory_used()
        assert 0 <= mem <= 100

    def test_get_disk_used(self):
        """Disk usage returns 0-100 range."""
        backend = GenericBackend()
        disk = backend.get_disk_used('/')
        assert 0 <= disk <= 100

    def test_get_temperature(self):
        """Temperature returns non-negative value."""
        backend = GenericBackend()
        temp = backend.get_temperature()
        assert temp >= 0

    def test_get_gpu_load(self):
        """GPU load returns 0-100 or 255 (unavailable)."""
        backend = GenericBackend()
        gpu = backend.get_gpu_load()
        assert (0 <= gpu <= 100) or gpu == 255

    def test_get_platform_name(self):
        """Platform name is a string."""
        backend = GenericBackend()
        name = backend.get_platform_name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_collect_all(self):
        """collect_all returns HealthMetrics."""
        backend = GenericBackend()
        metrics = backend.collect_all('/')
        assert isinstance(metrics, HealthMetrics)

    def test_status_flags_throttled(self):
        """High temperature sets throttled flag."""
        backend = GenericBackend({'thresholds': {'temp_throttle': 80.0}})
        flags = backend.get_status_flags(temperature=850, memory=50, disk=50)
        assert flags & FLAG_THROTTLED

    def test_status_flags_overheating(self):
        """Very high temperature sets overheating flag."""
        backend = GenericBackend({'thresholds': {'temp_overheat': 85.0}})
        flags = backend.get_status_flags(temperature=900, memory=50, disk=50)
        assert flags & FLAG_OVERHEATING

    def test_status_flags_low_memory(self):
        """High memory usage sets low memory flag."""
        backend = GenericBackend({'thresholds': {'memory_low': 90}})
        flags = backend.get_status_flags(temperature=450, memory=95, disk=50)
        assert flags & FLAG_LOW_MEMORY

    def test_status_flags_low_disk(self):
        """High disk usage sets low disk flag."""
        backend = GenericBackend({'thresholds': {'disk_low': 95}})
        flags = backend.get_status_flags(temperature=450, memory=50, disk=98)
        assert flags & FLAG_LOW_DISK

    def test_status_flags_normal(self):
        """Normal metrics return no flags."""
        backend = GenericBackend()
        flags = backend.get_status_flags(temperature=450, memory=50, disk=50)
        assert flags == 0
