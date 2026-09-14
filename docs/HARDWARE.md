# Hardware

Known relay meanings:

- K1: laser power relay.
- K2: E-stop / interrupt relay.

Known Orange Pi pin assignments:

- PC14: laser power button / physical latching power switch input.
- PC15: physical E-stop latching switch input.
- PC5: K1 laser power relay output.
- PC8: K2 E-stop / interrupt relay output.

GPIO chip and Linux line numbers are intentionally unset until verified on the real Orange Pi Zero 3 Armbian image. Configure `chip` and `line` in `/etc/ts1-controller/controller.yaml` after validation.

USB devices must be identified by VID, PID, serial, or descriptive fallback. Do not rely on `/dev/ttyUSB0` or `/dev/video0`.
