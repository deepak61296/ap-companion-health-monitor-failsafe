# Companion Computer Health Monitor

Monitors the health of companion computers (Raspberry Pi, Jetson Nano, generic Linux) and reports metrics to ArduPilot over MAVLink. The flight controller uses these reports to trigger failsafe actions (RTL, Land, SmartRTL) if the companion stops responding or enters a critical state.

**GSoC 2026 Project** | ArduPilot | Mentor: Jaime Machuca

## Demo

**[Watch Demo Video](https://www.youtube.com/watch?v=s6RZwZTwf14)** - ArduCopter failsafe triggering when the companion health script stops sending messages.

## Latest Updates

*   **[April 2026]** MAVLink Router architecture configured and tested on SITL. The health monitor now connects through `mavlink-router` instead of directly to the serial port, allowing MAVROS, DroneKit, and other apps to run concurrently.

## Project Structure

```
companion-health-monitor/
  src/companion_health/
    monitor.py           # Main telemetry loop (1 Hz COMPANION_HEALTH sender)
    state.py             # State machine (DISCONNECTED/HEALTHY/DEGRADED/CRITICAL)
    mavlink.py           # Raw MAVLink packet encoding for COMPANION_HEALTH
    config.py            # YAML configuration loader
    cli.py               # Command-line argument parsing
    backends/
      base.py            # Abstract MetricsBackend interface
      generic.py         # Generic Linux backend (psutil)
      raspberry_pi.py    # RPi backend (vcgencmd for throttle/temp)
      jetson.py          # Jetson backend (tegrastats for GPU/temp)
    services/
      monitor.py         # ServicesMonitor class (placeholder, pgrep not yet implemented)
  config/
    sitl.yaml            # SITL testing config
    raspberry_pi.yaml    # RPi hardware config
    jetson.yaml          # Jetson hardware config
  deploy/
    mavlink-router/
      usb.conf           # Production mavlink-router config (USB)
    companion-health.service  # systemd unit file (paths need updating)
    install.sh           # Service installer script
    Dockerfile           # Docker image (references old file structure)
    docker-compose.yml   # Docker compose setup
  scripts/
    run_sitl_router.sh   # SITL mavlink-router helper
    build_pymavlink.sh   # pymavlink wheel builder
  tests/
    unit/                # Unit tests for backends, config, state
    integration/         # Integration tests for SITL and hardware
  screenshots/
    test_health_rpi.png  # RPi hardware test screenshot
    test_health_jetson.png  # Jetson hardware test screenshot
```

ArduPilot fork files (branch: `companion-computer-health-monitor`):
```
ardupilot/
  libraries/AP_CompanionHealth/
    AP_CompanionHealth.h       # Library header (State enum, CompanionStatus struct, parameters)
    AP_CompanionHealth.cpp     # Message handler, timeout detection, GCS reporting
    AP_CompanionHealth_config.h  # Build enable/disable flag
  ArduCopter/
    events.cpp                 # Failsafe routing (RTL/Land/SmartRTL based on CCH_ENABLE)
    Copter.h                   # g2 parameter group registration
    Parameters.cpp             # CCH_ENABLE and CCH_TIMEOUT parameter definitions
  Tools/autotest/
    arducopter.py              # CompanionHealthFailsafe SITL autotest
```

## Implementation Progress

### Pre-GSoC Implementation (v0.1)

These features were built before GSoC and form the foundation. Hardware tests were done on a pre-GSoC prototype. They will be reverified with mentors during GSoC community bonding.

| Component | Description | SITL (verified) | RPi 4 (pre-GSoC, reverify) | Jetson Nano (pre-GSoC, reverify) |
| :--- | :--- | :---: | :---: | :---: |
| MAVLink message | `COMPANION_HEALTH` (ID 11061, 13 bytes) defined locally in `ardupilotmega.xml` | Pass | Pass | Pass |
| FC message handling | `AP_CompanionHealth::handle_message()` receives and stores all fields | Pass | Pass | Pass |
| FC timeout failsafe | `update()` sets `DISCONNECTED` when no message for `CCH_TIMEOUT` seconds | Pass | Pass | Pass |
| FC state machine | `DISCONNECTED` > `HEALTHY` > `DEGRADED` > `CRITICAL` transitions | Pass | Pass | Pass |
| FC parameters | `CCH_ENABLE` (failsafe action 0-7) and `CCH_TIMEOUT` (seconds, default 5) | Pass | Pass | Pass |
| FC GCS messages | "Companion computer connected" on first message, periodic report every 10s | Pass | Pass | Pass |
| Copter failsafe routing | `events.cpp` routes action (RTL/Land/SmartRTL) based on `CCH_ENABLE` value | Pass | Pass | Pass |
| Python metrics | CPU, memory, disk, temperature, GPU collection via psutil | Pass | Pass | Pass |
| Platform backends | Generic Linux (psutil), RPi (vcgencmd), Jetson (tegrastats) | Pass | Pass | Pass |
| YAML config loading | Connection string, send rate, platform override, services list | Pass | Pass | Pass |
| Python state machine | Mirrors FC-side thresholds (80% warn, 95% critical, 75/90C temp) | Pass | N/A | N/A |

### Recently Completed

| Component | Description | SITL (verified) | Hardware |
| :--- | :--- | :---: | :---: |
| MAVLink router | `mavlink-router` multiplexes FC stream to multiple UDP endpoints | Pass | Pending |
| SITL autotest | `CompanionHealthFailsafe` in `arducopter.py` (timeout, reconnect, critical flags) | Pass | N/A |

### GSoC Deliverables (Not Yet Implemented)

| Task | Target | What Exists Today | What Needs to Be Done | GSoC Week |
| :--- | :--- | :--- | :--- | :---: |
| Mentor code review | Architecture | Working v0.1 prototype | Review with mentor, refactor based on feedback | Bonding |
| Services monitoring (`pgrep`) | Python | `ServicesMonitor` class with placeholder `check_service()` that always returns True | Implement `pgrep`/`psutil.process_iter()` to actively check processes | 1-2 |
| `services_status` bitmask | Python | Bitmask struct exists but is always 0 | Build real bitmask from `pgrep` results and send in message | 1-2 |
| `CCH_SVC_MASK` parameter | C++ | Not present | Add AP_Param, bitwise AND comparison in `is_healthy()` | 1-2 |
| Watchdog stall detection | C++ | `_last_watchdog_seq` is stored in `.h` but never compared in `.cpp` | Compare seq across successive packets, trigger CRITICAL if frozen | 1-2 |
| Spike filtering | Python | Not present | `collections.deque(maxlen=N)` moving average for CPU/temp metrics | 1-2 |
| Auto-reconnect | Python | Not present | Exponential backoff loop in `monitor.py` when connection drops | 1-2 |
| DataFlash logging | C++ | Not present | Define `LOG_CCH_MSG` in `LogStructure.h`, implement `Write_CCH()` | 3-4 |
| Arming check | C++ | Not present | Query `is_healthy()` in `AP_Arming.cpp`, block if DISCONNECTED/CRITICAL | 3-4 |
| Update systemd service | Deploy | File exists but references old paths (`health_and_forward.py`) | Rewrite to use `python -m companion_health` with correct paths | 5-6 |
| Update Dockerfile | Deploy | File exists but references old structure (`health_monitor.py`) | Rewrite to match new `src/companion_health` package layout | 5-6 |
| `mavlink-router` UART config | Deploy | USB config only (`usb.conf`) | Add UART config for production RPi/Jetson deployments | 5-6 |
| Installer script update | Deploy | `install.sh` exists but depends on outdated service file | Update to install correct paths and dependencies | 5-6 |
| Expand SITL autotest | Testing | Basic timeout/reconnect/critical test exists | Add tests for services_status, watchdog stall, reconnect stability | 7-8 |
| CI integration | Testing | Not present | GitHub Actions workflow to run autotests on PR | 7-8 |
| Test procedure docs | Testing | Not present | Document how to reproduce SITL and hardware tests | 7-8 |
| Hardware reverification | Testing | Pre-GSoC tests done, screenshots exist | Re-run full suite on RPi 4 and Jetson Nano with updated code | 7-8 |
| ArduPlane integration | C++ | Not present | Register `AP_CompanionHealth` in `Plane.h`, add failsafe in Plane `events.cpp` | 9-10 |
| ArduPlane SITL tests | Testing | Not present | Write `CompanionHealthFailsafe` test for ArduPlane autotest | 9-10 |
| ArduRover integration | C++ | Not present | Register in `Rover.h`, add failsafe in `failsafe.cpp` | 9-10 |
| ArduRover SITL tests | Testing | Not present | Write `CompanionHealthFailsafe` test for ArduRover autotest | 9-10 |
| MAVLink upstream PR | Protocol | Local `ardupilotmega.xml` definition only | Submit PR to `mavlink/mavlink`, address community feedback | 11-12 |
| Regenerate MAVLink headers | Protocol | Not applicable yet | After PR merge, update ArduPilot's MAVLink submodule and regenerate | 11-12 |
| Wiki documentation | Docs | Not present | Write ArduPilot wiki pages for setup, parameters, troubleshooting | 11-12 |
| `mavlink-router` wiki guide | Docs | Example config exists | Document multi-app setup with mavlink-router on wiki | 11-12 |
| Blog post | Docs | Not present | Final ArduPilot blog post summarizing the project | 11-12 |

## FC Parameters

| Parameter | Type | Default | Status | Description |
| :--- | :--- | :--- | :--- | :--- |
| `CCH_ENABLE` | int8 | 0 | Implemented | Failsafe action: 0=Disabled, 1=RTL, 2=Continue, 3=SmartRTL/RTL, 4=SmartRTL/Land, 5=Land |
| `CCH_TIMEOUT` | float | 5.0 | Implemented | Seconds without messages before failsafe triggers |
| `CCH_SVC_MASK` | uint32 | 0 | GSoC Week 1-2 | Bitmask of which services are critical (bit N = service N must be running) |

## MAVLink Message Format

`COMPANION_HEALTH` (ID 11061, 13 bytes):
- `services_status` (uint32) - bitmask of running services
- `watchdog_seq` (uint16) - incrementing counter to detect stalls
- `temperature` (int16) - decidegrees Celsius (450 = 45.0C)
- `cpu_load` (uint8) - 0-100%
- `memory_used` (uint8) - 0-100%
- `disk_used` (uint8) - 0-100%
- `gpu_load` (uint8) - 0-100% or 255 if not available
- `status_flags` (uint8) - bit 0: throttled, bit 1: overheating, bit 2: low memory, bit 3: low disk

## Quick Start

```bash
# Clone and install
git clone https://github.com/deepak61296/ap-companion-health-monitor-failsafe.git
cd ap-companion-health-monitor-failsafe
pip install -e .

# SITL testing (direct connection)
python -m companion_health --device udpout:127.0.0.1:14560 -v

# SITL testing (through mavlink-router)
./scripts/run_sitl_router.sh &
python -m companion_health --device udpout:127.0.0.1:14551 -v

# Hardware (USB)
python -m companion_health --device /dev/ttyACM0 -v

# With config file
python -m companion_health --config config/raspberry_pi.yaml -v
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run unit tests
pytest tests/unit/ -v

# Run linter
flake8 src/
```

## GSoC Timeline

| Phase | Dates | Key Deliverables |
| :--- | :--- | :--- |
| Community Bonding | May 1-24 | Code review with mentor, architecture finalization |
| Week 1-2 | May 25 - Jun 7 | Services monitoring (`pgrep`), watchdog stall detection, spike filtering |
| Week 3-4 | Jun 8-21 | DataFlash logging, arming checks |
| Week 5-6 | Jun 22 - Jul 5 | Deployment tooling (systemd, Docker, mavlink-router UART) |
| Midterm | Jul 6-10 | Midterm evaluation |
| Week 7-8 | Jul 11-19 | SITL autotest expansion, CI integration |
| Week 9-10 | Jul 20 - Aug 2 | ArduPlane and ArduRover integration |
| Week 11-12 | Aug 3-16 | MAVLink upstream PR, wiki documentation |
| Final | Aug 17-24 | Code freeze and final evaluation |

## Related

- [ArduPilot fork](https://github.com/deepak61296/ardupilot/tree/companion-computer-health-monitor) - Flight controller library
- [Video Demo](https://www.youtube.com/watch?v=s6RZwZTwf14)

## License

GPLv3
