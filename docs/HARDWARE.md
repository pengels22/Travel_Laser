# Hardware

Known relay meanings:

- K1: laser power relay.
- K2: E-stop / interrupt relay.

Known Orange Pi pin assignments:

- PC14: laser power button / physical latching power switch input.
- PC15: physical E-stop latching switch input.
- PC5: K1 laser power relay output.
- PC8: K2 E-stop / interrupt relay output.

Relay polarity:

- K1 is confirmed active high.
- K2 is confirmed active high.

Open GPIO mapping item:

- PC5, PC8, PC14, and PC15 are expected to appear on `gpiochip0` or `gpiochip1`.
- GPIO chip and Linux line numbers must still be verified on the real Orange Pi Zero 3 Armbian image using Orange Pi pinout documentation plus `gpioinfo`.
- Configure `chip` and `line` in `/etc/ts1-controller/controller.yaml` after validation.

USB devices must be identified by VID, PID, serial, or descriptive fallback. Do not rely on `/dev/ttyUSB0` or `/dev/video0`.
