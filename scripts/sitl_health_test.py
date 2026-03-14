#!/usr/bin/env python3
"""
SITL test script for COMPANION_HEALTH message.
Connects to SITL and sends health messages to test failsafe.
"""

import os
import sys
import time
import struct
import argparse

os.environ['MAVLINK20'] = '1'
from pymavlink import mavutil

# COMPANION_HEALTH message ID (custom message)
MAVLINK_MSG_ID_COMPANION_HEALTH = 11061


def send_companion_health_raw(mav_connection, services_status, watchdog_seq,
                               temperature, cpu_load, memory_used, disk_used,
                               gpu_load, status_flags):
    """Send COMPANION_HEALTH as raw MAVLink2 message."""
    payload = struct.pack('<IHhBBBBB',
        services_status, watchdog_seq, temperature,
        cpu_load, memory_used, disk_used, gpu_load, status_flags
    )

    msg_id = MAVLINK_MSG_ID_COMPANION_HEALTH
    seq = mav_connection.mav.seq
    mav_connection.mav.seq = (seq + 1) % 256

    header = struct.pack('<BBBBBBBHB',
        0xFD, len(payload), 0, 0, seq,
        mav_connection.mav.srcSystem, mav_connection.mav.srcComponent,
        msg_id & 0xFFFF, (msg_id >> 16) & 0xFF
    )

    crc = mavutil.x25crc(header[1:])
    crc.accumulate(payload)
    crc.accumulate_str(chr(81))  # CRC extra for COMPANION_HEALTH

    packet = header + payload + struct.pack('<H', crc.crc)
    mav_connection.write(packet)


def main():
    parser = argparse.ArgumentParser(description='SITL Companion Health Test')
    parser.add_argument('--connect', default='udp:127.0.0.1:14551',
                        help='Connection string (default: udp:127.0.0.1:14551)')
    parser.add_argument('--rate', type=float, default=1.0, help='Health message rate (Hz)')
    args = parser.parse_args()

    print("=" * 60)
    print("SITL Companion Health Test Script")
    print("=" * 60)
    print(f"Connecting to: {args.connect}")

    mav = mavutil.mavlink_connection(args.connect, source_system=1, source_component=191)

    print("Waiting for heartbeat from SITL...")
    mav.wait_heartbeat()
    print(f"Heartbeat received! System {mav.target_system}, Component {mav.target_component}")

    watchdog_seq = 0
    interval = 1.0 / args.rate

    print(f"\nSending COMPANION_HEALTH at {args.rate:.1f} Hz")
    print("Press Ctrl+C to stop (this will trigger failsafe after timeout)\n")

    try:
        while True:
            # Send heartbeat (MAV_TYPE_ONBOARD_CONTROLLER=18, MAV_AUTOPILOT_INVALID=8)
            mav.mav.heartbeat_send(18, 8, 0, 0, 4)

            # Send COMPANION_HEALTH
            send_companion_health_raw(mav,
                services_status=0,
                watchdog_seq=watchdog_seq,
                temperature=450,    # 45.0C in decidegrees
                cpu_load=25,        # 25%
                memory_used=60,     # 60%
                disk_used=40,       # 40%
                gpu_load=10,        # 10%
                status_flags=1      # Normal
            )

            print(f"[HEALTH] seq={watchdog_seq:4d} cpu=25% mem=60% temp=45.0C - Sending...")

            watchdog_seq = (watchdog_seq + 1) % 65536
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n")
        print("=" * 60)
        print("Script stopped! Failsafe should trigger in ~5 seconds...")
        print("Restart this script to clear the failsafe.")
        print("=" * 60)


if __name__ == '__main__':
    main()
