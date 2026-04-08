# Companion Computer Health Monitor for ArduPilot

[![Demo Video](https://img.youtube.com/vi/s6RZwZTwf14/maxresdefault.jpg)](https://www.youtube.com/watch?v=s6RZwZTwf14)

**[Watch Demo Video](https://www.youtube.com/watch?v=s6RZwZTwf14)** - Failsafe triggers when companion stops sending health messages

---

## GSoC 2026 Project

| Item | Details |
|------|---------|
| **Organization** | ArduPilot |
| **Project** | Companion Computer Health Monitoring and Failsafe |
| **Mentor** | Jaime Machuca |
| **Size** | Medium (175 hours) |
| **Status** | Pre-GSoC Implementation Complete (44%) |

---

## Project Overview

Companion computers (Raspberry Pi, Jetson Nano, etc.) run critical software like vision processing, obstacle avoidance, and autonomous navigation. If the companion crashes or freezes, the flight controller has no way to know. The drone continues flying with dead navigation code.

**Solution:** A health monitoring system where the companion sends periodic health messages to ArduPilot. If messages stop or report critical failure, the FC triggers a configurable failsafe.

---

## Implementation Progress

### Pre-GSoC v0.1 (Complete)

- [x] **MAVLink Message** - COMPANION_HEALTH (ID 11061) defined
- [x] **FC Library** - AP_CompanionHealth with state machine
- [x] **Parameters** - CCH_ENABLE, CCH_TIMEOUT
- [x] **Timeout Failsafe** - Triggers when messages stop
- [x] **ArduCopter Integration** - Full failsafe in events.cpp
- [x] **GCS Notifications** - Status messages every 10s
- [x] **Companion Script** - health_monitor.py
- [x] **Platform Backends** - Raspberry Pi, Jetson, Generic Linux
- [x] **Docker Support** - Dockerfile + docker-compose
- [x] **SITL Testing** - Basic timeout test
- [x] **Hardware Testing** - RPi4 + CubeOrange (USB)

### GSoC Work (Planned)

- [ ] **CCH_SVC_MASK** - Required services bitmask parameter
- [ ] **Services Monitoring** - Check critical processes via pgrep
- [ ] **Watchdog Detection** - Detect frozen companion (stuck loop)
- [ ] **DataFlash Logging** - Log health metrics to flight logs
- [ ] **Arming Check** - Block arming if companion not connected
- [ ] **ArduPlane Support** - Port to fixed-wing aircraft
- [ ] **ArduRover Support** - Port to ground vehicles
- [ ] **SITL Test Suite** - Automated tests in ArduPilot CI
- [ ] **MAVLink Upstream** - Submit message to official MAVLink
- [ ] **Wiki Documentation** - Setup guides and troubleshooting

---

## GSoC 2026 Timeline

| Period | Dates | Deliverables |
|--------|-------|--------------|
| Community Bonding | May 1-24 | Review code with mentor, finalize architecture |
| **Week 1-2** | May 25 - Jun 7 | CCH_SVC_MASK, services_status check, watchdog detection |
| **Week 3-4** | Jun 8-21 | DataFlash logging, arming check |
| **Week 5-6** | Jun 22 - Jul 5 | ServicesMonitor class, spike filtering, auto-reconnect |
| **Midterm** | Jul 6-10 | ArduCopter complete, hardware tested |
| **Week 7-8** | Jul 11-19 | SITL test suite, CI integration |
| **Week 9** | Jul 20-26 | ArduPlane integration |
| **Week 10** | Jul 27 - Aug 2 | ArduRover integration |
| **Week 11** | Aug 3-9 | MAVLink PR submission |
| **Week 12** | Aug 10-16 | Wiki documentation |
| **Final** | Aug 17-24 | Final evaluation |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    COMPANION COMPUTER                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              health_monitor.py                       │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────────────────┐  │    │
│  │  │ Metrics │  │  State  │  │   Platform Backend  │  │    │
│  │  │Collector│──│ Machine │──│ (RPi/Jetson/Generic)│  │    │
│  │  └─────────┘  └─────────┘  └─────────────────────┘  │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │ COMPANION_HEALTH @ 1Hz             │
└─────────────────────────┼───────────────────────────────────┘
                          │ MAVLink (USB/UART/UDP)
┌─────────────────────────┼───────────────────────────────────┐
│                         ▼         FLIGHT CONTROLLER          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              AP_CompanionHealth                      │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────────────────┐  │    │
│  │  │ Message │  │  State  │  │  Failsafe Actions   │  │    │
│  │  │ Handler │──│ Machine │──│ (RTL/Land/SmartRTL) │  │    │
│  │  └─────────┘  └─────────┘  └─────────────────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
│                         ArduCopter / ArduPlane / ArduRover   │
└─────────────────────────────────────────────────────────────┘
```

---

## State Machine

```
DISCONNECTED ──── First message ────► HEALTHY
     ▲                                   │
     │                          cpu>80% OR mem>80%
     │                          OR temp>75C
     │                                   ▼
     │                               DEGRADED
     │                                   │
     │ Timeout                  cpu>95% OR mem>95%
     │ (CCH_TIMEOUT)            OR temp>90C OR services down
     │                                   ▼
     └─────────────────────────────  CRITICAL ──► FAILSAFE
```

---

## Quick Start

### SITL Testing

```bash
# Terminal 1: Start SITL
cd ~/ardupilot
./Tools/autotest/sim_vehicle.py -v ArduCopter --console

# In MAVProxy console:
param set CCH_ENABLE 1
param set CCH_TIMEOUT 5
```

```bash
# Terminal 2: Run companion script
cd companion-health-monitor
python3 health_monitor.py --device udpout:127.0.0.1:14560 -v
```

### Hardware (USB)

```bash
# Raspberry Pi or Jetson connected to CubeOrange via USB
python3 health_monitor.py --device /dev/ttyACM0 --baud 115200 -v
```

---

## FC Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CCH_ENABLE` | 0 | Failsafe action: 0=Disabled, 1=RTL, 2=Continue, 3=SmartRTL, 4=SmartRTL/Land, 5=Land |
| `CCH_TIMEOUT` | 5.0 | Seconds without message before failsafe triggers |

---

## COMPANION_HEALTH Message

| Field | Type | Description |
|-------|------|-------------|
| `services_status` | uint32 | Bitmask of running services |
| `watchdog_seq` | uint16 | Counter to detect frozen companion |
| `temperature` | int16 | Board temp (celsius * 10) |
| `cpu_load` | uint8 | CPU usage 0-100% |
| `memory_used` | uint8 | RAM usage 0-100% |
| `disk_used` | uint8 | Disk usage 0-100% |
| `gpu_load` | uint8 | GPU usage 0-100%, 255=N/A |
| `status_flags` | uint8 | Warning flags bitmask |

**Message ID:** 11061 | **Payload:** 13 bytes | **Rate:** 1 Hz

---

## Platform Support

| Platform | Temperature | GPU | Features |
|----------|-------------|-----|----------|
| Raspberry Pi | vcgencmd | N/A | Throttle detection |
| Jetson Nano/Xavier/Orin | sysfs thermal | tegrastats | GPU load |
| Generic Linux | /sys/class/thermal | N/A | Standard /proc |
| Docker | Host passthrough | Optional | Easy deployment |

---

## Installation

```bash
git clone https://github.com/deepak61296/ap-companion-health-monitor-failsafe.git
cd ap-companion-health-monitor-failsafe

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Build pymavlink with COMPANION_HEALTH

```bash
cd /path/to/ardupilot
MDEF=modules/mavlink/message_definitions pip install modules/mavlink/pymavlink
```

---

## Configuration

```yaml
# config.yaml
connection:
  device: "/dev/ttyACM0"
  baud: 115200

monitoring:
  rate_hz: 1.0
  disk_path: "/"

thresholds:
  temp_throttle: 80.0
  temp_overheat: 85.0
  memory_low: 90
  disk_low: 95
```

---

## Related Repositories

| Repository | Description |
|------------|-------------|
| [ArduPilot Fork](https://github.com/deepak61296/ardupilot/tree/companion-computer-health-monitor) | FC library (AP_CompanionHealth) |
| [This Repo](https://github.com/deepak61296/ap-companion-health-monitor-failsafe) | Companion script |

---

## Hardware Tested

| Companion | Flight Controller | Connection | Status |
|-----------|-------------------|------------|--------|
| Raspberry Pi 4 | CubeOrange | USB | Tested |
| Jetson Nano | CubeOrange | USB | Tested |
| SITL | - | UDP | Tested |
| Raspberry Pi 4 | CubeOrange | UART | Pending |
| Jetson Nano | CubeOrange | UART | Pending |

---

## Project Links

- **Proposal PDF:** [DeepakGSOC2026Proposal.pdf](proposal/DeepakGSOC2026Proposal.pdf)
- **Demo Video:** [YouTube](https://www.youtube.com/watch?v=s6RZwZTwf14)
- **ArduPilot Fork:** [GitHub](https://github.com/deepak61296/ardupilot/tree/companion-computer-health-monitor)

---

## License

GPLv3
