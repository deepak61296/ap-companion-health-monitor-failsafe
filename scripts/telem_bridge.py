#!/usr/bin/env python3
"""
Simple telemetry bridge - forwards between serial and UDP, exposes local port.
"""

import os
import sys
import time
import socket
import threading
import argparse

os.environ['MAVLINK20'] = '1'
from pymavlink import mavutil


def main():
    parser = argparse.ArgumentParser(description='Telemetry bridge')
    parser.add_argument('--device', default='/dev/ttyACM0', help='Serial device')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    parser.add_argument('--out', default='10.221.95.25:14550', help='Remote GCS host:port')
    parser.add_argument('--local', type=int, default=14551, help='Local UDP port for health script')
    args = parser.parse_args()

    print("Connecting to FC on %s..." % args.device)
    fc = mavutil.mavlink_connection(args.device, baud=args.baud)

    remote_host, remote_port = args.out.split(':')
    remote_port = int(remote_port)

    # UDP socket for sending to remote GCS and local health script
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', args.local))
    sock.setblocking(False)

    print("Forwarding to %s:%d" % (remote_host, remote_port))
    print("Local port for health script: udp:127.0.0.1:%d" % args.local)
    print("Press Ctrl+C to stop")

    fc_count = 0
    gcs_count = 0
    local_count = 0
    last_print = time.time()

    while True:
        # Forward FC -> GCS and local
        try:
            msg = fc.recv_match(blocking=False)
            if msg:
                buf = msg.get_msgbuf()
                sock.sendto(buf, (remote_host, remote_port))
                sock.sendto(buf, ('127.0.0.1', args.local + 1))  # health script listens on local+1
                fc_count += 1
        except:
            pass

        # Receive from GCS or local health script
        try:
            data, addr = sock.recvfrom(4096)
            if data:
                fc.write(data)
                if addr[0] == '127.0.0.1':
                    local_count += 1
                else:
                    gcs_count += 1
        except BlockingIOError:
            pass
        except:
            pass

        # Print stats
        if time.time() - last_print >= 5:
            print("[BRIDGE] fc->out: %d  gcs->fc: %d  health->fc: %d" % (fc_count, gcs_count, local_count))
            last_print = time.time()

        time.sleep(0.001)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped")
