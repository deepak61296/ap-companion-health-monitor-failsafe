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
| `CCH_ENABLE` | -1 for Warn only to start with, 1 for RTL once you trust it. Values 0 to 7 are the same set as `FS_GCS_ENABLE`: 0 Disabled, 1 RTL, 3 SmartRTL or RTL, 4 SmartRTL or Land, 5 Land, 6 Auto DO_LAND_START or RTL, 7 Brake or Land. -1 is Warn only: full reporting and logging, no failsafe action and no pre-arm block |
| `CCH_TIMEOUT` | Seconds of silence before the failsafe fires. Default 5, valid 2 to 120 |
| `CCH_SVC_MASK` | Bitmask of required companion services, 0 to disable. Bit N maps to entry N of the `services` list in the companion config. Fill in that list before setting the mask: a nonzero mask with an empty list fails over immediately |

Write Params, then reboot is not required. Because this is a fork, Mission
Planner may not show descriptions for the `CCH_` parameters. The values still
work; the descriptions ship with official firmware releases only.

## What you will see

Everything below needs `CCH_ENABLE` set to something other than 0. At the
default of 0 the subsystem is off: the flight controller still accepts the
message and prints `Companion computer connected` once, but the timeout and
watchdog checks, the status texts and the `CCH` logging all stop. Set
`CCH_ENABLE` to -1, Warn only, if you want the reporting and the logs without
giving the failsafe any authority over the vehicle.

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
  healthy companion while `CCH_ENABLE` is set to a failsafe action. Warn only
  never blocks arming
- `Companion Failsafe Cleared` on recovery

Two things worth knowing. First, `COMPANION_HEALTH` carries no target
system or component, so ArduPilot's router broadcasts it to every other
MAVLink link it has learned a route for. Mission Planner does not decode it,
but it does reach a second GCS, and anything that can inspect raw MAVLink
will see id 11061. Second, health is logged to dataflash as `CCH` records
about once a second, not only on state changes, so post-flight analysis works even with no
GCS connected.

## Bench test before flying

Arm on the bench (props off) with the companion running, stop the companion
service, and confirm the failsafe fires. On the ground the vehicle is
disarmed rather than sent to RTL, because a landed vehicle takes the disarm
path, so expect `Companion Failsafe - Disarming` and no mode change. Then
confirm arming is blocked until the service is back. The whole check takes
under a minute and exercises the exact path a real crash would take.
