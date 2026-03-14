#!/bin/bash
#
# Companion Health Monitor - Run Script
#
# Usage:
#   ./scripts/run.sh                    # Use config.yaml
#   ./scripts/run.sh --device /dev/ttyACM0 --verbose
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPANION_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$COMPANION_DIR/venv"

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Error: Virtual environment not found!"
    echo "Run ./scripts/setup.sh first"
    exit 1
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Set MAVLink 2.0
export MAVLINK20=1

# Run with arguments or default config
cd "$COMPANION_DIR"
if [ $# -eq 0 ]; then
    # No arguments, use config file
    if [ -f "config.yaml" ]; then
        exec python health_monitor.py --config config.yaml --verbose
    else
        echo "Error: config.yaml not found"
        echo "Create it from config.yaml.example or pass arguments"
        exit 1
    fi
else
    # Pass all arguments to health_monitor.py
    exec python health_monitor.py "$@"
fi
