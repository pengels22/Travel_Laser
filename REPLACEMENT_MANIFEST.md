# Travel_Laser validated hardware replacement bundle

This bundle contains full replacement files for the Orange Pi Zero 3 hardware values physically validated on 2026-09-24.

Validated values:

- `/dev/spidev1.1`
- `/dev/i2c-2`
- FT6336U address `0x38`
- `/dev/gpiochip1`
- LCD DC line 70
- touch reset line 69
- 480x320 landscape
- ST7796U MADCTL `0x28`
- ST7796U inversion ON
- 10 MHz SPI validated
- Ethernet interface `end0`
- Wi-Fi interface `wlan0`

New files:

- `hardware/overlays/spi1-cs1-pins.dts`
- `scripts/configure-display-buses.sh`
- `systemd/99-travel-laser-hardware.rules`

Touch interrupt note:

CTP_INT is not used in this build. The FT6336U is polled over I2C, so the interrupt GPIO remains unset and PC8/GPIO72 is dedicated to K1.
