"""
Tests for metric collection backends.
"""


from companion_health.backends.base import HealthMetrics
from companion_health.backends import generic
from companion_health.backends.generic import GenericBackend
from companion_health.mavlink import (
    STATUS_FLAG_LOW_DISK,
    STATUS_FLAG_LOW_MEMORY,
    STATUS_FLAG_OVERHEATING,
    STATUS_FLAG_THROTTLED,
    TEMPERATURE_UNKNOWN,
)


class TestHealthMetrics:
    """Test HealthMetrics dataclass."""

    def test_create_metrics(self):
        """Can create HealthMetrics with all fields."""
        m = HealthMetrics(
            cpu_load=50,
            memory_used=60,
            disk_used=70,
            temperature=4500,
            gpu_load=255,
            status_flags=0
        )
        assert m.cpu_load == 50
        assert m.memory_used == 60
        assert m.disk_used == 70
        assert m.temperature == 4500
        assert m.gpu_load == 255
        assert m.status_flags == 0


class TestStatusFlags:
    """Test status flag constants."""

    def test_flag_values(self):
        """Flags have expected bit positions."""
        assert STATUS_FLAG_THROTTLED == 0x01
        assert STATUS_FLAG_OVERHEATING == 0x02
        assert STATUS_FLAG_LOW_MEMORY == 0x04
        assert STATUS_FLAG_LOW_DISK == 0x08

    def test_flags_are_distinct(self):
        """All flags can be combined."""
        combined = (
            STATUS_FLAG_THROTTLED
            | STATUS_FLAG_OVERHEATING
            | STATUS_FLAG_LOW_MEMORY
            | STATUS_FLAG_LOW_DISK
        )
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
        flags = backend.get_status_flags(temp_cdeg=8500, memory_pct=50, disk_pct=50)
        assert flags & STATUS_FLAG_THROTTLED

    def test_status_flags_overheating(self):
        """Very high temperature sets overheating flag."""
        backend = GenericBackend({'thresholds': {'temp_overheat': 85.0}})
        flags = backend.get_status_flags(temp_cdeg=9000, memory_pct=50, disk_pct=50)
        assert flags & STATUS_FLAG_OVERHEATING

    def test_status_flags_low_memory(self):
        """High memory usage sets low memory flag."""
        backend = GenericBackend({'thresholds': {'memory_low': 90}})
        flags = backend.get_status_flags(temp_cdeg=4500, memory_pct=95, disk_pct=50)
        assert flags & STATUS_FLAG_LOW_MEMORY

    def test_status_flags_low_disk(self):
        """High disk usage sets low disk flag."""
        backend = GenericBackend({'thresholds': {'disk_low': 95}})
        flags = backend.get_status_flags(temp_cdeg=4500, memory_pct=50, disk_pct=98)
        assert flags & STATUS_FLAG_LOW_DISK

    def test_status_flags_normal(self):
        """Normal metrics return no flags."""
        backend = GenericBackend()
        flags = backend.get_status_flags(temp_cdeg=4500, memory_pct=50, disk_pct=50)
        assert flags == 0


class TestTemperatureUnits:
    """Pin the wire unit: sysfs millidegrees must become centidegrees."""

    def test_sysfs_path_converts_millidegrees(self, tmp_path, monkeypatch):
        """A discovered sysfs sensor reading 45000 (45.0C) reports 4500."""
        sensor = tmp_path / "temp"
        sensor.write_text("45000\n")
        monkeypatch.setattr(generic, "TEMP_SENSOR_PATHS", [str(sensor)])
        backend = GenericBackend()
        assert backend.get_temperature() == 4500

    def test_cached_path_matches_discovery_path(self, tmp_path, monkeypatch):
        """The cached read returns the same value as the discovery read."""
        sensor = tmp_path / "temp"
        sensor.write_text("45000\n")
        monkeypatch.setattr(generic, "TEMP_SENSOR_PATHS", [str(sensor)])
        backend = GenericBackend()
        first = backend.get_temperature()
        second = backend.get_temperature()
        assert first == second == 4500

    def test_overheat_temperature_crosses_fc_threshold(self, tmp_path, monkeypatch):
        """90C must report above the flight controller's 9000 cdegC limit."""
        sensor = tmp_path / "temp"
        sensor.write_text("90000\n")
        monkeypatch.setattr(generic, "TEMP_SENSOR_PATHS", [str(sensor)])
        backend = GenericBackend()
        assert backend.get_temperature() == 9000

    def test_missing_sensor_reports_unknown(self, monkeypatch):
        """No sensor anywhere reports the invalid sentinel, not zero."""
        monkeypatch.setattr(generic, "TEMP_SENSOR_PATHS", ["/nonexistent/temp"])
        monkeypatch.setattr(generic.psutil, "sensors_temperatures", lambda: {})
        backend = GenericBackend()
        assert backend.get_temperature() == TEMPERATURE_UNKNOWN

    def test_freezing_temperatures_survive(self, tmp_path, monkeypatch):
        """0C and sub-zero readings are real values, not 'unknown'."""
        sensor = tmp_path / "temp"
        monkeypatch.setattr(generic, "TEMP_SENSOR_PATHS", [str(sensor)])
        for milli, expected in ((0, 0), (-5000, -500)):
            sensor.write_text(f"{milli}\n")
            backend = GenericBackend()
            metrics = backend.collect_all("/")
            assert backend.get_temperature() == expected
            assert metrics.temperature != TEMPERATURE_UNKNOWN

    def test_unknown_temperature_sets_no_heat_flags(self):
        """The sentinel must not read as an overheat."""
        backend = GenericBackend()
        flags = backend.get_status_flags(
            temp_cdeg=TEMPERATURE_UNKNOWN, memory_pct=50, disk_pct=50
        )
        assert not flags & STATUS_FLAG_OVERHEATING
        assert not flags & STATUS_FLAG_THROTTLED
