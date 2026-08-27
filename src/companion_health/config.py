"""
Configuration management for companion health monitor.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .mavlink import MAV_COMP_ID_ONBOARD_COMPUTER

log = logging.getLogger(__name__)


# Default configuration values
DEFAULTS: Dict[str, Any] = {
    'connection': {
        'device': 'udpout:127.0.0.1:14550',
        'baud': 115200,
        'source_system': 1,
        'source_component': MAV_COMP_ID_ONBOARD_COMPUTER,
    },
    'monitoring': {
        'rate_hz': 1.0,
        'disk_path': '/',
    },
    'thresholds': {
        'temp_throttle_c': 80.0,
        'temp_overheat_c': 85.0,
        'memory_low_pct': 90,
        'disk_low_pct': 95,
    },
    'services': [],  # process names to monitor, in CCH_SVC_MASK bit order
    'platform': None,
}


@dataclass
class ConnectionConfig:
    """MAVLink connection settings."""
    device: str = 'udpout:127.0.0.1:14550'
    baud: int = 115200
    source_system: int = 1
    source_component: int = MAV_COMP_ID_ONBOARD_COMPUTER


@dataclass
class MonitoringConfig:
    """Monitoring settings."""
    rate_hz: float = 1.0
    disk_path: str = '/'


@dataclass
class ThresholdsConfig:
    """Health thresholds."""
    temp_throttle_c: float = 80.0
    temp_overheat_c: float = 85.0
    memory_low_pct: int = 90
    disk_low_pct: int = 95


@dataclass
class Config:
    """Main configuration container."""
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    thresholds: ThresholdsConfig = field(default_factory=ThresholdsConfig)
    services: List[str] = field(default_factory=list)
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
        except IOError as e:
            log.error("Failed to read config from %s (IOError): %s", path, e)
            return cls()
        except yaml.YAMLError as e:
            log.error("Failed to parse config from %s (YAMLError): %s", path, e)
            return cls()

        return cls.from_dict(data)

    @staticmethod
    def _merge_section(name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge a config section over its defaults, dropping unknown keys.

        Older config files use key names that have since been renamed, so an
        unrecognised key warns rather than killing the daemon at startup.
        """
        defaults = DEFAULTS[name]
        merged = dict(defaults)
        for key, value in data.get(name, {}).items():
            if key in defaults:
                merged[key] = value
            else:
                log.warning("Ignoring unknown '%s' config key: %s", name, key)
        return merged

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create Config from dictionary.

        Args:
            data: Dictionary with configuration values

        Returns:
            Config instance
        """
        conn_data = cls._merge_section('connection', data)
        mon_data = cls._merge_section('monitoring', data)
        thresh_data = cls._merge_section('thresholds', data)

        return cls(
            connection=ConnectionConfig(**conn_data),
            monitoring=MonitoringConfig(**mon_data),
            thresholds=ThresholdsConfig(**thresh_data),
            services=data.get('services', []),
            platform=data.get('platform'),
        )

    def to_dict(self) -> Dict[str, Any]:
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
                'temp_throttle_c': self.thresholds.temp_throttle_c,
                'temp_overheat_c': self.thresholds.temp_overheat_c,
                'memory_low_pct': self.thresholds.memory_low_pct,
                'disk_low_pct': self.thresholds.disk_low_pct,
            },
            'services': self.services,
            'platform': self.platform,
        }

    def get_thresholds_dict(self) -> Dict[str, Any]:
        """Get thresholds as dict for backend config."""
        return {
            'temp_throttle': self.thresholds.temp_throttle_c,
            'temp_overheat': self.thresholds.temp_overheat_c,
            'memory_low': self.thresholds.memory_low_pct,
            'disk_low': self.thresholds.disk_low_pct,
        }
