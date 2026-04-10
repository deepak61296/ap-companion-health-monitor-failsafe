"""
Pytest fixtures for companion health tests.

AP_FLAKE8_CLEAN
"""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_config():
    """Return a sample configuration dict."""
    return {
        'connection': {
            'device': 'udpout:127.0.0.1:14560',
            'baud': 115200,
            'source_system': 1,
            'source_component': 191,
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
        'services': [],
        'platform': None,
    }
