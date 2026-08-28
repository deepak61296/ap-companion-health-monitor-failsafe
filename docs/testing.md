# Testing and verification

Honest state of the evidence as of August 2026, and how to reproduce each
piece yourself.

## Verification status

| Setup | Status |
| :--- | :--- |
| SITL (autotest, 11 subtests) | Passing on current ArduPilot master, August 2026, with `allow_skips=False` |
| Unit suite | 66 passed / 2 skipped; CI on Python 3.10-3.12, also verified on 3.13 |
| SITL flight + real RPi 4 over WiFi | Full demo arc verified August 2026: healthy, degraded under real load with no failsafe, timeout failsafe to RTL mid flight, pre-arm gate, recovery |
| CubeOrange + Raspberry Pi 4 (USB) | End-to-end verified August 2026: pre-arm gate, failsafe at exactly `CCH_TIMEOUT`, recovery, all as a real systemd service |
| 1-hour stress soak on RPi 4 | Passed August 2026: memory flat, zero restarts, no spurious failsafes under staged CPU and memory load |
| mavlink-router multi-app | Verified on real hardware August 2026: companion, a network GCS and a TCP client sharing one flight controller link |
| Dataflash `CCH` logging | Verified in a real `.BIN` pulled off a CubeOrange, August 2026 |
| CubeOrange + Raspberry Pi 4 (UART) | Not yet tested, planned. The message layer is transport-agnostic, but the GPIO serial path has not been exercised |
| CubeOrange + Jetson | On hold. The backend and its unit tests exist, but the last on-device run predates the current code. Reverification will come later |
| Docker deployment | Optional path, SITL only, not yet on hardware |

## Reproducing the SITL autotest

The FC-side behavior is covered by `CompanionHealthFailsafe` in the ArduPilot
autotest suite, 11 subtests: message handling, all four failsafe triggers,
the pre-arm gate, recovery, a reconnect storm and timeout edge cases.

```bash
cd ardupilot
./Tools/autotest/autotest.py build.ArduCopter test.Copter.CompanionHealthFailsafe
```

## Reproducing the unit suite

```bash
cd companion-health-monitor
pip install -e ".[dev]"
pytest tests/ -v
flake8 src tests
```

## Manual SITL check

The five minute version, two machines or one:

1. Build and start SITL from the `companion-health` branch:
   `./Tools/autotest/sim_vehicle.py -v ArduCopter --console --map`
2. Set `CCH_ENABLE` to 1 and `CCH_TIMEOUT` to 5.
3. Start the monitor: `python -m companion_health --device tcp:IP:5762 -v`
   (use `udpout:127.0.0.1:14560` for a same-machine UDP link instead).
4. Watch for `Companion [HEALTHY]` in the console.
5. Stop the monitor. Five seconds later the console prints
   `Companion Failsafe`, and an armed copter switches to your configured
   action. Arming is now blocked.
6. Start the monitor again. `Companion Failsafe Cleared`, arming works.

A full walkthrough with a flight in the loop is in [demo.md](demo.md).

## Hardware bench check

Same sequence as the manual SITL check, with the monitor installed as a
systemd service (`deploy/install.sh`) and the flight controller on USB or
UART. This was verified on a CubeOrange and a Raspberry Pi 4, including a
14-cell behavior matrix (every state transition and trigger) and the 1-hour
soak. The detailed evidence travels with the ArduPilot pull request.
