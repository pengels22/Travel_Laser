# Hardware

Known relay meanings:

- K1: laser power relay.
- K2: E-stop relay that kills the laser controller completely.

Known Orange Pi pin assignments:

- PC12: laser power button / physical latching power switch input.
- PC15: physical E-stop latching switch input.
- PC5: K1 laser power relay output.
- PC8: K2 E-stop relay output.

Relay polarity:

- K1 is confirmed active high.
- K2 is confirmed active high.

K2 behavior:

- K2 is the hard E-stop path.
- Dropping K2 kills the laser controller completely.
- The laser USB serial device is expected to disappear when K2 drops.
- USB disappearance after an intentional K2 drop is normal and must not be logged as a second critical USB fault.

Input behavior:

- PC12 and PC15 switch inputs are on `gpiochip0`.
- PC12 high means the laser power switch is on.
- PC15 high means E-stop OK. PC15 low means E-stop active.
- Because internal software state tracks "E-stop active", PC15 is configured as active-low in `controller.yaml`.
- PC12 and PC15 switch inputs are not pulled up or down by the controller configuration.
- The switch signals are expected to be deterministic high or low with no floating/in-between state.
- Do not enable internal GPIO pull-up/down bias unless the physical wiring changes.

Serial:

- GRBL serial baud is confirmed at `115200`.

Fire safety:

- Fire handling code exists but is blocked by `FIRE_SENSOR: false` and `fire.sensor_enabled: false`.
- When fire sensing is later enabled and fire is active, K1 and K2 should both drop.

Open GPIO mapping item:

- PC5, PC8, PC12, and PC15 Linux line numbers must still be verified.
- GPIO chip and Linux line numbers must still be verified on the real Orange Pi Zero 3 Armbian image using Orange Pi pinout documentation plus `gpioinfo`.
- Configure `chip` and `line` in `/etc/ts1-controller/controller.yaml` after validation.

USB devices must be identified by VID, PID, serial, or descriptive fallback. Do not rely on `/dev/ttyUSB0` or `/dev/video0`.
