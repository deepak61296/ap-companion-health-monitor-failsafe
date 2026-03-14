#!/usr/bin/env python3
"""
Companion health monitor - sends COMPANION_HEALTH messages to FC.
Run this separately from telemetry forwarder.
"""

import os
import sys
import time
import argparse
import struct

os.environ['MAVLINK20'] = '1'
from pymavlink import mavutil
import psutil


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


def send_companion_health_raw(mav, services_status, watchdog_seq,
                               temperature, cpu_load, memory_used, disk_used,
                               gpu_load, status_flags):
    """Send COMPANION_HEALTH as raw MAVLink2 message."""
    payload = struct.pack('<IHhBBBBB',
        services_status, watchdog_seq, temperature,
        cpu_load, memory_used, disk_used, gpu_load, status_flags
    )

    msg_id = MAVLINK_MSG_ID_COMPANION_HEALTH
    seq = mav.mav.seq
    mav.mav.seq = (seq + 1) % 256

    header = struct.pack('<BBBBBBBHB',
        0xFD, len(payload), 0, 0, seq,
        mav.mav.srcSystem, mav.mav.srcComponent,
        msg_id & 0xFFFF, (msg_id >> 16) & 0xFF
    )

    crc = mavutil.x25crc(header[1:])
    crc.accumulate(payload)
    crc.accumulate_str(chr(81))  # CRC extra for COMPANION_HEALTH

    packet = header + payload + struct.pack('<H', crc.crc)
    mav.write(packet)


def main():
    parser = argparse.ArgumentParser(description='Companion health monitor')
    parser.add_argument('--device', default='/dev/ttyACM0', help='Cube USB device')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    parser.add_argument('--rate', type=float, default=1.0, help='Health message rate (Hz)')
    args = parser.parse_args()

    print("Connecting to Cube on %s..." % args.device)
    mav = mavutil.mavlink_connection(args.device, baud=args.baud,
                                      source_system=1, source_component=191)

    watchdog_seq = 0
    interval = 1.0 / args.rate
    print("Sending COMPANION_HEALTH at %.1f Hz" % args.rate)
    print("Press Ctrl+C to stop (will trigger failsafe after timeout)")

    while True:
        start = time.time()
        metrics = collect_metrics()

        # Send heartbeat
        mav.mav.heartbeat_send(18, 8, 0, 0, 4)

        # Send companion health
        send_companion_health_raw(mav,
            services_status=0,
            watchdog_seq=watchdog_seq,
            temperature=metrics['temperature'],
            cpu_load=metrics['cpu_load'],
            memory_used=metrics['memory_used'],
            disk_used=metrics['disk_used'],
            gpu_load=metrics['gpu_load'],
            status_flags=metrics['status_flags']
        )

        print("[HEALTH] cpu=%d%% mem=%d%% temp=%.1fC seq=%d" % (
            metrics['cpu_load'], metrics['memory_used'],
            metrics['temperature'] / 10.0, watchdog_seq))

        watchdog_seq = (watchdog_seq + 1) % 65536
        elapsed = time.time() - start
        time.sleep(max(0, interval - elapsed))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped - failsafe will trigger in %d seconds" % 5)
