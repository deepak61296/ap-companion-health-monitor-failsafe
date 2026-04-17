# Companion Computer Health Monitor

Sends health telemetry from companion computers (RPi, Jetson, etc.) to ArduPilot. The flight controller triggers failsafe if the companion stops responding or reports critical issues.

**GSoC 2026 Project** | ArduPilot | Mentor: Jaime Machuca

## System Overview

This project provides a robust, cross-platform telemetry pipeline to ensure drones safely handle companion computer failures. 

1. **Flight Controller** (`AP_CompanionHealth` library): Monitors incoming MAVLink heartbeats, validates computer state, and executes strict failsafe handling (RTL, Land, SmartRTL) upon timeouts.
2. **Companion Daemon**: Cross-platform Python service reading kernel metrics (CPU, RAM, GPU, thermals) and pushing status to ArduPilot at 1Hz.

## Demo

**[Watch Demo Video](https://www.youtube.com/watch?v=s6RZwZTwf14)** - Demonstrates ArduCopter failsafe triggering when a custom companion computer health script ceases operation.

## Latest Updates
*   **[April 2026] MAVLink Router Decoupling:** Successfully configured and tested `mavlink-router` architecture on SITL to ensure the health monitor script does not monopolize the flight controller's telemetry stream, allowing MAVROS and DroneKit to run concurrently.

## Development Roadmap

### Pre-GSoC Implementation (v0.1)
*   **MAVLink Protocol**: Local definition of `COMPANION_HEALTH` message.
*   **FC Message Handling**: `AP_CompanionHealth.cpp` receives and stores metrics.
*   **FC Failsafe Core**: Strict timeout-based failsafe detection conforming to ArduPilot standards (`events.cpp`).
*   **Platform Support**: Python foundation with platform metrics for RPi (`vcgencmd`), Jetson (`tegrastats`), and general Linux (`psutil`).
*   **Hardware Validation**: Tested via USB on Raspberry Pi 4 and Jetson Nano with CubeOrange.

### GSoC Timeline & Deliverables

#### Community Bonding (May 1-24): Architecture & Review
*   Code review with mentor.
*   Finalize architecture and refactor `AP_CompanionHealth.cpp` based on feedback.

#### Week 1-2 (May 25 - Jun 7): Services array & Watchdog loops
*   **Services**: implement active process discovery in `ServicesMonitor`, add the `CCH_SVC_MASK` parameter, and establish bitwise failing states.
*   **Watchdog**: Track sequence values in C++ and trigger failsafes to catch frozen OS processes.
*   **Filtering**: Add moving averages for CPU/Temp metrics, and exponential backoff for reconnection loops.

#### Week 3-4 (Jun 8-21): Logging & Arming Checks
*   **Arming**: Query `is_healthy()` inside `AP_Arming.cpp` to block takeoff on disconnected or critical states.
*   **DataFlash**: Define `LOG_CCH_MSG` in `LogStructure.h` and implement DataFlash routing in `AP_Logger`.

#### Week 5-6 (Jun 22 - Jul 5): Deployment Tooling & Telemetry Routing
*   Create `deploy/mavlink-router/usb.conf` to multiplex the FC USB/UART stream across multiple UDP endpoints (ensuring MAVROS, DroneKit, and Health Monitor all run concurrently).
*   Create `deploy/health_monitor.service` systemd daemon for automatic boot execution.
*   Create shell installation scripts and Docker compose files for containerized packaging.

#### Midterm (Jul 6-10): Evaluation
*   Midterm evaluations.

#### Week 7-8 (Jul 11-19): SITL Testing & CI
*   Finalize the `CompanionHealthFailsafe` strictly deterministic Python autotests.
*   Integrate tests into GitHub Actions workflows.

#### Week 9-10 (Jul 20 - Aug 2): Ecosystem Expansion
*   Register metrics and parameter groups in `ArduPlane/Plane.h` and `Rover/Rover.h`.
*   Port the `events.cpp` failsafe routing from Copter pattern to Plane and Rover.

#### Week 11-12 (Aug 3-16): MAVLink Upstream & Documentation
*   Submit final XML specifications upstream to `mavlink/mavlink`.
*   Author official ArduPilot wiki pages detailing CCH parameters and architecture.

#### Final (Aug 17-24): Final Evaluation
*   Code freeze and final reviews.

## Future Scope

Development will continue beyond the official GSoC timeline:
*   Testing compatibility with previous companion computer GSoC projects.
*   Implementing hardware backends for Arduino Uno R4 / Ventuno.
*   Creating a highly-optimized `C++` MAVSDK alternate implementation for extremely resource-constrained SBCs.

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/deepak61296/ap-companion-health-monitor-failsafe.git
cd ap-companion-health-monitor-failsafe
pip install -e .

# SITL testing
python -m companion_health --device udpout:127.0.0.1:14560 -v

# Hardware (USB)
python -m companion_health --device /dev/ttyACM0 -v

# With config file
python -m companion_health --config config/sitl.yaml -v
```

## Architecture Documentation

### Message Format
COMPANION_HEALTH (ID 11061, 13 bytes):
- `cpu_load`, `memory_used`, `disk_used` - 0-100%
- `temperature` - decidegrees (450 = 45.0C)
- `gpu_load` - 0-100% or 255 if N/A
- `services_status` - bitmask of running services
- `watchdog_seq` - counter to detect stalls
- `status_flags` - warning flags

### FC Parameters Configured
- `CCH_ENABLE` - 0=off, 1=RTL, 2=Continue, 3=SmartRTL, 4=SmartRTL/Land, 5=Land
- `CCH_TIMEOUT` - seconds without heartbeat before triggering failsafe

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/unit/ -v

# Run linter
flake8 src/
```

## Related

- [ArduPilot fork](https://github.com/deepak61296/ardupilot/tree/companion-computer-health-monitor) - Flight controller system library
- [Video Demo](https://www.youtube.com/watch?v=s6RZwZTwf14)

## License
GPLv3
