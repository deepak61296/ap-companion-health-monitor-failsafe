#!/usr/bin/env python3
"""
Hardware Test: Failsafe Trigger
Run on companion computer (RPi/Jetson) connected to CubeOrange.

Usage:
    python3 test_hw_failsafe.py [--device /dev/ttyACM0]
"""

import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['MAVLINK20'] = '1'

from companion_health.config import Config, ConnectionConfig, MonitoringConfig
from companion_health.monitor import HealthMonitor


def main():
    parser = argparse.ArgumentParser(description='Hardware test: Failsafe')
    parser.add_argument('--device', default='/dev/ttyACM0', help='Serial device')
    args = parser.parse_args()

    print("=" * 60)
    print("HARDWARE TEST: Companion Failsafe Trigger")
    print("=" * 60)

    config = Config(
        connection=ConnectionConfig(device=args.device, baud=115200),
        monitoring=MonitoringConfig(rate_hz=1.0)
    )

    # Phase 1: Connect and send health messages
    print("\n[PHASE 1] Establishing connection (5 seconds)")
    print("-" * 40)

    monitor = HealthMonitor(config)

    try:
        monitor.connect()
        print("Connected! Sending health messages...")

        for i in range(5):
            monitor.send_health()
            print(f"  Sent message {i+1}/5")
            time.sleep(1.0)

        print("\nFC should show: 'Companion computer connected'")

        # Phase 2: Stop sending to trigger failsafe
        print("\n[PHASE 2] Stopping health messages (simulating crash)")
        print("-" * 40)
        print("Health messages STOPPED.")
        print("Waiting for failsafe... (CCH_TIMEOUT = 5 seconds)")
        print("")

        for i in range(8):
            remaining = 8 - i
            print(f"  Waiting... {remaining}s remaining")
            time.sleep(1.0)

        print("\n" + "=" * 60)
        print("FC should now show: 'Companion Failsafe'")
        print("=" * 60)

        # Phase 3: Recovery
        print("\n[PHASE 3] Recovery - resuming health messages")
        print("-" * 40)

        for i in range(5):
            monitor.send_health()
            print(f"  Sent recovery message {i+1}/5")
            time.sleep(1.0)

        print("\n" + "=" * 60)
        print("FC should show: 'Companion Failsafe Cleared'")
        print("=" * 60)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        monitor.stop()

    return 0


if __name__ == '__main__':
    sys.exit(main())
