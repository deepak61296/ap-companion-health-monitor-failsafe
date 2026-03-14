# Real-Time Companion Computer Health Monitoring & Failsafe
## GSoC 2026 Project - Full Context Document

---

## 1. PROJECT OVERVIEW

### 1.1 Problem Statement
Modern drones increasingly rely on companion computers (Jetson Nano, Raspberry Pi, etc.) for advanced autonomous capabilities like computer vision, YOLO object detection, ROS navigation, and SLAM. However, ArduPilot currently has no standardized way to:

1. Monitor companion computer health (CPU, memory, temperature)
2. Detect companion computer failures (crashes, freezes, overheating)
3. Trigger automatic failsafe actions when the companion fails

**The Risk**: If a companion computer running critical autonomous navigation crashes mid-flight, the drone continues flying with no awareness of the failure, potentially leading to flyaways or crashes.

### 1.2 Solution
Implement a standardized health reporting mechanism that:
- Sends periodic health messages from companion to flight controller
- Monitors CPU load, memory usage, temperature, disk usage, GPU load
- Tracks critical service status (ROS, YOLO, camera pipelines)
- Triggers configurable failsafe (RTL, Land, SmartRTL) on timeout
- Displays health data in standard GCS (Mission Planner, MAVProxy)

---

## 2. WHAT HAS BEEN IMPLEMENTED

### 2.1 MAVLink Message: COMPANION_HEALTH

**Message ID**: 11061 (ArduPilot dialect)
**CRC Extra**: 81

```xml
<message id="11061" name="COMPANION_HEALTH">
  <description>Health status from companion computer</description>
  <field type="uint32_t" name="services_status">Bitmask of service states</field>
  <field type="uint16_t" name="watchdog_seq">Incrementing watchdog sequence</field>
  <field type="int16_t" name="temperature">CPU temperature in decidegrees C</field>
  <field type="uint8_t" name="cpu_load">CPU load percentage (0-100)</field>
  <field type="uint8_t" name="memory_used">Memory usage percentage (0-100)</field>
  <field type="uint8_t" name="disk_used">Disk usage percentage (0-100)</field>
  <field type="uint8_t" name="gpu_load">GPU load percentage (0-100, 255=N/A)</field>
  <field type="uint8_t" name="status_flags">Status flags (throttled, overheating, etc)</field>
</message>
```

**Total payload**: 14 bytes (efficient for 1Hz transmission)

### 2.2 Flight Controller Implementation (C++)

#### New Library: `libraries/AP_CompanionHealth/`

**Files:**
```
libraries/AP_CompanionHealth/
├── AP_CompanionHealth.h           # Class definition
├── AP_CompanionHealth.cpp         # Implementation
└── AP_CompanionHealth_config.h    # Build configuration
```

**Class: AP_CompanionHealth**
```cpp
class AP_CompanionHealth {
public:
    // Called when COMPANION_HEALTH message received
    void handle_message(const mavlink_message_t &msg);

    // Called from main loop to check timeout
    void update();

    // State accessors
    bool is_healthy() const;
    bool has_ever_connected() const;
    uint32_t last_message_age_ms() const;
    int8_t get_failsafe_action() const;

    // Latest companion status
    struct CompanionStatus {
        uint32_t services_status;
        uint16_t watchdog_seq;
        int16_t temperature;      // celsius * 10
        uint8_t cpu_load;         // 0-100%
        uint8_t memory_used;      // 0-100%
        uint8_t disk_used;        // 0-100%
        uint8_t gpu_load;         // 0-100%, 255 if N/A
        uint8_t status_flags;
    };

    static const struct AP_Param::GroupInfo var_info[];

private:
    AP_Int8 _fs_enable;      // Failsafe action (0=disabled, 1-7)
    AP_Float _fs_timeout;    // Timeout in seconds

    uint32_t _last_msg_ms;
    uint32_t _last_report_ms;
    bool _healthy;
    CompanionStatus _status;
};
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `CC_ENABLE` | INT8 | 0 | Failsafe action (same values as GCS failsafe) |
| `CC_TIMEOUT` | FLOAT | 5.0 | Seconds before failsafe triggers |

**CC_ENABLE Values** (matching GCS failsafe):
- 0 = Disabled
- 1 = RTL (Return to Launch)
- 2 = Continue Mission in Auto
- 3 = SmartRTL or RTL
- 4 = SmartRTL or Land
- 5 = Land
- 6 = Auto DO_LAND_START or RTL
- 7 = Brake or Land

#### ArduCopter Integration

**Modified Files:**

1. **ArduCopter/Copter.h**
   - Added `failsafe.companion` flag to failsafe structure

2. **ArduCopter/Copter.cpp**
   - Added `failsafe_companion_check()` call in main 3Hz loop

3. **ArduCopter/events.cpp**
   - Added `failsafe_companion_check()` - checks health timeout
   - Added `failsafe_companion_on_event()` - handles failsafe trigger
   - Added `failsafe_companion_off_event()` - handles recovery

4. **ArduCopter/GCS_MAVLink_Copter.cpp**
   - Added handler for `MAVLINK_MSG_ID_COMPANION_HEALTH`

5. **ArduCopter/Parameters.h/cpp**
   - Added `companion_health` member to `ParametersG2`
   - Added `AP_SUBGROUPINFO` for parameter registration

6. **ArduCopter/wscript**
   - Added `AP_CompanionHealth` to library dependencies

#### GCS Messages Sent

| Event | Message | Severity |
|-------|---------|----------|
| First connection | `Companion computer connected` | INFO |
| Every 10 seconds | `Companion: CPU X% Mem X% Temp X.XC` | INFO |
| Failsafe trigger | `Companion Failsafe` | WARNING |
| Failsafe recovery | `Companion Failsafe Cleared` | WARNING |

### 2.3 Companion Computer Implementation (Python)

#### Main Script: `health_and_forward.py`

**Location**: `companion_script/scripts/health_and_forward.py`

**Features:**
- Collects system metrics using `psutil`
- Platform-specific temperature reading (Jetson thermal zones)
- GPU load detection for Jetson
- Sends COMPANION_HEALTH at configurable rate (default 1Hz)
- Forwards telemetry bidirectionally (FC ↔ GCS over UDP)
- Raw MAVLink2 packet construction (for compatibility)

**Usage:**
```bash
python3 health_and_forward.py \
    --device /dev/ttyACM0 \
    --dest udpout:192.168.1.100:14550 \
    --rate 1.0
```

**Metrics Collected:**
```python
{
    'cpu_load': psutil.cpu_percent(),           # 0-100%
    'memory_used': psutil.virtual_memory().percent,  # 0-100%
    'disk_used': psutil.disk_usage('/').percent,     # 0-100%
    'temperature': read_thermal_zone(),          # decidegrees C
    'gpu_load': read_jetson_gpu(),               # 0-100% or 0
    'status_flags': 1                            # healthy
}
```

### 2.4 Testing Completed

| Test | Platform | Result |
|------|----------|--------|
| SITL simulation | Linux PC | ✅ Pass |
| USB connection | CubeOrange + Jetson Nano | ✅ Pass |
| Message reception | FC receives COMPANION_HEALTH | ✅ Pass |
| GCS display | Messages appear in MAVProxy | ✅ Pass |
| Failsafe trigger | Script stop → "Companion Failsafe" after 5s | ✅ Pass |
| Failsafe recovery | Script restart → "Companion Failsafe Cleared" | ✅ Pass |
| Parameter visibility | CC_ENABLE, CC_TIMEOUT in GCS | ✅ Pass |
| Telemetry forwarding | Bidirectional FC ↔ GCS | ✅ Pass |

---

## 3. ARCHITECTURE

### 3.1 System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMPANION COMPUTER (Jetson/RPi)                      │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     health_and_forward.py                             │   │
│  │                                                                       │   │
│  │   ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐  │   │
│  │   │ Collect     │    │ Build       │    │ Forward Telemetry       │  │   │
│  │   │ Metrics     │───►│ COMPANION_  │    │ FC ←──────────────► GCS │  │   │
│  │   │ (psutil)    │    │ HEALTH msg  │    │                         │  │   │
│  │   └─────────────┘    └──────┬──────┘    └─────────────────────────┘  │   │
│  │                             │                                         │   │
│  └─────────────────────────────┼─────────────────────────────────────────┘   │
│                                │                                              │
└────────────────────────────────┼──────────────────────────────────────────────┘
                                 │ USB/UART (/dev/ttyACM0)
                                 │ 1 Hz
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLIGHT CONTROLLER (CubeOrange)                       │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      GCS_MAVLink_Copter.cpp                           │   │
│  │   case MAVLINK_MSG_ID_COMPANION_HEALTH:                               │   │
│  │       copter.g2.companion_health.handle_message(msg);                 │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│                                      ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      AP_CompanionHealth                               │   │
│  │                                                                       │   │
│  │   handle_message()          update()              Parameters          │   │
│  │   ├─ Store metrics          ├─ Check timeout      ├─ CC_ENABLE        │   │
│  │   ├─ Update timestamp       ├─ Set healthy flag   └─ CC_TIMEOUT       │   │
│  │   └─ First connect msg      └─ Send GCS report                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│                                      ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      Failsafe System (events.cpp)                     │   │
│  │                                                                       │   │
│  │   failsafe_companion_check()  ──► is_healthy()? ──► failsafe action   │   │
│  │                                                                       │   │
│  │   Actions: RTL / Land / SmartRTL / Brake / Continue Mission           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 │ Telemetry (UDP)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GROUND CONTROL STATION                               │
│                     (Mission Planner / MAVProxy / QGC)                       │
│                                                                              │
│   Status Messages:                          Parameters:                      │
│   • "Companion computer connected"          • CC_ENABLE = 1 (RTL)           │
│   • "Companion: CPU 7% Mem 29% Temp 34.5C"  • CC_TIMEOUT = 5.0 (seconds)    │
│   • "Companion Failsafe"                                                     │
│   • "Companion Failsafe Cleared"                                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow

```
COMPANION                           FC                              GCS
    │                               │                                │
    │   COMPANION_HEALTH (1Hz)      │                                │
    ├──────────────────────────────►│                                │
    │                               │                                │
    │                               │   "Companion connected"        │
    │                               ├───────────────────────────────►│
    │                               │                                │
    │                               │   Status report (every 10s)    │
    │                               ├───────────────────────────────►│
    │                               │   "Companion: CPU 7%..."       │
    │                               │                                │
    │      (script crashes)         │                                │
    X                               │                                │
    │                               │                                │
    │      (CC_TIMEOUT expires)     │                                │
    │                               │   "Companion Failsafe"         │
    │                               ├───────────────────────────────►│
    │                               │                                │
    │                               │   (triggers RTL/Land/etc)      │
    │                               │                                │
    │      (script restarts)        │                                │
    ├──────────────────────────────►│                                │
    │   COMPANION_HEALTH            │   "Companion Failsafe Cleared" │
    │                               ├───────────────────────────────►│
    │                               │                                │
```

### 3.3 File Structure

```
ardupilot/
├── libraries/
│   └── AP_CompanionHealth/
│       ├── AP_CompanionHealth.h           # Class definition
│       ├── AP_CompanionHealth.cpp         # Implementation (133 lines)
│       └── AP_CompanionHealth_config.h    # Build config (22 lines)
│
├── ArduCopter/
│   ├── events.cpp                         # +92 lines (failsafe functions)
│   ├── Copter.cpp                         # +5 lines (check call)
│   ├── Copter.h                           # +9 lines (failsafe flag)
│   ├── Parameters.cpp                     # +6 lines (SUBGROUPINFO)
│   ├── Parameters.h                       # +6 lines (member)
│   ├── GCS_MAVLink_Copter.cpp             # +6 lines (message handler)
│   └── wscript                            # +1 line (library)
│
├── modules/mavlink/
│   └── message_definitions/v1.0/
│       └── ardupilotmega.xml              # COMPANION_HEALTH message
│
└── companion_script/
    ├── scripts/
    │   ├── health_and_forward.py          # Main script (183 lines)
    │   ├── health_monitor.py              # Health-only script
    │   └── telem_forward.py               # Telemetry-only script
    ├── README.md                          # Documentation
    └── requirements.txt                   # Python dependencies
```

---

## 4. WHAT REMAINS TO BE DONE

### 4.1 High Priority

| Task | Description | Estimated Hours |
|------|-------------|-----------------|
| **Services Monitoring** | Monitor systemd services (ROS, YOLO, camera) via `services_status` bitmask | 15 |
| **Hardware Watchdog** | Integrate with `/dev/watchdog` for auto-reboot on companion freeze | 10 |
| **DataFlash Logging** | Log COMPANION_HEALTH to FC's onboard SD card | 10 |
| **Raspberry Pi Testing** | Test and optimize for RPi 4/5 | 8 |

### 4.2 Medium Priority

| Task | Description | Estimated Hours |
|------|-------------|-----------------|
| **ArduPlane Support** | Port failsafe to ArduPlane | 8 |
| **ArduRover Support** | Port failsafe to ArduRover | 6 |
| **ArduSub Support** | Port failsafe to ArduSub | 6 |
| **SITL Automated Tests** | Python tests with simulated companion | 12 |
| **MAVLink Upstream** | Submit COMPANION_HEALTH to MAVLink common.xml | 8 |

### 4.3 Low Priority / Polish

| Task | Description | Estimated Hours |
|------|-------------|-----------------|
| **Systemd Service** | Auto-start on boot | 4 |
| **Docker Container** | Containerized deployment | 6 |
| **Documentation** | User guide, developer docs | 10 |
| **Video Demo** | Demonstration video for GSoC | 4 |

---

## 5. IMPLEMENTATION PLAN

### Phase 1: Core System (COMPLETED - 40 hours)
- [x] MAVLink message design (COMPANION_HEALTH)
- [x] FC-side library (AP_CompanionHealth)
- [x] Failsafe integration (events.cpp)
- [x] Parameters (CC_ENABLE, CC_TIMEOUT)
- [x] Python companion script
- [x] Hardware testing (CubeOrange + Jetson Nano)
- [x] GCS status messages

### Phase 2: Services & Watchdog (45 hours)
- [ ] Define service status bitmask
- [ ] Implement systemd service monitoring
- [ ] Add service status to COMPANION_HEALTH
- [ ] Integrate hardware watchdog (/dev/watchdog)
- [ ] Test service failure detection
- [ ] Test watchdog recovery

### Phase 3: Logging & Multi-Vehicle (35 hours)
- [ ] Add DataFlash logging (LOG_COMPANION_HEALTH)
- [ ] Create log analysis tools
- [ ] Port to ArduPlane
- [ ] Port to ArduRover
- [ ] Port to ArduSub

### Phase 4: Testing & Documentation (35 hours)
- [ ] SITL automated tests
- [ ] Crash simulation tests (CPU stress, memory stress, kill script)
- [ ] Raspberry Pi testing
- [ ] User documentation
- [ ] Developer documentation
- [ ] Video demonstration

### Phase 5: Upstream & Polish (20 hours)
- [ ] Submit MAVLink message to official repo
- [ ] Code review preparation
- [ ] PR submission to ArduPilot
- [ ] Address review feedback
- [ ] Final cleanup

**Total Estimated: 175 hours** (matches GSoC project size)

---

## 6. HOW TO TEST

### 6.1 Hardware Setup

**Requirements:**
- Flight Controller: CubeOrange (or any ArduPilot-supported FC)
- Companion: Jetson Nano or Raspberry Pi 4
- Connection: USB cable (FC to Companion)
- GCS: Laptop with MAVProxy or Mission Planner

**Wiring:**
```
CubeOrange USB ──────── Jetson USB
                        └── /dev/ttyACM0
```

### 6.2 Running the System

**On Companion (Jetson/RPi):**
```bash
python3 health_and_forward.py \
    --device /dev/ttyACM0 \
    --dest udpout:<GCS_IP>:14550 \
    --rate 1.0
```

**On GCS (Laptop):**
```bash
mavproxy.py --master=udpin:0.0.0.0:14550
```

### 6.3 Test Cases

| Test | Command | Expected Result |
|------|---------|-----------------|
| Connection | Start script | "Companion computer connected" in GCS |
| Health data | Wait 10s | "Companion: CPU X% Mem X% Temp X.XC" |
| Parameters | `param show CC*` | CC_ENABLE=1, CC_TIMEOUT=5 |
| Failsafe trigger | `Ctrl+C` on companion, wait 5s | "Companion Failsafe" in GCS |
| Failsafe recovery | Restart script | "Companion Failsafe Cleared" |

### 6.4 Simulating Crashes

```bash
# Method 1: Kill script
pkill -9 -f health_and_forward

# Method 2: CPU stress
stress --cpu 4 --timeout 60

# Method 3: Memory stress
stress --vm 2 --vm-bytes 512M --timeout 30

# Method 4: Kernel panic (WARNING: reboots system)
echo c > /proc/sysrq-trigger
```

---

## 7. PARAMETERS REFERENCE

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| CC_ENABLE | INT8 | 0-7 | 0 | Failsafe action when companion times out |
| CC_TIMEOUT | FLOAT | 1-60 | 5.0 | Seconds before failsafe triggers |

### CC_ENABLE Values

| Value | Action | Description |
|-------|--------|-------------|
| 0 | Disabled | No failsafe action |
| 1 | RTL | Return to Launch |
| 2 | Continue Mission | Continue Auto mission (requires GCS) |
| 3 | SmartRTL or RTL | SmartRTL if available, else RTL |
| 4 | SmartRTL or Land | SmartRTL if available, else Land |
| 5 | Land | Land immediately |
| 6 | Auto DO_LAND_START or RTL | Execute DO_LAND_START if defined |
| 7 | Brake or Land | Brake if available, else Land |

---

## 8. FUTURE ENHANCEMENTS

### 8.1 Services Monitoring

**Proposed `services_status` Bitmask:**
```
Bit 0: ROS master running
Bit 1: Camera pipeline running
Bit 2: YOLO/CV service running
Bit 3: MAVROS running
Bit 4: Obstacle avoidance running
Bit 5: SLAM/mapping running
Bit 6-31: Reserved for user-defined services
```

### 8.2 Status Flags

**Proposed `status_flags` Bitmask:**
```
Bit 0: System throttled (undervoltage/thermal)
Bit 1: Overheating warning
Bit 2: Low memory warning
Bit 3: Low disk space warning
Bit 4: Watchdog active
Bit 5-7: Reserved
```

### 8.3 DataFlash Log Format

```
LOG_COMPANION_HEALTH:
  TimeUS: uint64_t
  CPU: uint8_t
  Mem: uint8_t
  Temp: int16_t
  Disk: uint8_t
  GPU: uint8_t
  Svc: uint32_t
  Flags: uint8_t
  WDSeq: uint16_t
```

---

## 9. RELATED WORK

### 9.1 Existing ArduPilot Features
- **GCS Failsafe**: Similar timeout-based failsafe for ground station
- **Battery Failsafe**: Triggers on low voltage/capacity
- **Radio Failsafe**: Triggers on RC signal loss
- **EKF Failsafe**: Triggers on navigation failure

### 9.2 External References
- [ArduPilot Companion Computers](https://ardupilot.org/dev/docs/companion-computers.html)
- [MAVLink Protocol](https://mavlink.io/en/)
- [NVIDIA Jetson Watchdog](https://forums.developer.nvidia.com/t/enable-and-setup-watchdog-for-jetson-nano/167539)
- [Raspberry Pi Watchdog](https://gist.github.com/PSJoshi/803a0419e568cc95c6bec24ebb0d44dc)

---

## 10. COMMIT HISTORY

```
12df741 AP_CompanionHealth: add periodic GCS status report
d471dbd AP_CompanionHealth: fix param names and add connection message
5b3c280 add companion computer health monitoring and failsafe
d3f0b8b companion_script: add heartbeat for MAVLink handshake
b95ea9e testing with jetson
62ee35d works in sitl
```

---

## 11. CONTACT & RESOURCES

- **Branch**: `companion-computer-health-monitor`
- **GSoC Idea**: [Real-Time Companion Computer Health Monitoring & Failsafe](https://ardupilot.org/dev/docs/gsoc-ideas-list.html)
- **Mentor**: Jaime Machuca
- **Discord**: #gsoc channel on ArduPilot Discord

---

*Document generated for GSoC 2026 proposal preparation*
