#!/usr/bin/env python3
"""
Quick SITL test script.

Starts companion health monitor and connects to SITL.
Useful for quick testing during development.

Usage:
    # First start SITL:
    ./Tools/autotest/sim_vehicle.py -v ArduCopter

    # Then run this script:
    python scripts/sitl_test.py
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from companion_health.cli import main

if __name__ == '__main__':
    sys.exit(main(['--device', 'udpout:127.0.0.1:14560', '-v']))
