#!/bin/bash
# Install companion health monitor as a systemd service
#
# Usage: sudo ./install.sh [device]
#   device defaults to /dev/ttyACM0. Prefer the stable /dev/serial/by-id/
#   path so USB enumeration order cannot swap devices between boots.

set -e

DEVICE="${1:-/dev/ttyACM0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./install.sh)"
    exit 1
fi

# Determine the actual user (if run with sudo, use SUDO_USER)
ACTUAL_USER="${SUDO_USER:-root}"
echo "Installing service for user: $ACTUAL_USER"

# Install the module globally or for the user
echo "Installing companion-health-monitor package..."
sudo -u "$ACTUAL_USER" python3 -m pip install -e "$PROJECT_ROOT" --user --break-system-packages 2>/dev/null || \
sudo -u "$ACTUAL_USER" python3 -m pip install -e "$PROJECT_ROOT" --user

# Create dynamic service file
SERVICE_FILE="/etc/systemd/system/companion-health.service"
echo "Creating systemd service at $SERVICE_FILE..."
sed -e "s/COMPANION_USER/$ACTUAL_USER/g" -e "s|COMPANION_DEVICE|$DEVICE|g" "$SCRIPT_DIR/companion-health.service" > "$SERVICE_FILE"

# Reload systemd
systemctl daemon-reload

# Enable and restart service
systemctl enable companion-health.service
systemctl restart companion-health.service

echo "Service installed and started (device: $DEVICE)"
echo "Check status with: systemctl status companion-health"
echo "View logs with: journalctl -u companion-health -f"
