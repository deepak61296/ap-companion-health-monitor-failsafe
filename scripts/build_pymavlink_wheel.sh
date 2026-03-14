#!/bin/bash
# Build pymavlink wheel with COMPANION_HEALTH message for Docker
#
# Usage: ./scripts/build_pymavlink_wheel.sh
#
# This creates a wheel in ./wheels/ that can be used in Docker builds

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPANION_DIR="$(dirname "$SCRIPT_DIR")"
ARDUPILOT_DIR="$(dirname "$COMPANION_DIR")"
MAVLINK_DIR="$ARDUPILOT_DIR/modules/mavlink"
PYMAVLINK_DIR="$MAVLINK_DIR/pymavlink"
WHEEL_DIR="$COMPANION_DIR/wheels"

echo "Building pymavlink wheel..."
echo "  ArduPilot: $ARDUPILOT_DIR"
echo "  MAVLink:   $MAVLINK_DIR"
echo "  Output:    $WHEEL_DIR"

# Check mavlink exists
if [ ! -d "$PYMAVLINK_DIR" ]; then
    echo "Error: pymavlink not found at $PYMAVLINK_DIR"
    echo "Make sure you're running from within the ArduPilot repository"
    exit 1
fi

# Check COMPANION_HEALTH exists
if ! grep -q "COMPANION_HEALTH" "$MAVLINK_DIR/message_definitions/v1.0/ardupilotmega.xml"; then
    echo "Warning: COMPANION_HEALTH message not found in ardupilotmega.xml"
    echo "The wheel may not include the custom message"
fi

# Create output directory
mkdir -p "$WHEEL_DIR"

# Build wheel
cd "$PYMAVLINK_DIR"
MDEF="$MAVLINK_DIR/message_definitions" pip wheel . --no-deps -w "$WHEEL_DIR"

echo ""
echo "Done! Wheel created:"
ls -la "$WHEEL_DIR"/*.whl

echo ""
echo "To use in Docker, copy the wheel to companion_script/wheels/"
echo "and update Dockerfile to use it instead of building from git."
