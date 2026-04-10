"""
Platform-specific metric collection backends.

AP_FLAKE8_CLEAN
"""

import logging
import os
from typing import Any, Dict, Optional

from .base import HealthMetrics, MetricsBackend
from .generic import GenericBackend

__all__ = [
    'MetricsBackend',
    'HealthMetrics',
    'GenericBackend',
    'detect_backend',
    'get_backend',
]

log = logging.getLogger(__name__)


def detect_backend(config: Optional[Dict[str, Any]] = None) -> MetricsBackend:
    """Auto-detect and return the appropriate backend for this platform.

    Detection order:
    1. Jetson (has /etc/nv_tegra_release or /sys/devices/gpu.0)
    2. Raspberry Pi (has vcgencmd)
    3. Generic Linux fallback

    Args:
        config: Optional configuration dict with thresholds

    Returns:
        Appropriate MetricsBackend instance for this platform
    """
    # Check for Jetson (has tegrastats and specific GPU path)
    if os.path.exists('/etc/nv_tegra_release') or os.path.exists('/sys/devices/gpu.0'):
        try:
            from .jetson import JetsonBackend
            log.debug("Detected Jetson platform")
            return JetsonBackend(config)
        except ImportError as e:
            log.warning("Jetson detected but backend failed: %s", e)

    # Check for Raspberry Pi (has vcgencmd)
    if os.path.exists('/usr/bin/vcgencmd') or os.path.exists('/opt/vc/bin/vcgencmd'):
        try:
            from .raspberry_pi import RaspberryPiBackend
            log.debug("Detected Raspberry Pi platform")
            return RaspberryPiBackend(config)
        except ImportError as e:
            log.warning("Raspberry Pi detected but backend failed: %s", e)

    # Fallback to generic
    log.debug("Using generic backend")
    return GenericBackend(config)


def get_backend(name: str, config: Optional[Dict[str, Any]] = None) -> MetricsBackend:
    """Get a specific backend by name.

    Args:
        name: Backend name ('generic', 'raspberry_pi', 'jetson')
        config: Optional configuration dict

    Returns:
        MetricsBackend instance

    Raises:
        ValueError: If backend name is unknown
    """
    name = name.lower()

    if name == 'generic':
        return GenericBackend(config)
    elif name == 'raspberry_pi':
        from .raspberry_pi import RaspberryPiBackend
        return RaspberryPiBackend(config)
    elif name == 'jetson':
        from .jetson import JetsonBackend
        return JetsonBackend(config)
    else:
        raise ValueError(f"Unknown backend: {name}")
