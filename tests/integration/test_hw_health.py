#!/usr/bin/env python3
"""
Hardware Test: Health Monitor
Run on companion computer (RPi/Jetson) connected to CubeOrange.

Usage:
    python3 test_hw_health.py [--device /dev/ttyACM0]
"""

import sys
import os
import time
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['MAVLINK20'] = '1'

from companion_health.backends import detect_backend
from companion_health.config import Config, ConnectionConfig, MonitoringConfig
from companion_health.monitor import HealthMonitor


def main():
    parser = argparse.ArgumentParser(description='Hardware test: Health Monitor')
    parser.add_argument('--device', default='/dev/ttyACM0', help='Serial device')
    parser.add_argument('--duration', type=int, default=15, help='Test duration in seconds')
    args = parser.parse_args()

    print("=" * 60)
    print("HARDWARE TEST: Companion Health Monitor")
    print("=" * 60)

    # Test 1: Platform detection
    print("\n[TEST 1] Platform Detection")
    print("-" * 40)
    backend = detect_backend()
    print(f"Backend: {backend.__class__.__name__}")

    # Test 2: Metrics collection
    print("\n[TEST 2] Metrics Collection")
    print("-" * 40)
    metrics = backend.collect_all()
    print(f"CPU Load:    {metrics.cpu_load}%")
    print(f"Memory Used: {metrics.memory_used}%")
    print(f"Disk Used:   {metrics.disk_used}%")
    print(f"Temperature: {metrics.temperature / 10.0:.1f}C")
    print(f"GPU Load:    {'N/A' if metrics.gpu_load == 255 else f'{metrics.gpu_load}%'}")
    print(f"Flags:       0x{metrics.status_flags:02X}")

    # Test 3: MAVLink connection
    print(f"\n[TEST 3] MAVLink Connection to {args.device}")
    print("-" * 40)

    # Create config with the device
    config = Config(
        connection=ConnectionConfig(device=args.device, baud=115200),
        monitoring=MonitoringConfig(rate_hz=1.0)
    )

    monitor = HealthMonitor(config)

    try:
        monitor.connect()
        print("Connected to flight controller!")
        print(f"State: {monitor.state_machine.get_status_string()}")

        # Test 4: Send health messages
        print(f"\n[TEST 4] Sending COMPANION_HEALTH messages for {args.duration}s")
        print("-" * 40)

        start = time.time()
        count = 0
        while time.time() - start < args.duration:
            if monitor.send_health():
                count += 1
                m = backend.collect_all()
                print(f"[{count:3d}] CPU={m.cpu_load:2d}% Mem={m.memory_used:2d}% Temp={m.temperature/10:.1f}C")
            time.sleep(1.0)

        print("\n" + "=" * 60)
        print(f"SUCCESS: Sent {count} COMPANION_HEALTH messages")
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
