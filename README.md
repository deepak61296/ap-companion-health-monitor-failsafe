# Companion Computer Health Monitor

Sends health telemetry from companion computers (RPi, Jetson, etc.) to ArduPilot. The flight controller triggers failsafe if the companion stops responding or reports critical issues.

**GSoC 2026 Project** | ArduPilot | Mentor: Jaime Machuca

## Demo

<a href="https://www.youtube.com/watch?v=s6RZwZTwf14">
  <img src="https://img.youtube.com/vi/s6RZwZTwf14/0.jpg" alt="Demo Video" width="480">
</a>

Click to watch - shows failsafe triggering when health monitor stops.

## Hardware Tests

Tested with CubeOrange flight controller:

**Raspberry Pi 4**
![RPi Test](screenshots/test_health_rpi.png)

**Jetson Nano**
![Jetson Test](screenshots/test_health_jetson.png)

## What's Working (Pre-GSoC)

- [x] COMPANION_HEALTH MAVLink message (ID 11061)
- [x] FC library with timeout-based failsafe
- [x] CCH_ENABLE and CCH_TIMEOUT parameters
- [x] ArduCopter integration
- [x] Python script with platform backends (RPi, Jetson, Generic)
- [x] Docker support
- [x] SITL and hardware testing

## GSoC Work (Planned)

- [ ] Services monitoring (track critical processes)
- [ ] Watchdog stall detection
- [ ] DataFlash logging
- [ ] Arming check
- [ ] ArduPlane/Rover support
- [ ] MAVLink upstream PR

## Timeline

| Period | Dates | Work |
|--------|-------|------|
| Community Bonding | May 1-24 | Code review with mentor |
| Week 1-2 | May 25 - Jun 7 | Services monitoring, watchdog |
| Week 3-4 | Jun 8-21 | Logging, arming check |
| Week 5-6 | Jun 22 - Jul 5 | Script improvements |
| Midterm | Jul 6-10 | Evaluation |
| Week 7-8 | Jul 11-19 | SITL tests, CI |
| Week 9-10 | Jul 20 - Aug 2 | Plane/Rover support |
| Week 11-12 | Aug 3-16 | MAVLink PR, docs |
| Final | Aug 17-24 | Final evaluation |

## Quick Start

```bash
git clone https://github.com/deepak61296/ap-companion-health-monitor-failsafe.git
cd ap-companion-health-monitor-failsafe
pip install -r requirements.txt

# SITL
python3 health_monitor.py --device udpout:127.0.0.1:14560 -v

# Hardware (USB)
python3 health_monitor.py --device /dev/ttyACM0 -v
```

## FC Parameters

- `CCH_ENABLE` - 0=off, 1=RTL, 2=Continue, 3=SmartRTL, 4=SmartRTL/Land, 5=Land
- `CCH_TIMEOUT` - seconds before failsafe (default 5)

## Message Format

COMPANION_HEALTH (ID 11061, 13 bytes):
- `cpu_load`, `memory_used`, `disk_used` - 0-100%
- `temperature` - decidegrees (450 = 45.0C)
- `gpu_load` - 0-100% or 255 if N/A
- `services_status` - bitmask of running services
- `watchdog_seq` - counter to detect stalls
- `status_flags` - warning flags

## Platforms

Auto-detects and uses optimized backend:
- **Raspberry Pi** - vcgencmd for temp, throttle detection
- **Jetson** - tegrastats for GPU, thermal zones
- **Generic Linux** - psutil + sysfs

## Related

- [ArduPilot fork](https://github.com/deepak61296/ardupilot/tree/companion-computer-health-monitor) - FC library
- [Demo video](https://www.youtube.com/watch?v=s6RZwZTwf14)

## License

GPLv3
