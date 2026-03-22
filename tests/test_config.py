"""Tests for configuration handling."""

import pytest
import tempfile
import os
from companion_health.config import Config, ConnectionConfig, MonitoringConfig


class TestConnectionConfig:
    """Test ConnectionConfig dataclass."""

    def test_defaults(self):
        """ConnectionConfig has sensible defaults."""
        c = ConnectionConfig()
        assert c.device is not None
        assert c.baud > 0
        assert c.source_system > 0
        assert c.source_component > 0


class TestMonitoringConfig:
    """Test MonitoringConfig dataclass."""

    def test_defaults(self):
        """MonitoringConfig has sensible defaults."""
        m = MonitoringConfig()
        assert m.rate_hz > 0
        assert m.disk_path == '/'


class TestConfig:
    """Test Config class."""

    def test_default_config(self):
        """Config creates valid defaults."""
        config = Config()
        assert config.connection is not None
        assert config.monitoring is not None

    def test_get_thresholds_dict(self):
        """get_thresholds_dict returns expected keys."""
        config = Config()
        thresholds = config.get_thresholds_dict()
        assert 'temp_throttle' in thresholds
        assert 'temp_overheat' in thresholds
        assert 'memory_low' in thresholds
        assert 'disk_low' in thresholds

    def test_from_file_yaml(self):
        """Config can load from YAML file."""
        yaml_content = """
connection:
  device: /dev/ttyUSB0
  baud: 57600

monitoring:
  rate_hz: 2.0
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            try:
                config = Config.from_file(f.name)
                assert config.connection.device == '/dev/ttyUSB0'
                assert config.connection.baud == 57600
                assert config.monitoring.rate_hz == 2.0
            finally:
                os.unlink(f.name)

    def test_from_file_missing(self):
        """Config.from_file returns defaults for missing file."""
        # Config.from_file gracefully handles missing files with a warning
        config = Config.from_file('/nonexistent/config.yaml')
        # Should return a valid config with defaults
        assert config.connection is not None
