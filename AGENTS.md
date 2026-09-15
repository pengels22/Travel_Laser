# Agent Instructions

These instructions apply to the entire `Travel_Laser` workspace.

## Startup

1. Run `git status --short --branch`.
2. Read this file and `README.md`.
3. Inspect the file tree with `rg --files -g '!.git'` before making changes.
4. Preserve any user changes already present in the working tree.

## Architectural Invariants

- The project name is `ts1-laser-controller`.
- The Orange Pi backend owns GPIO and the laser USB serial device in normal Network mode.
- GRBL Network mode TCP port is fixed at `23` for deployment.
- VirtualHere is backup/service mode only.
- The GRBL proxy and VirtualHere must never own the laser USB device at the same time.
- The selected laser connection mode is persistent across reboot and failures: `network` or `virtualhere`.
- USB devices must be matched by VID, PID, serial, or descriptive fallback. Never assume `/dev/ttyUSB0` or `/dev/video0`.
- Either physical USB port may contain either camera or laser; identity determines assignment.
- The deployed hostname is `Travel-Laser`.
- The built-in `wlan0` adapter hosts the always-enabled hidden TS1 network named `TS1PE`; the TS1 connects to it as a client and should not run AP mode.
- `eth0` is the preferred uplink with metric `100`; `wlan1` is secondary uplink with metric `300`.

## Safety Rules

- Physical GPIO outputs must initialize safe before higher-level services start.
- K1 is the laser power relay.
- K2 is the hard E-stop relay and kills the laser controller completely.
- K2 is normally energized during normal operation.
- PC14 high means power switch on. PC15 high means E-stop OK, so PC15 low means E-stop active.
- K1 stays active during E-stop if the power switch is on, except fire detection may drop K1 once fire sensing is enabled.
- Any E-stop source must drop K2 immediately and mark the machine unhomed.
- E-stop sources include physical E-stop, TS1 command, web command, software E-stop, active LightBurn stream loss, laser USB loss while K2 is expected on, and future fire logic.
- Fire infrastructure must remain present, but `fire.enabled` and `fire.sensor_enabled` default to `false`.
- Software E-stop clearing requires a housing E-stop cycle: PC15 low, then PC15 high/OK.
- Camera failure never stops the laser.
- TS1 disconnect alone never stops the laser while the LightBurn control stream is healthy.
- Unexpected LightBurn TCP stream loss during an active job is fatal and must drop K2.
- Unexpected laser USB disappearance while K2 is supposed to be energized is fatal and must drop K2.
- If K2 is intentionally dropped, laser USB disappearance is expected and should not create a second USB fault.
- Never implement automatic job resume after E-stop, Pi reboot, power failure, controller reset, or unexpected laser USB loss.
- After recovery, LightBurn is responsible for reconnecting and homing.

## Development Rules

- Keep hardware adapters mockable and development-friendly on macOS/Linux.
- Do not guess Orange Pi GPIO chip/line numbers.
- Do not guess VirtualHere binary paths.
- Do not guess camera streamer commands.
- Do not guess laser VID/PID or TS1 LCD/touch pins.
- Add or update tests whenever changing safety behavior, mode ownership, GRBL proxy behavior, or command handling.
- Do not run install scripts or systemd commands on the development machine unless the user explicitly asks.
