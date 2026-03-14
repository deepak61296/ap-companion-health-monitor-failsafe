# Companion Computer Health Monitor

A MAVLink-based health monitoring system for ArduPilot companion computers. Sends `COMPANION_HEALTH` messages (ID 11061) to the flight controller.

## Features

- **Cross-platform**: Raspberry Pi, Jetson Nano/Xavier/Orin, generic Linux
- **Auto-detection**: Automatically uses optimized backend for your platform
- **Easy setup**: Single script installs everything
- **Flexible connection**: USB, UART, or UDP
- **Docker support**: Optional containerized deployment

## Quick Start

### Automated Setup (Recommended)

```bash
cd ~/ardupilot/companion_script
./scripts/setup.sh
```

This script:
- Detects your platform (Jetson/Pi/generic)
- Creates a Python virtual environment
- Builds pymavlink with COMPANION_HEALTH message
- Installs all dependencies
- Creates config file
- Verifies everything works

### Run

```bash
# Using config file
./scripts/run.sh

# Or with USB connection
./scripts/run.sh --device /dev/ttyACM0 --verbose

# Or with UDP (for SITL)
./scripts/run.sh --device udpout:127.0.0.1:14560 --verbose
```

---

## Jetson Nano Setup (USB Connection)

### Step 1: Hardware Connection

Connect Cube Orange to Jetson via USB cable:
- Plug USB cable into Cube Orange's USB port
- Plug other end into Jetson's USB port
- The Cube will appear as `/dev/ttyACM0`

### Step 2: Check USB Device

```bash
# List USB devices
ls -la /dev/ttyACM*

# You should see:
# /dev/ttyACM0
```

If you don't see it:
```bash
# Check dmesg for USB connection
dmesg | tail -20

# Add user to dialout group (for serial access)
sudo usermod -a -G dialout $USER
# Log out and back in for this to take effect
```

### Step 3: Run Setup

```bash
cd ~/ardupilot/companion_script
./scripts/setup.sh
```

Expected output:
```
==============================================
 Companion Health Monitor - Setup Script
==============================================

[INFO] Detecting platform...
[OK] Detected: NVIDIA Jetson
[OK] Python 3.8.10 found
[OK] pip found
[OK] MAVLink found at /home/user/ardupilot/modules/mavlink
[OK] COMPANION_HEALTH message found in ardupilotmega.xml
[OK] Virtual environment created
[OK] pymavlink built and installed
[OK] Runtime dependencies installed
[OK] COMPANION_HEALTH message verified (ID: 11061)

==============================================
 Setup completed successfully!
==============================================
```

### Step 4: Configure (Optional)

Edit `config.yaml` for USB connection:
```yaml
connection:
  device: "/dev/ttyACM0"
  baud: 115200
  source_system: 1
  source_component: 191

monitoring:
  rate_hz: 1.0
  disk_path: "/"
```

### Step 5: Run

```bash
# Option 1: Use config file
./scripts/run.sh

# Option 2: Command line (no config needed)
./scripts/run.sh --device /dev/ttyACM0 --verbose
```

Expected output:
```
12:34:56 INFO: Using jetson backend
12:34:56 INFO: Connecting to /dev/ttyACM0
12:34:56 INFO: Connected successfully
12:34:56 INFO: Sending COMPANION_HEALTH at 1.0 Hz
12:34:56 DEBUG: Sent: cpu=5% mem=30% disk=45% temp=42.0C gpu=0% flags=0x00 seq=1
12:34:57 DEBUG: Sent: cpu=4% mem=30% disk=45% temp=42.0C gpu=0% flags=0x00 seq=2
```

### Step 6: Verify on Ground Station

In Mission Planner or QGroundControl:
- Connect to Cube Orange
- Check MAVLink Inspector for `COMPANION_HEALTH` message
- Or use MAVProxy: `status` command shows all messages

---

## Raspberry Pi Setup

### Hardware Connection (USB)

Same as Jetson - connect Cube Orange via USB cable.

### Setup

```bash
cd ~/ardupilot/companion_script
./scripts/setup.sh
./scripts/run.sh --device /dev/ttyACM0 --verbose
```

### UART Connection (Alternative)

For direct UART connection (faster, more reliable):

1. Enable UART:
```bash
sudo raspi-config
# Interface Options -> Serial Port
# Login shell: No
# Hardware: Yes
```

2. Wire connections:
```
Pi GPIO14 (TX) -> Cube TELEM2 RX (pin 3)
Pi GPIO15 (RX) -> Cube TELEM2 TX (pin 2)
Pi GND        -> Cube TELEM2 GND (pin 6)
```

3. Configure:
```yaml
connection:
  device: "/dev/ttyAMA0"
  baud: 921600
```

4. Set Cube parameters:
```
SERIAL2_PROTOCOL = 2 (MAVLink2)
SERIAL2_BAUD = 921
```

---

## Testing with SITL

### Terminal 1: Start SITL

```bash
cd ~/ardupilot
./Tools/autotest/sim_vehicle.py -v Copter --console --map
```

Wait for `STABILIZE>` prompt, then add UDP input:
```
link add udp:0.0.0.0:14560
```

### Terminal 2: Run Health Monitor

```bash
cd ~/ardupilot/companion_script
./scripts/run.sh --device udpout:127.0.0.1:14560 --verbose
```

### Verify in MAVProxy

```
status
```

Look for:
```
COMPANION_HEALTH {services_status: 0, watchdog_seq: 42, temperature: 450, cpu_load: 5, ...}
```

---

## Configuration Reference

### config.yaml

```yaml
# Connection settings
connection:
  device: "/dev/ttyACM0"           # USB: /dev/ttyACM0, UART: /dev/ttyAMA0, UDP: udpout:IP:PORT
  baud: 115200                      # Baud rate (USB/UART only)
  source_system: 1                  # MAVLink system ID
  source_component: 191             # MAVLink component ID (191 = onboard computer)

# Monitoring settings
monitoring:
  rate_hz: 1.0                      # Messages per second
  disk_path: "/"                    # Filesystem to monitor

# Thresholds for status flags
thresholds:
  temp_throttle: 80.0               # Temperature (°C) for throttle warning
  temp_overheat: 85.0               # Temperature (°C) for overheat warning
  memory_low: 90                    # Memory (%) for low memory warning
  disk_low: 95                      # Disk (%) for low disk warning

# Platform override (auto-detect if not set)
# platform: "jetson"                # Options: generic, raspberry_pi, jetson
```

### Command-Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--config` | `-c` | Path to YAML config file |
| `--device` | `-d` | MAVLink connection string |
| `--baud` | `-b` | Baud rate for serial |
| `--rate` | `-r` | Send rate in Hz |
| `--platform` | `-p` | Force platform backend |
| `--verbose` | `-v` | Enable debug logging |

Command-line arguments override config file values.

---

## Message Format

### COMPANION_HEALTH (ID 11061)

| Field | Type | Description |
|-------|------|-------------|
| services_status | uint32 | Service bitmask (reserved) |
| watchdog_seq | uint16 | Sequence counter (detects stalls) |
| temperature | int16 | Temperature × 10 (e.g., 450 = 45.0°C) |
| cpu_load | uint8 | CPU usage 0-100% |
| memory_used | uint8 | RAM usage 0-100% |
| disk_used | uint8 | Disk usage 0-100% |
| gpu_load | uint8 | GPU usage 0-100%, or 255 if N/A |
| status_flags | uint8 | Health status flags |

### Status Flags

| Bit | Flag | Trigger |
|-----|------|---------|
| 0 | THROTTLED | Temperature > 80°C |
| 1 | OVERHEATING | Temperature > 85°C |
| 2 | LOW_MEMORY | RAM usage > 90% |
| 3 | LOW_DISK | Disk usage > 95% |

---

## Docker Deployment (Optional)

### Build

```bash
cd ~/ardupilot/companion_script

# Build pymavlink wheel first
./scripts/build_pymavlink_wheel.sh

# Build Docker image
docker build -t companion-health .
```

### Run

```bash
# Create config.yaml first, then:
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## Troubleshooting

### "Permission denied: /dev/ttyACM0"

```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```

### "No module named 'pymavlink'"

Run setup script again:
```bash
./scripts/setup.sh
```

### "companion_health_send not found"

The pymavlink wasn't built with COMPANION_HEALTH. Re-run setup:
```bash
rm -rf venv
./scripts/setup.sh
```

### "No USB device found"

1. Check cable connection
2. Try different USB port
3. Check dmesg: `dmesg | grep -i usb | tail -20`
4. Make sure Cube is powered

### Messages not appearing in GCS

1. Check connection string matches
2. Verify baud rate
3. For USB, usually no baud rate setting needed on Cube side
4. Check MAVLink Inspector in Mission Planner

---

## Project Structure

```
companion_script/
├── health_monitor.py           # Main entry point
├── config.yaml                 # Your configuration (create from example)
├── config.yaml.example         # Example configuration
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── Dockerfile                  # Docker build
├── docker-compose.yml          # Docker deployment
├── scripts/
│   ├── setup.sh               # Automated setup
│   ├── run.sh                 # Run script
│   └── build_pymavlink_wheel.sh  # Build wheel for Docker
└── companion_health/           # Main package
    ├── __init__.py
    ├── config.py              # Config loader
    ├── monitor.py             # HealthMonitor class
    └── backends/
        ├── __init__.py        # Auto-detection
        ├── base.py            # Abstract backend
        ├── generic.py         # Generic Linux
        ├── raspberry_pi.py    # Pi with vcgencmd
        └── jetson.py          # Jetson with sysfs
```

---

## Future Work

- [ ] FC-side `AP_CompanionHealth` library
- [ ] Failsafe actions when companion degrades
- [ ] Service monitoring (systemd services)
- [ ] Automatic reconnection with backoff
- [ ] Web dashboard for monitoring

---

## License

GPLv3 (same as ArduPilot)
