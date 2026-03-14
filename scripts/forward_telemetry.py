#!/usr/bin/env python3
"""Forward MAVLink telemetry from Cube to remote machine via UDP."""

import os
import sys
import argparse

os.environ['MAVLINK20'] = '1'
from pymavlink import mavutil


def main():
    parser = argparse.ArgumentParser(description='Forward MAVLink telemetry')
    parser.add_argument('--source', default='/dev/ttyACM1', help='Source device')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    parser.add_argument('--dest', default='udpout:10.221.95.25:14550', help='Destination')
    args = parser.parse_args()

    print(f"Connecting to {args.source}...")
    master = mavutil.mavlink_connection(args.source, baud=args.baud)

    print(f"Forwarding to {args.dest}...")
    out = mavutil.mavlink_connection(args.dest)

    print("Forwarding started. Press Ctrl+C to stop.")
    count = 0
    while True:
        msg = master.recv_match(blocking=True, timeout=1)
        if msg:
            out.mav.send(msg)
            count += 1
            if count % 100 == 0:
                print(f"Forwarded {count} messages")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped")
        sys.exit(0)
