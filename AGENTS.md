# Agent Instructions

These instructions apply to the entire `Travel_Laser` workspace.

## Startup

1. Run `git status --short --branch`.
2. Read this file and `README.md`.
3. Inspect the file tree with `rg --files -g '!.git'` before making changes.
4. Preserve any user changes already present in the working tree.

## Architectural Invariants

- The project name is `travel-laser-controller`.
- SCULPFUN TS1 runtime support is abandoned. Do not add active code that flashes, emulates, talks to, or depends on the TS1 accessory/controller/display.
- The supported local platform is Orange Pi Zero 3 plus a Hosyond 3.5-inch ST7796U SPI LCD and FT6336U I2C capacitive touch controller.
- The Orange Pi backend owns GPIO and the laser USB serial device in normal Network mode.
- GRBL Network mode TCP port is fixed at `23` for deployment.
- VirtualHere is backup/service mode only.
- The GRBL proxy and VirtualHere must never own the laser USB device at the same time.
- The selected laser connection mode is persistent across reboot and failures: `network` or `virtualhere`.
- USB devices must be matched by VID, PID, serial, or descriptive fallback. Never assume `/dev/ttyUSB0` or `/dev/video0`.
- Either physical USB port may contain either camera or laser; identity determines assignment.
- Display/touch pin assignments must stay configurable and documented until physical wiring is confirmed.

## Safety Rules

- Physical GPIO outputs must initialize safe before higher-level services start.
- K1 is the hard E-stop relay and kills the laser controller completely.
- K1 is normally energized during normal operation.
- Any E-stop source must drop K1 immediately and mark the machine unhomed.
- E-stop sources include physical E-stop, local touchscreen command, web command, software E-stop, active LightBurn stream loss, laser USB loss while K1 is expected on, and future fire logic.
- Fire infrastructure must remain present, but `fire.enabled` defaults to `false`.
- Camera failure never stops the laser.
- Unexpected LightBurn TCP stream loss during an active job is fatal and must drop K1.
- Unexpected laser USB disappearance while K1 is supposed to be energized is fatal and must drop K1.
- If K1 is intentionally dropped, laser USB disappearance is expected and should not create a second USB fault.
- Never implement automatic job resume after E-stop, Pi reboot, power failure, controller reset, or unexpected laser USB loss.
- After recovery, LightBurn is responsible for reconnecting and homing.

## Development Rules

- Keep hardware adapters mockable and development-friendly on macOS/Linux.
- Do not guess Orange Pi display SPI/I2C/GPIO pin assignments.
- Do not guess VirtualHere binary paths.
- Do not guess camera streamer commands.
- Do not guess laser VID/PID.
- Add or update tests whenever changing safety behavior, mode ownership, GRBL proxy behavior, display/touch configuration, or command handling.
- Do not run install scripts or systemd commands on the development machine unless the user explicitly asks.
