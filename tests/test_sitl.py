#!/usr/bin/env python3
"""SITL integration test - verifies FC receives COMPANION_HEALTH messages."""

import os
import sys
import time
import subprocess

os.environ['MAVLINK20'] = '1'
from pymavlink import mavutil

def test_sitl():
    # Start SITL
    sitl_path = "/home/deepak/Documents/ap-companion-health-failsafe/ardupilot/build/sitl/bin/arducopter"
    sitl_cmd = [
        sitl_path,
        "--model", "+",
        "--speedup", "1",
        "--defaults", "/home/deepak/Documents/ap-companion-health-failsafe/ardupilot/Tools/autotest/default_params/copter.parm",
        "-I0"
    ]

    print("Starting SITL...")
    sitl = subprocess.Popen(sitl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(5)

    try:
        # Connect
        print("Connecting to SITL...")
        mav = mavutil.mavlink_connection('tcp:127.0.0.1:5760', source_system=1, source_component=191)

        # Wait for heartbeat
        print("Waiting for FC heartbeat...")
        mav.wait_heartbeat(timeout=10)
        print(f"Got heartbeat from system {mav.target_system}")

        # Set CC_ENABLE = 1
        print("Setting CC_ENABLE = 1...")
        mav.mav.param_set_send(
            mav.target_system,
            mav.target_component,
            b'CC_ENABLE',
            1.0,
            mavutil.mavlink.MAV_PARAM_TYPE_INT8
        )
        time.sleep(1)

        # Send COMPANION_HEALTH
        print("Sending COMPANION_HEALTH messages...")
        for i in range(5):
            mav.mav.companion_health_send(
                services_status=0,
                watchdog_seq=i,
                temperature=450,
                cpu_load=25,
                memory_used=30,
                disk_used=50,
                gpu_load=255,
                status_flags=0
            )
            time.sleep(0.5)

        # Check for STATUSTEXT from FC
        print("Checking for FC response...")
        start = time.time()
        found = False
        while time.time() - start < 5:
            msg = mav.recv_match(type='STATUSTEXT', blocking=True, timeout=1)
            if msg:
                text = msg.text
                print(f"  STATUSTEXT: {text}")
                if 'Companion' in text:
                    found = True
                    print("SUCCESS: FC received COMPANION_HEALTH!")
                    break

        if not found:
            print("WARNING: No 'Companion' STATUSTEXT received (might need CC_ENABLE set)")

        return found

    finally:
        print("Stopping SITL...")
        sitl.terminate()
        sitl.wait()

if __name__ == '__main__':
    success = test_sitl()
    sys.exit(0 if success else 1)
