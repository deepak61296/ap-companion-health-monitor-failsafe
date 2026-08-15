#!/usr/bin/env python3
"""SITL integration test - verifies FC receives COMPANION_HEALTH messages.

Needs an ArduPilot checkout with a SITL build of the companion-health
branch, and a pymavlink that includes COMPANION_HEALTH
(scripts/build_pymavlink.sh). Skipped otherwise, e.g. in CI.
"""

import os
import time
import subprocess
from pathlib import Path

import pytest

os.environ['MAVLINK20'] = '1'
from pymavlink import mavutil

ARDUPILOT_ROOT = Path(os.environ.get(
    'CCH_ARDUPILOT_ROOT',
    Path(__file__).resolve().parents[3] / 'ardupilot'))
SITL_BINARY = ARDUPILOT_ROOT / 'build' / 'sitl' / 'bin' / 'arducopter'
COPTER_DEFAULTS = ARDUPILOT_ROOT / 'Tools' / 'autotest' / 'default_params' / 'copter.parm'

pytestmark = [
    pytest.mark.skipif(
        not SITL_BINARY.exists(),
        reason='SITL binary not found, set CCH_ARDUPILOT_ROOT'),
    pytest.mark.skipif(
        not hasattr(mavutil.mavlink, 'MAVLINK_MSG_ID_COMPANION_HEALTH'),
        reason='pymavlink built without COMPANION_HEALTH'),
]


def test_sitl():
    # Start SITL
    sitl_cmd = [
        str(SITL_BINARY),
        "--model", "+",
        "--speedup", "1",
        "--defaults", str(COPTER_DEFAULTS),
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

        # Set CCH_ENABLE = 1
        print("Setting CCH_ENABLE = 1...")
        mav.mav.param_set_send(
            mav.target_system,
            mav.target_component,
            b'CCH_ENABLE',
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

        assert found, "FC never acknowledged COMPANION_HEALTH"

    finally:
        print("Stopping SITL...")
        sitl.terminate()
        sitl.wait()


if __name__ == '__main__':
    test_sitl()
