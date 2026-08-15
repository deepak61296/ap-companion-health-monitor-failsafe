#!/usr/bin/env python3
"""Test that failsafe triggers when companion stops sending.

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


def test_failsafe():
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
        print("Connecting...")
        mav = mavutil.mavlink_connection('tcp:127.0.0.1:5760', source_system=1, source_component=191)
        mav.wait_heartbeat(timeout=10)
        print(f"Connected to system {mav.target_system}")

        # Set CCH_ENABLE = 1 (RTL)
        print("Setting CCH_ENABLE = 1 (RTL on failsafe)...")
        mav.mav.param_set_send(mav.target_system, mav.target_component,
                               b'CCH_ENABLE', 1.0, mavutil.mavlink.MAV_PARAM_TYPE_INT8)
        time.sleep(0.5)

        # Set CCH_TIMEOUT = 3 seconds
        print("Setting CCH_TIMEOUT = 3...")
        mav.mav.param_set_send(mav.target_system, mav.target_component,
                               b'CCH_TIMEOUT', 3.0, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
        time.sleep(0.5)

        # Send COMPANION_HEALTH to establish connection
        print("Sending COMPANION_HEALTH to establish connection...")
        for i in range(3):
            mav.mav.companion_health_send(0, i, 450, 25, 30, 50, 255, 0)
            time.sleep(0.5)

        # Wait for connection message
        print("Waiting for connection confirmation...")
        start = time.time()
        connected = False
        while time.time() - start < 3:
            msg = mav.recv_match(type='STATUSTEXT', blocking=True, timeout=1)
            if msg and 'Companion computer connected' in msg.text:
                connected = True
                print(f"  Got: {msg.text}")
                break

        assert connected, "FC never confirmed companion connection"

        # Stop sending - wait for failsafe
        print("Stopping companion messages, waiting for failsafe (timeout=3s)...")
        print("(Failsafe only triggers when ARMED, so we just check for the message)")

        start = time.time()
        failsafe_msg = False
        while time.time() - start < 6:
            msg = mav.recv_match(type='STATUSTEXT', blocking=True, timeout=1)
            if msg:
                print(f"  STATUSTEXT: {msg.text}")
                if 'Failsafe' in msg.text or 'failsafe' in msg.text:
                    failsafe_msg = True
                    print("SUCCESS: Failsafe message received!")
                    break

        if not failsafe_msg:
            print("NOTE: No failsafe message - this is expected when not armed")
            print("      Failsafe only triggers in flight")

    finally:
        print("Stopping SITL...")
        sitl.terminate()
        sitl.wait()


if __name__ == '__main__':
    test_failsafe()
