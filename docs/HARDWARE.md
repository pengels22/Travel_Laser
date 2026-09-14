# Hardware

Known relay meanings:

- K1: laser power relay.
- K2: E-stop / interrupt relay.

GPIO chip and line numbers are intentionally unset until measured on the real Orange Pi carrier wiring. Configure them in `/etc/ts1-controller/controller.yaml` after validation.

USB devices must be identified by VID, PID, serial, or descriptive fallback. Do not rely on `/dev/ttyUSB0` or `/dev/video0`.

