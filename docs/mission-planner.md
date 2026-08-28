# Setting up from Mission Planner

The failsafe is configured entirely through standard parameters, so any GCS
works: Mission Planner, QGroundControl or MAVProxy. This page uses Mission
Planner names.

## Prerequisites

The flight controller must run firmware built from the `companion-health`
branch of the [ArduPilot fork](https://github.com/deepak61296/ardupilot/tree/companion-health).
The `CCH_` parameters and the failsafe do not exist in upstream ArduPilot yet.

## Parameters

Connect, then open Config, Full Parameter List and search for `CCH`.

| Parameter | Set to |
| :--- | :--- |
| `CCH_ENABLE` | 1 for RTL. Same value set as `FS_GCS_ENABLE`: 0 Disabled, 1 RTL, 3 SmartRTL or RTL, 4 SmartRTL or Land, 5 Land, 6 Auto DO_LAND_START or RTL, 7 Brake or Land |
| `CCH_TIMEOUT` | Seconds of silence before the failsafe fires. Default 5, valid 2 to 120 |
| `CCH_SVC_MASK` | Bitmask of required companion services, 0 to disable. Bit N maps to entry N of the `services` list in the companion config |

Write Params, then reboot is not required. Because this is a fork, Mission
Planner may not show descriptions for the `CCH_` parameters. The values still
work; the descriptions ship with official firmware releases only.

## What you will see

Mission Planner does not decode the raw `COMPANION_HEALTH` message. It does
not need to. Everything relevant arrives as status text, which shows in the
HUD and under Data, Messages:

- `Companion computer connected` when the monitor first talks
- `Companion [HEALTHY]: CPU 3% Mem 12% Temp 45.1C` on every state change,
  never as a periodic spam
- `Companion [DEGRADED]: ...` as a warning while the vehicle keeps flying
- `Companion Failsafe` when the failsafe fires, plus the mode change to your
  configured action
- `PreArm: Companion Computer is not healthy` if you try to arm without a
  healthy companion while `CCH_ENABLE` is on
- `Companion Failsafe Cleared` on recovery

Two things worth knowing. First, ArduPilot does not forward the raw
`COMPANION_HEALTH` message to other GCS links, so a message inspector will
not show id 11061 traffic; the status texts are the interface. Second, state
changes are also logged to dataflash as `CCH` records, so post-flight
analysis works even with no GCS connected.

## Bench test before flying

Arm on the bench (props off) with the companion running, stop the companion
service, and confirm the failsafe fires and the vehicle would RTL. Then
confirm arming is blocked until the service is back. The whole check takes
under a minute and exercises the exact path a real crash would take.
