"""
MAVLink constants and utilities for COMPANION_HEALTH message.

AP_FLAKE8_CLEAN
"""

import struct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pymavlink import mavutil

# COMPANION_HEALTH message (ID 11061, 13 bytes payload)
MAVLINK_MSG_ID_COMPANION_HEALTH = 11061
COMPANION_HEALTH_CRC_EXTRA = 81

# MAVLink component identifiers
MAV_TYPE_ONBOARD_CONTROLLER = 18
MAV_COMP_ID_ONBOARD_COMPUTER = 191
MAV_AUTOPILOT_INVALID = 8
MAV_MODE_FLAG_CUSTOM_MODE_ENABLED = 1
MAV_STATE_ACTIVE = 4

# Status flag bits (matches FC-side definitions)
STATUS_FLAG_THROTTLED = 0x01    # CPU frequency capped
STATUS_FLAG_OVERHEATING = 0x02  # Temperature > 85C
STATUS_FLAG_LOW_MEMORY = 0x04   # Memory > 90%
STATUS_FLAG_LOW_DISK = 0x08     # Disk > 95%


def send_companion_health_raw(
    mav: "mavutil.mavfile",
    services_status: int,
    watchdog_seq: int,
    temperature: int,
    cpu_load: int,
    memory_used: int,
    disk_used: int,
    gpu_load: int,
    status_flags: int
) -> None:
    """Send COMPANION_HEALTH as raw MAVLink2 packet.

    Use this when pymavlink doesn't have native companion_health_send().

    Args:
        mav: MAVLink connection from mavutil
        services_status: 32-bit bitmask of running services
        watchdog_seq: Stall detection counter (0-65535)
        temperature: Board temp in decidegrees (450 = 45.0C)
        cpu_load: CPU usage 0-100%
        memory_used: RAM usage 0-100%
        disk_used: Disk usage 0-100%
        gpu_load: GPU usage 0-100%, or 255 if N/A
        status_flags: Warning flags bitmask
    """
    # Pack payload: uint32 + uint16 + int16 + 5x uint8 = 13 bytes
    payload = struct.pack(
        '<IHhBBBBB',
        services_status,
        watchdog_seq,
        temperature,
        cpu_load,
        memory_used,
        disk_used,
        gpu_load,
        status_flags
    )

    seq = mav.mav.seq
    mav.mav.seq = (seq + 1) % 256

    # MAVLink2 header (10 bytes)
    header = struct.pack(
        '<BBBBBBBHB',
        0xFD,  # MAVLink2 magic
        len(payload),
        0,  # incompat_flags
        0,  # compat_flags
        seq,
        mav.mav.srcSystem,
        mav.mav.srcComponent,
        MAVLINK_MSG_ID_COMPANION_HEALTH & 0xFFFF,
        (MAVLINK_MSG_ID_COMPANION_HEALTH >> 16) & 0xFF
    )

    # Calculate CRC using mavutil's x25crc
    from pymavlink import mavutil as _mavutil
    crc = _mavutil.x25crc(header[1:])
    crc.accumulate(payload)
    crc.accumulate_str(chr(COMPANION_HEALTH_CRC_EXTRA))

    # Send complete packet
    mav.write(header + payload + struct.pack('<H', crc.crc))
