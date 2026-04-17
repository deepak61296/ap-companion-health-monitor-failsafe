#!/bin/bash
# Simulates the mavlink-router production environment
# Connects to ArduPilot SITL and opens ports for health_monitor, mavros, etc.
#
# Prerequisites: mavlink-routerd must be installed or built and available in PATH.
# Build from source: https://github.com/mavlink-router/mavlink-router

set -e

ROUTER_BIN=$(command -v mavlink-routerd 2>/dev/null || true)

if [ -z "$ROUTER_BIN" ]; then
    echo "ERROR: mavlink-routerd not found in PATH."
    echo "Build it from https://github.com/mavlink-router/mavlink-router"
    echo "and add to PATH, or pass it as first argument."
    echo "Usage: $0 [path/to/mavlink-routerd]"
    exit 1
fi

echo "Starting MAVLink Router for SITL..."
echo "  SITL Input: TCP 5760"
echo "  Health Monitor Output: UDP 14551"
echo "  Other Apps: UDP 14552, 14553"

CONF=$(mktemp /tmp/sitl_router.XXXXXX.conf)
cat << 'EOF' > "$CONF"
[General]
TcpServerPort=0

[TcpEndpoint SITL]
Mode = client
Address = 127.0.0.1
Port = 5760

[UdpEndpoint HealthMonitor]
Mode = Server
Address = 127.0.0.1
Port = 14551

[UdpEndpoint App2]
Mode = Normal
Address = 127.0.0.1
Port = 14552

[UdpEndpoint App3]
Mode = Normal
Address = 127.0.0.1
Port = 14553
EOF

trap "rm -f $CONF" EXIT
"$ROUTER_BIN" -t 0 -c "$CONF"
