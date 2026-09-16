# Hardware

Known relay meanings:

- K1: E-stop relay that kills the laser controller completely.

Known Orange Pi pin assignments:

- PC5: CTP_RST output, Linux GPIO `69`, header pin `13`.
- PC6: LCD_DC output, Linux GPIO `70`, header pin `11`.
- PC9: LCD_RST output, Linux GPIO `73`, header pin `7`.
- PC11: optional CTP_INT input, Linux GPIO `75`, header pin `12`.
- PC14: power sense input, Linux GPIO `78`, header pin `18`.
- PC15: E-stop power sense input, Linux GPIO `79`, header pin `16`.
- PC8: K1 E-stop relay output, Linux GPIO `72`, header pin `15`.

Display/touch buses:

- ST7796U LCD uses SPI1 only: MOSI PH7/pin `19`, MISO PH8/pin `21`, SCK PH6/pin `23`, CS PH9/pin `24`.
- FT6336U touch uses I2C3 only: SDA PH5/pin `3`, SCL PH4/pin `5`.
- Do not substitute other SPI/I2C buses automatically.
- Do not use PC8 for touch interrupt because PC8 is reserved for K1.

Relay polarity:

- K1 is confirmed active high.

K1 behavior:

- K1 is the hard E-stop path.
- Dropping K1 kills the laser controller completely.
- The laser USB serial device is expected to disappear when K1 drops.
- USB disappearance after an intentional K1 drop is normal and must not be logged as a second critical USB fault.

Input behavior:

- PC14 and PC15 sense inputs are on `gpiochip0`.
- PC14 high means laser input power is present.
- PC15 high means E-stop power sense is OK. PC15 low means E-stop active.
- Because internal software state tracks "E-stop active", PC15 is configured as active-low in `controller.yaml`.
- PC14 and PC15 are not pulled up or down by the controller configuration.
- The sense signals are expected to be deterministic high or low with no floating/in-between state.
- Do not enable internal GPIO pull-up/down bias unless the physical wiring changes.

Serial:

- GRBL serial baud is confirmed at `115200`.

Fire safety:

- Fire handling code exists but is blocked by `FIRE_SENSOR: false` and `fire.sensor_enabled: false`.
- When fire sensing is later enabled and fire is active, K1 should drop.

GPIO mapping source:

- PC5, PC6, PC8, PC9, PC11, PC14, and PC15 are mapped from the Orange Pi Zero 3 official documentation.
- Verify with `gpioinfo` on the target Armbian image during install, but the configured default chip is `gpiochip0`.

USB devices must be identified by VID, PID, serial, or descriptive fallback. Do not rely on `/dev/ttyUSB0` or `/dev/video0`.
