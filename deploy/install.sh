#!/bin/bash
# Install companion health monitor as a systemd service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./install_service.sh)"
    exit 1
fi

# Install pymavlink if not present
pip3 install pymavlink psutil --quiet 2>/dev/null || true

# Copy service file
cp "$SCRIPT_DIR/companion-health.service" /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable and start service
systemctl enable companion-health.service
systemctl start companion-health.service

echo "Service installed and started"
echo "Check status with: systemctl status companion-health"
echo "View logs with: journalctl -u companion-health -f"
