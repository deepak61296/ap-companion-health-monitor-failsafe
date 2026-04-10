#!/bin/bash
# Build pymavlink wheel with COMPANION_HEALTH message
#
# Usage:
#   ./scripts/build_pymavlink.sh
#
# This builds a wheel from ArduPilot's mavlink repo which includes
# the COMPANION_HEALTH message definition.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build/pymavlink"

echo "Building pymavlink wheel with COMPANION_HEALTH..."

# Create build directory
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Clone ArduPilot mavlink if not exists
if [ ! -d "mavlink" ]; then
    echo "Cloning ArduPilot mavlink repository..."
    git clone --depth 1 https://github.com/ArduPilot/mavlink.git
fi

# Install build dependencies
pip install --quiet lxml cython

# Build wheel
cd mavlink/pymavlink
MDEF="$BUILD_DIR/mavlink/message_definitions" pip wheel . --no-deps -w "$PROJECT_DIR/wheels"

echo ""
echo "Done! Wheel saved to: $PROJECT_DIR/wheels/"
echo "Install with: pip install wheels/pymavlink-*.whl"
