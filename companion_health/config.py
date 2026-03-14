"""Configuration management for companion health monitor."""

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)

# Default configuration values
DEFAULTS = {
    'connection': {
        'device': 'udpout:127.0.0.1:14550',
        'baud': 115200,
        'source_system': 1,
        'source_component': 191,  # MAV_COMP_ID_ONBOARD_COMPUTER
    },
    'monitoring': {
        'rate_hz': 1.0,
        'disk_path': '/',
    },
    'thresholds': {
        'temp_throttle': 80.0,
        'temp_overheat': 85.0,
        'memory_low': 90,
        'disk_low': 95,
    },
    'platform': None,  # Auto-detect if not set
}


@dataclass
class ConnectionConfig:
    device: str = 'udpout:127.0.0.1:14550'
    baud: int = 115200
    source_system: int = 1
    source_component: int = 191


@dataclass
class MonitoringConfig:
    rate_hz: float = 1.0
    disk_path: str = '/'


@dataclass
class ThresholdsConfig:
    temp_throttle: float = 80.0
    temp_overheat: float = 85.0
    memory_low: int = 90
    disk_low: int = 95


@dataclass
class Config:
    """Main configuration container."""
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    thresholds: ThresholdsConfig = field(default_factory=ThresholdsConfig)
    platform: Optional[str] = None

    @classmethod
    def from_file(cls, path: str) -> 'Config':
        """Load configuration from YAML file.

        Args:
            path: Path to YAML configuration file

        Returns:
            Config instance with values from file
        """
        try:
            import yaml
        except ImportError:
            log.warning("PyYAML not installed, using defaults")
            return cls()

        if not os.path.exists(path):
            log.warning("Config file %s not found, using defaults", path)
            return cls()

        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            log.error("Failed to load config from %s: %s", path, e)
            return cls()

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> 'Config':
        """Create Config from dictionary.

        Args:
            data: Dictionary with configuration values

        Returns:
            Config instance
        """
        conn_data = {**DEFAULTS['connection'], **data.get('connection', {})}
        mon_data = {**DEFAULTS['monitoring'], **data.get('monitoring', {})}
        thresh_data = {**DEFAULTS['thresholds'], **data.get('thresholds', {})}

        return cls(
            connection=ConnectionConfig(**conn_data),
            monitoring=MonitoringConfig(**mon_data),
            thresholds=ThresholdsConfig(**thresh_data),
            platform=data.get('platform'),
        )

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            'connection': {
                'device': self.connection.device,
                'baud': self.connection.baud,
                'source_system': self.connection.source_system,
                'source_component': self.connection.source_component,
            },
            'monitoring': {
                'rate_hz': self.monitoring.rate_hz,
                'disk_path': self.monitoring.disk_path,
            },
            'thresholds': {
                'temp_throttle': self.thresholds.temp_throttle,
                'temp_overheat': self.thresholds.temp_overheat,
                'memory_low': self.thresholds.memory_low,
                'disk_low': self.thresholds.disk_low,
            },
            'platform': self.platform,
        }

    def get_thresholds_dict(self) -> dict:
        """Get thresholds as dict for backend config."""
        return {
            'temp_throttle': self.thresholds.temp_throttle,
            'temp_overheat': self.thresholds.temp_overheat,
            'memory_low': self.thresholds.memory_low,
            'disk_low': self.thresholds.disk_low,
        }
