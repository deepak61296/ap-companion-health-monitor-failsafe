"""
Tests for configuration handling.

AP_FLAKE8_CLEAN
"""

import os
import tempfile

import pytest

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
        assert config.services == []

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

services:
  - mavproxy
  - camera_node
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            try:
                config = Config.from_file(f.name)
                assert config.connection.device == '/dev/ttyUSB0'
                assert config.connection.baud == 57600
                assert config.monitoring.rate_hz == 2.0
                assert config.services == ['mavproxy', 'camera_node']
            finally:
                os.unlink(f.name)

    def test_from_file_missing(self):
        """Config.from_file returns defaults for missing file."""
        config = Config.from_file('/nonexistent/config.yaml')
        assert config.connection is not None

    def test_to_dict(self):
        """Config can be converted to dict."""
        config = Config()
        d = config.to_dict()
        assert 'connection' in d
        assert 'monitoring' in d
        assert 'thresholds' in d
        assert 'services' in d

    def test_from_dict(self):
        """Config can be created from dict."""
        data = {
            'connection': {'device': '/dev/ttyACM0'},
            'services': ['test_service'],
        }
        config = Config.from_dict(data)
        assert config.connection.device == '/dev/ttyACM0'
        assert config.services == ['test_service']
