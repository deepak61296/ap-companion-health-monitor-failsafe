# Companion Computer Health Monitor

Monitors the health of companion computers (Raspberry Pi, Jetson, generic Linux) and reports metrics to ArduPilot over MAVLink. The flight controller uses these reports to trigger failsafe actions (RTL, Land, SmartRTL) if the companion stops responding, freezes, or enters a critical state.

This started as a prototype for a GSoC 2026 proposal and is now being completed independently as a contribution to the ArduPilot community. The flight-controller side lives in the [ArduPilot fork](https://github.com/deepak61296/ardupilot/tree/companion-computer-health-monitor) (`AP_CompanionHealth` library); this repo is the reference companion-side implementation - any MAVLink-capable software can replace it.

## Demo

**[Watch Demo Video](https://www.youtube.com/watch?v=s6RZwZTwf14)** - ArduCopter failsafe triggering when the companion health script stops sending messages.

## How it works

The companion sends a 13-byte `COMPANION_HEALTH` message at 1 Hz. The FC tracks a state machine (`DISCONNECTED` / `HEALTHY` / `DEGRADED` / `CRITICAL`) and triggers a configurable failsafe on:

- **Timeout** - no message for `CCH_TIMEOUT` seconds
- **Watchdog stall** - messages still arriving but `watchdog_seq` frozen (companion stuck in a loop)
- **Service loss** - a process required by the `CCH_SVC_MASK` bitmask stopped running
- **Critical metrics** - overheating flag, or CPU/memory/temperature past critical thresholds

`DEGRADED` (warning thresholds) only logs and warns; it never triggers a failsafe. An optional pre-arm check blocks arming while the companion is unhealthy.

## Features

- Platform backends with auto-detection: generic Linux (psutil), Raspberry Pi (`vcgencmd` temperature and throttle detection), Jetson (sysfs GPU load and thermal zones)
- Service monitoring via psutil with `pgrep` fallback, packed into the `services_status` bitmask
- Spike filtering (moving average) on CPU and temperature to avoid false failsafes
- Auto-reconnect with exponential backoff
- Works with stock pymavlink (raw-packet fallback, no rebuilt dialect needed on the companion)
- YAML config with CLI overrides, systemd service + installer, Dockerfile/compose, mavlink-router configs
- FC side: `CCH` DataFlash logging at 1 Hz, GCS status text, pre-arm check, 8-subtest SITL autotest (`CompanionHealthFailsafe`)

## Verification status

Honest state of testing evidence, not aspirations:

| Setup | Status |
| :--- | :--- |
| SITL (autotest, 8 subtests) | Passing as of May 2026; FC branch is being rebased onto current master, will be re-run after |
| CubeOrange + Raspberry Pi 4 (USB) | End-to-end verified May 2026 (telemetry, failsafe triggers, systemd) |
| CubeOrange + Raspberry Pi 4 (UART) | Not yet tested |
| CubeOrange + Jetson Nano | Pre-GSoC prototype only - reverification with current code pending |
| Docker deployment | SITL only, not yet on hardware |
| mavlink-router multi-app | Verified on SITL and RPi 4, May 2026 |

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
      base.py            # Abstract MetricsBackend + spike filtering
      generic.py         # Generic Linux backend (psutil)
      raspberry_pi.py    # RPi backend (vcgencmd for throttle/temp)
      jetson.py          # Jetson backend (sysfs GPU load, thermal zones)
    services/
      monitor.py         # ServicesMonitor (psutil/pgrep process detection)
  config/                # Example configs (sitl, raspberry_pi, jetson)
  deploy/
    mavlink-router/      # mavlink-router configs
    companion-health.service  # systemd unit
    install.sh           # Installer (pip install + service setup)
    Dockerfile, docker-compose.yml
  scripts/               # SITL helpers, pymavlink wheel builder
  tests/
    unit/                # Backends, config, state, services
    integration/         # SITL and hardware tests
```

FC-side files (branch `companion-computer-health-monitor` of the ArduPilot fork):

```
libraries/AP_CompanionHealth/   # Library: message handling, state machine, params, logging
ArduCopter/events.cpp           # failsafe_companion_check/on_event/off_event (3Hz)
libraries/AP_Arming/            # Pre-arm health check
Tools/autotest/arducopter.py    # CompanionHealthFailsafe autotest
modules/mavlink                 # Submodule pinned to the companion-health branch of
                                # deepak61296/mavlink (COMPANION_HEALTH message definition)
```

## FC Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `CCH_ENABLE` | int8 | 0 | Failsafe action: 0=Disabled, 1=RTL, 2=Continue Mission in Auto, 3=SmartRTL or RTL, 4=SmartRTL or Land, 5=Land, 6=Auto DO_LAND_START or RTL, 7=Brake or Land (same values as GCS failsafe) |
| `CCH_TIMEOUT` | float | 5.0 | Seconds without messages before failsafe triggers |
| `CCH_SVC_MASK` | int32 | 0 | Bitmask of required services (bit N = service N from the config list must be running; 0 = ignore) |

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

The flight controller must run the `companion-computer-health-monitor` branch of the ArduPilot fork linked below (the custom message and failsafe are not in upstream ArduPilot yet).

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run unit tests
pytest tests/unit/ -v

# Run linter
flake8 src/
```

## Roadmap

1. Rebase the FC branch onto current ArduPilot master and re-run the full autotest
2. Hardware test matrix: RPi 4 (USB + UART) and Jetson Nano reverification, soak testing
3. Upstream the `COMPANION_HEALTH` message to ArduPilot/mavlink
4. Submit the `AP_CompanionHealth` + Copter failsafe PR to ArduPilot
5. ArduPilot wiki documentation; ArduPlane and ArduRover ports as follow-ups

## Related

- [ArduPilot fork](https://github.com/deepak61296/ardupilot/tree/companion-computer-health-monitor) - Flight controller library and autotest
- [MAVLink fork](https://github.com/deepak61296/mavlink/tree/companion-health) - COMPANION_HEALTH message definition
- [Video Demo](https://www.youtube.com/watch?v=s6RZwZTwf14)

## License

GPLv3
