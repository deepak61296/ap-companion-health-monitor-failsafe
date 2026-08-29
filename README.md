# Companion Computer Health Monitor

Companion computers do flight-critical work on a lot of ArduPilot vehicles: precision landing, obstacle avoidance, visual navigation. When that computer crashes, hangs or overheats mid-flight, ArduPilot currently has no idea. This project closes that gap.

A small daemon on the companion sends a 1 Hz health message to the flight controller. On the FC side, the `AP_CompanionHealth` library tracks it and runs a real failsafe when the companion goes silent or reports a critical condition. This repo is the companion half, written as a reference implementation. Any MAVLink-capable software can send the same message and get the same failsafe.

The flight controller side lives in the [ArduPilot fork](https://github.com/deepak61296/ardupilot/tree/companion-health), branch `companion-health`.

## Demo

[Watch the demo video](https://www.youtube.com/watch?v=GweYXp5yXuU): SITL on a laptop, the monitor on a real Raspberry Pi 4 over WiFi. The Pi is stressed to 90 percent CPU before takeoff (warning only, still armable and still flies), then the companion service is killed in flight and the copter fails over to RTL on its own. Beat-by-beat screenshots in [docs/demo.md](docs/demo.md).

## Architecture

```
companion computer                        flight controller (ArduCopter)
------------------                       ------------------------------
psutil / vcgencmd / sysfs
      |
platform backend
(metrics + spike filtering)
      |
state machine (local logging
only, not transmitted)
      |
COMPANION_HEALTH sender, 1 Hz  ------->  AP_CompanionHealth library
(serial, UDP, TCP,                       DISCONNECTED / HEALTHY /
 or via mavlink-router)                  DEGRADED / CRITICAL
                                               |
                                         failsafe action (GCS failsafe
                                         pattern), pre-arm check,
                                         status text on state change,
                                         CCH dataflash logging
```

Four things trigger the failsafe:

1. Timeout. No message for `CCH_TIMEOUT` seconds.
2. Watchdog stall. Messages keep arriving but `watchdog_seq` stops incrementing. This catches any sender whose transmit path outlives its main loop. The reference monitor here increments the counter in the same loop that transmits, so for it a hang shows up as a plain timeout; the watchdog trigger exists for multi-threaded companion software.
3. Required service loss. `CCH_SVC_MASK` marks processes that must be present on the companion. This detects a process that has exited or crashed. A process that is still running but internally hung keeps its bit set, so it is not detected.
4. Critical state. Overheating flag set, or load and temperature past the critical thresholds.

DEGRADED is a warning only and never triggers a failsafe. Dropouts shorter than the timeout are invisible by design, so restarting the companion service does not shake the vehicle.

`CCH_ENABLE=-1` is Warn only, and it is the recommended way to start. The state machine, the status texts and the `CCH` dataflash records all run exactly as they do with a failsafe configured, but an unhealthy companion never takes the vehicle and never blocks arming. Fly it that way for a few flights, read the logs, then pick a real action once you trust what you are seeing. At `CCH_ENABLE=0` the FC still accepts the message and prints the connect text, but nothing else runs: no timeout detection, no status texts, no logging.

Thresholds exist on both sides. The companion sets `status_flags` from its own config (overheat, low memory, low disk, throttling). The flight controller classifies the raw fields independently: DEGRADED past 80 percent load or 75 C, CRITICAL past 95 percent or 90 C.

Platform backends are auto-detected at startup. Raspberry Pi (`vcgencmd` for temperature and throttle state) and generic Linux (psutil, also what runs inside Docker) are fully supported; generic works on any Linux companion, so nothing needs a dedicated backend to run. The Jetson backend (sysfs thermal zones and GPU load) exists but is not complete yet: no unit tests of its own, and its last on-device run predates the current code. CPU and temperature pass through a five sample moving average, so a single spiky reading is much less likely to trip a threshold. Memory and disk are reported unaveraged. The MAVLink layer encodes the message as a raw packet, so the companion runs on stock pymavlink with no rebuilt dialect.

## The message

`COMPANION_HEALTH`, id 11061, 13 byte payload, sent at 1 Hz:

| Field | Type | Meaning |
| :--- | :--- | :--- |
| `services_status` | uint32 | bitmask of running services |
| `watchdog_seq` | uint16 | increments every message, detects stalls |
| `temperature` | int16 | centidegrees Celsius (4500 = 45.0 C), INT16_MAX if no sensor |
| `cpu_load` | uint8 | 0-100 percent |
| `memory_used` | uint8 | 0-100 percent |
| `disk_used` | uint8 | 0-100 percent |
| `gpu_load` | uint8 | 0-100 percent, 255 if not available |
| `status_flags` | uint8 | bit 0 throttled, bit 1 overheating, bit 2 low memory, bit 3 low disk |

## FC parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `CCH_ENABLE` | int8 | 0 | Failsafe action, same value set as `FS_GCS_ENABLE`: 0 Disabled, 1 RTL, 3 SmartRTL or RTL, 4 SmartRTL or Land, 5 Land, 6 Auto DO_LAND_START or RTL, 7 Brake or Land. -1 is Warn only, following the same convention as Q_TRANS_FAIL_ACT |
| `CCH_TIMEOUT` | float | 5.0 | Seconds without a message before the failsafe fires |
| `CCH_SVC_MASK` | int32 | 0 | Bitmask of required services. Bit N maps to entry N of the `services` list in the companion config. 0 disables the check. Populate the `services` list first: a nonzero mask against an empty list reads as every required service missing and fails over immediately |

## Quick start

```bash
git clone https://github.com/deepak61296/ap-companion-health-monitor-failsafe.git
cd ap-companion-health-monitor-failsafe
pip install -e .

# SITL, direct connection
python -m companion_health --device udpout:127.0.0.1:14560 -v

# SITL through mavlink-router
./scripts/run_sitl_router.sh &
python -m companion_health --device udpout:127.0.0.1:14551 -v

# Hardware over USB
python -m companion_health --device /dev/ttyACM0 -v

# With a config file
python -m companion_health --config config/raspberry_pi.yaml -v
```

The flight controller must run the `companion-health` branch of the ArduPilot fork linked above. The message and the failsafe are not in upstream ArduPilot yet.

## Install as a service

```bash
sudo ./deploy/install.sh
```

That installs the package, writes a systemd unit and starts it against `/dev/ttyACM0`. To use a different device, pass it as an argument:

```bash
sudo ./deploy/install.sh /dev/serial/by-id/usb-Hex_ProfiCNC_CubeOrange_XXXX-if00
```

Prefer the `/dev/serial/by-id/` path over `/dev/ttyACM0`. Numbered device names depend on USB enumeration order, and another device plugged in at boot can steal the number. The same advice applies to `deploy/docker-compose.yml` and the mavlink-router configs, which default to `/dev/ttyACM0` and need editing for your setup. Re-running `install.sh` rewrites the unit file, so pass the device argument every time.

## Configuration

YAML config with CLI overrides. Example configs for SITL, Raspberry Pi and Jetson are in `config/`. The `services` list names the processes to monitor; its order defines the `CCH_SVC_MASK` bit positions, so keep the list stable once you set the mask on the FC.

## Documentation

- [docs/demo.md](docs/demo.md): what the demo shows, with screenshots, and how to reproduce it
- [docs/mission-planner.md](docs/mission-planner.md): configuring the failsafe from Mission Planner and what a GCS shows
- [docs/testing.md](docs/testing.md): full verification status and how to rerun every test

## Future work

Liveness checking. The current service check confirms that a named process exists, which does not detect a process that is running but internally stalled. The planned approach is an optional heartbeat file per service, written by the monitored program after each work iteration, with the monitor clearing the bit when the file goes stale. This follows the principle the flight controller already applies to the companion link: a periodic signal from the party whose health is in question is what proves health, not its presence in a process table. It needs no flight controller or MAVLink change.

## Verification status

Tested on real hardware, not just SITL: the autotest suite (12 subtests) passes on ArduPilot master as of 14 August 2026, the unit suite runs in CI, and the failsafe chain is verified end to end on a CubeOrange with a Raspberry Pi 4 as a systemd service, including a 1-hour stress soak and dataflash logging. UART transport and Jetson reverification are still open. The honest table with dates lives in [docs/testing.md](docs/testing.md).

## Project structure

```
companion-health-monitor/
  src/companion_health/
    monitor.py           # main 1 Hz telemetry loop
    state.py             # state machine
    mavlink.py           # raw COMPANION_HEALTH packet encoding
    config.py            # YAML config loader
    cli.py               # command line parsing
    backends/            # base + generic, raspberry_pi, jetson
    services/            # process monitoring for services_status
  config/                # example configs (sitl, raspberry_pi, jetson)
  deploy/                # systemd unit, install.sh, Docker, mavlink-router configs
  scripts/               # SITL helpers
  tests/                 # unit + integration
```

FC side, on branch `companion-health` of the ArduPilot fork:

```
libraries/AP_CompanionHealth/   # message handling, state machine, params, logging
ArduCopter/events.cpp           # failsafe on/off events, 3 Hz check
libraries/AP_Arming/            # pre-arm health check
Tools/autotest/arducopter.py    # CompanionHealthFailsafe autotest
modules/mavlink                 # submodule with the COMPANION_HEALTH definition
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/unit/ -v
flake8 src tests
```

## Roadmap

1. Upstream the `COMPANION_HEALTH` message to ArduPilot/mavlink
2. Submit the `AP_CompanionHealth` + Copter failsafe PR to ArduPilot
3. UART (GPIO serial) between companion and flight controller
4. Jetson reverification on current code
5. ArduPilot wiki documentation; Plane and Rover ports as follow-ups
6. Local read-only status endpoint (JSON) on the companion, for bench debugging and fleet tooling

## Related

- [ArduPilot fork](https://github.com/deepak61296/ardupilot/tree/companion-health), flight controller library and autotest
- [MAVLink fork](https://github.com/deepak61296/mavlink/tree/companion-health-master), COMPANION_HEALTH message definition
- [Demo video](https://www.youtube.com/watch?v=GweYXp5yXuU)

## License

GPLv3
