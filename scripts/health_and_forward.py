#!/usr/bin/env python3
"""
Combined script that:
1. Sends COMPANION_HEALTH messages to the flight controller
2. Forwards all FC telemetry to a remote machine via UDP

Uses a single reader thread that handles all incoming messages.
"""

import os
import sys
import time
import threading
import argparse
import struct

os.environ['MAVLINK20'] = '1'
from pymavlink import mavutil
import psutil


# COMPANION_HEALTH message ID (custom message)
MAVLINK_MSG_ID_COMPANION_HEALTH = 11061


def get_cpu_temp():
    """Get CPU temperature in decidegrees C."""
    try:
        with open('/sys/devices/virtual/thermal/thermal_zone0/temp', 'r') as f:
            temp_milli = int(f.read().strip())
            return temp_milli // 100
    except:
        pass
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                if entries:
                    return int(entries[0].current * 10)
    except:
        pass
    return 0


def get_gpu_load():
    """Get GPU load percentage (Jetson specific)."""
    try:
        with open('/sys/devices/gpu.0/load', 'r') as f:
            return int(f.read().strip()) // 10
    except:
        pass
    return 0


def collect_metrics():
    """Collect system health metrics."""
    return {
        'cpu_load': int(psutil.cpu_percent()),
        'memory_used': int(psutil.virtual_memory().percent),
        'disk_used': int(psutil.disk_usage('/').percent),
        'temperature': get_cpu_temp(),
        'gpu_load': get_gpu_load(),
        'status_flags': 1
    }


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
    parser = argparse.ArgumentParser(description='Health monitor + telemetry forwarder')
    parser.add_argument('--device', default='/dev/ttyACM0', help='Cube USB device')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    parser.add_argument('--dest', default='udpout:10.221.95.25:14550', help='Forward destination')
    parser.add_argument('--rate', type=float, default=1.0, help='Health message rate (Hz)')
    args = parser.parse_args()

    print("Connecting to Cube on %s..." % args.device)
    mav = mavutil.mavlink_connection(args.device, baud=args.baud,
                                      source_system=1, source_component=191)

    print("Forwarding telemetry to %s..." % args.dest)
    out = mavutil.mavlink_connection(args.dest, source_system=1, source_component=191,
                                      input=True)

    watchdog_seq = 0
    interval = 1.0 / args.rate
    last_health_time = 0
    fwd_count = 0
    gcs_count = 0

    print("Sending COMPANION_HEALTH at %.1f Hz" % args.rate)
    print("Press Ctrl+C to stop")

    while True:
        now = time.time()

        # Send health message at specified rate
        if now - last_health_time >= interval:
            metrics = collect_metrics()

            # Send heartbeat to both
            mav.mav.heartbeat_send(18, 8, 0, 0, 4)
            out.mav.heartbeat_send(18, 8, 0, 0, 4)

            # Send COMPANION_HEALTH to both
            send_companion_health_raw(mav,
                services_status=0, watchdog_seq=watchdog_seq,
                temperature=metrics['temperature'],
                cpu_load=metrics['cpu_load'],
                memory_used=metrics['memory_used'],
                disk_used=metrics['disk_used'],
                gpu_load=metrics['gpu_load'],
                status_flags=metrics['status_flags']
            )
            send_companion_health_raw(out,
                services_status=0, watchdog_seq=watchdog_seq,
                temperature=metrics['temperature'],
                cpu_load=metrics['cpu_load'],
                memory_used=metrics['memory_used'],
                disk_used=metrics['disk_used'],
                gpu_load=metrics['gpu_load'],
                status_flags=metrics['status_flags']
            )

            print("[HEALTH] cpu=%d%% mem=%d%% temp=%.1fC seq=%d fwd=%d" % (
                metrics['cpu_load'], metrics['memory_used'],
                metrics['temperature'] / 10.0, watchdog_seq, fwd_count))

            watchdog_seq = (watchdog_seq + 1) % 65536
            last_health_time = now

        # Forward messages from FC to GCS (non-blocking)
        try:
            msg = mav.recv_match(blocking=False)
            if msg:
                out.write(msg.get_msgbuf())
                fwd_count += 1
        except:
            pass

        # Forward messages from GCS to FC (non-blocking)
        try:
            msg = out.recv_match(blocking=False)
            if msg:
                mav.write(msg.get_msgbuf())
                gcs_count += 1
        except:
            pass

        # Small sleep to prevent CPU spinning
        time.sleep(0.001)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped")
