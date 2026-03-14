#!/usr/bin/env python3
"""
Bidirectional telemetry forwarder between Cube (USB) and GCS (UDP).
Runs independently of health monitor.
"""

import os
import sys
import time
import threading
import argparse

os.environ['MAVLINK20'] = '1'
from pymavlink import mavutil


def forward_fc_to_gcs(mav, out):
    """Forward messages from FC to GCS."""
    count = 0
    while True:
        try:
            msg = mav.recv_match(blocking=True, timeout=0.1)
            if msg:
                out.write(msg.get_msgbuf())
                count += 1
                if count % 1000 == 0:
                    print("[FC->GCS] %d messages" % count)
        except Exception as e:
            print("[FC->GCS] Error: %s" % e)
            time.sleep(0.1)


def forward_gcs_to_fc(mav, out):
    """Forward messages from GCS to FC."""
    count = 0
    while True:
        try:
            msg = out.recv_match(blocking=True, timeout=0.1)
            if msg:
                mav.write(msg.get_msgbuf())
                count += 1
                if count % 100 == 0:
                    print("[GCS->FC] %d messages" % count)
        except:
            pass


def main():
    parser = argparse.ArgumentParser(description='Bidirectional telemetry forwarder')
    parser.add_argument('--device', default='/dev/ttyACM0', help='Cube USB device')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    parser.add_argument('--dest', default='udpout:10.221.95.25:14550', help='GCS destination')
    args = parser.parse_args()

    print("Connecting to Cube on %s..." % args.device)
    mav = mavutil.mavlink_connection(args.device, baud=args.baud,
                                      source_system=255, source_component=0)

    print("Forwarding to %s..." % args.dest)
    out = mavutil.mavlink_connection(args.dest, source_system=255, source_component=0,
                                      input=True)

    # Start bidirectional forwarding
    t1 = threading.Thread(target=forward_fc_to_gcs, args=(mav, out), daemon=True)
    t2 = threading.Thread(target=forward_gcs_to_fc, args=(mav, out), daemon=True)
    t1.start()
    t2.start()

    print("Forwarding active. Press Ctrl+C to stop.")
    while True:
        time.sleep(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped")
