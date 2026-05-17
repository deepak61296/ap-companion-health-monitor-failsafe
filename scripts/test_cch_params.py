#!/usr/bin/env python3
import time
import sys
from pymavlink import mavutil

def main():
    print("Connecting to /dev/ttyACM0...")
    try:
        master = mavutil.mavlink_connection('/dev/ttyACM0', baud=115200)
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

    print("Waiting for heartbeat...")
    heartbeat = master.wait_heartbeat(timeout=10)
    if not heartbeat:
        print("Timeout waiting for heartbeat from Flight Controller!")
        sys.exit(1)
    print(f"Heartbeat received from System {master.target_system}, Component {master.target_component}")

    for param_name in [b'CCH_ENABLE', b'CCH_TIMEOUT', b'CCH_SVC_MASK']:
        print(f"Requesting parameter: {param_name.decode()}...")
        master.mav.param_request_read_send(
            master.target_system, master.target_component,
            param_name, -1
        )
        msg = master.recv_match(type='PARAM_VALUE', blocking=True, timeout=3)
        if msg:
            param_id_str = msg.param_id
            if isinstance(param_id_str, bytes):
                param_id_str = param_id_str.decode('utf-8', errors='ignore')
            param_id_str = param_id_str.rstrip('\x00')
            if param_id_str == param_name.decode():
                print(f"-> {param_id_str} = {msg.param_value} (type: {msg.param_type})")
            else:
                print(f"-> Received unexpected parameter {param_id_str} instead of {param_name.decode()}")
        else:
            print(f"-> Failed to read {param_name.decode()}")

if __name__ == '__main__':
    main()
