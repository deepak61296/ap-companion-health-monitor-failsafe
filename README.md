# Companion Computer Health Monitor

Sends health telemetry from a companion computer (Jetson, RPi, etc.) to ArduPilot via a custom `COMPANION_HEALTH` MAVLink message. The flight controller can trigger failsafe actions if the companion stops responding.

## Requirements

- Python 3.8+
- ArduPilot with AP_CompanionHealth library (see [ardupilot fork](https://github.com/deepak61296/ardupilot/tree/companion-computer-health-monitor))
- pymavlink built with COMPANION_HEALTH message

## Install

```bash
# Clone
git clone https://github.com/deepak61296/companion-health-monitor.git
cd companion-health-monitor

# Setup venv and install deps
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Build pymavlink with custom message (from your ardupilot clone)
cd /path/to/ardupilot
MDEF=modules/mavlink/message_definitions pip install modules/mavlink/pymavlink
```

## Usage

```bash
# SITL testing
python health_monitor.py --device udpout:127.0.0.1:14560 --verbose

# USB to flight controller
python health_monitor.py --device /dev/ttyACM0 --verbose

# With config file
python health_monitor.py --config config.yaml
```

## SITL Testing

Terminal 1:
```bash
cd ~/ardupilot
./Tools/autotest/sim_vehicle.py -v Copter
# In MAVProxy:
link add udp:0.0.0.0:14560
param set CCH_ENABLE 1
```

Terminal 2:
```bash
source venv/bin/activate
python health_monitor.py --device udpout:127.0.0.1:14560 --verbose
```

## Configuration

Create `config.yaml`:
```yaml
connection:
  device: "/dev/ttyACM0"
  baud: 115200

monitoring:
  rate_hz: 1.0

thresholds:
  temp_throttle: 80.0
  temp_overheat: 85.0
  memory_low: 90
  disk_low: 95
```

## Message Format

`COMPANION_HEALTH` (ID 11061):
- `cpu_load` - CPU % (0-100)
- `memory_used` - RAM % (0-100)
- `disk_used` - Disk % (0-100)
- `temperature` - Temp in decidegrees (450 = 45.0C)
- `gpu_load` - GPU % or 255 if N/A
- `status_flags` - Bitmask (throttled, overheating, low_memory, low_disk)
- `watchdog_seq` - Incrementing counter to detect stalls

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## Platform Support

Auto-detects platform and uses optimized backend:
- **Jetson** - Uses tegrastats for GPU, thermal zones for temp
- **Raspberry Pi** - Uses vcgencmd for temp
- **Generic Linux** - Uses psutil + sysfs

## FC Parameters

On the flight controller (set via MAVProxy or GCS):
- `CCH_ENABLE` - Failsafe action (0=disabled, 1=RTL, 5=Land, etc.)
- `CCH_TIMEOUT` - Seconds without message before failsafe (default 5)

## License

GPLv3
