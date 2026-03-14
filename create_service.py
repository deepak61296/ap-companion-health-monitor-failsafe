#!/usr/bin/env python3
import os

service_content = """[Unit]
Description=Companion Health Monitor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/deepak/ardupilot/companion_script
ExecStart=/usr/bin/python3 /home/deepak/ardupilot/companion_script/scripts/health_and_forward.py --device /dev/ttyACM0 --dest udpout:10.221.95.25:14550 --rate 1.0
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

with open('/tmp/companion-health.service', 'w') as f:
    f.write(service_content)

print("Service file created at /tmp/companion-health.service")
print("Now run:")
print("  sudo mv /tmp/companion-health.service /etc/systemd/system/")
print("  sudo systemctl daemon-reload")
print("  sudo systemctl enable companion-health")
print("  sudo systemctl start companion-health")
print("  sudo systemctl status companion-health")
