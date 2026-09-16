# Hosyond ST7796U / FT6336U Display

This project targets the Hosyond 3.5-inch IPS capacitive touch LCD module, ASIN `B0CMD7Y55M`, as the local operator panel for the Orange Pi Zero 3.

## Module Facts

- LCD controller: ST7796U.
- Touch controller: FT6336U.
- Native portrait resolution: `320x480`.
- Application orientation: `480x320` landscape.
- Pixel format: RGB565.
- Module power: 5 V.
- GPIO logic: 3.3 V.

## Driver Approach

The first implementation pass provides a userspace fallback:

- `backend.display.st7796_display.ST7796Display` drives ST7796U over Linux `spidev`.
- `backend.input.ft6336_touch.FT6336Touch` reads FT6336U over Linux I2C with `smbus2`.
- `backend.display.desktop_display.DesktopDisplay` writes `.state/display.ppm` for development.

If the final Orange Pi OS image exposes the display through a reliable kernel DRM/fbdev/input stack, that path should be preferred later. Do not assume Raspberry Pi overlays or Raspberry Pi-only libraries.

## Config

Display and touch configuration lives in `config/controller.example.yaml`:

```yaml
display:
  controller: ST7796U
  width: 480
  height: 320
  rotation: 90
  spi_device: /dev/spidev1.0
  spi_speed_hz: 24000000
  dc_gpio_chip: gpiochip0
  dc_gpio_line: 70
  reset_gpio_chip: gpiochip0
  reset_gpio_line: 73
  backlight_gpio_chip: null
  backlight_gpio_line: null

touch:
  controller: FT6336U
  i2c_bus: 3
  i2c_address: 0x38
  rotation: 90
  reset_gpio_chip: gpiochip0
  reset_gpio_line: 69
  interrupt_gpio_chip: gpiochip0
  interrupt_gpio_line: 75
```

## Wiring Table

Proposed LCD/touch wiring, checked against existing project GPIO use:

| LCD module signal | Orange Pi Zero 3 signal | Header pin | Linux GPIO | Config | Status |
| --- | --- | ---: | ---: | --- | --- |
| VCC | 5V | 2 or 4 | n/a | n/a | OK |
| GND | Ground | 6 | n/a | n/a | OK |
| LCD_CS | SPI1 CS | 24 | n/a | `display.spi_device` | OK, verify `/dev/spidev1.0` |
| MOSI / SDI | SPI1 MOSI | 19 | n/a | `display.spi_device` | OK |
| MISO / SDO | SPI1 MISO | 21 | n/a | `display.spi_device` | OK |
| SCK / CLK | SPI1 CLK | 23 | n/a | `display.spi_device` | OK |
| LCD_DC / RS | PC6 | 11 | 70 | `display.dc_gpio_line` | OK |
| LCD_RST | PC9 | 7 | 73 | `display.reset_gpio_line` | OK |
| CTP_SDA | I2C3 SDA | 3 | n/a | `touch.i2c_bus` | OK, verify `/dev/i2c-3` |
| CTP_SCL | I2C3 SCL | 5 | n/a | `touch.i2c_bus` | OK, verify `/dev/i2c-3` |
| CTP_RST | PC5 | 13 | 69 | `touch.reset_gpio_line` | OK |
| CTP_INT | PC11 | 12 | 75 | `touch.interrupt_gpio_line` | OK |

Do not wire CTP_INT to PC8; PC8 is reserved for the K1 E-stop relay.

## Project Pin Ownership

| Orange Pi pin | Header pin | Linux GPIO | Owner |
| --- | ---: | ---: | --- |
| PC5 | 13 | 69 | Touch reset |
| PC6 | 11 | 70 | LCD D/C |
| PC8 | 15 | 72 | K1 E-stop relay |
| PC9 | 7 | 73 | LCD reset |
| PC11 | 12 | 75 | Touch interrupt |
| PC14 | 18 | 78 | Power sense input |
| PC15 | 16 | 79 | E-stop power sense input |

## Orange Pi Setup

Install runtime packages:

```bash
sudo apt-get update
sudo apt-get install -y gpiod i2c-tools libgpiod-dev python3-libgpiod python3-smbus
```

Enable SPI and I2C using the image-specific configuration tool:

```bash
sudo armbian-config
# or on Orange Pi OS:
sudo orangepi-config
sudo reboot
```

Verify buses and GPIO after reboot:

```bash
ls /dev/spidev*
ls /dev/i2c-*
gpioinfo
i2cdetect -l
```

Scan the selected I2C bus after wiring touch:

```bash
sudo i2cdetect -y <bus-number>
```

The FT6336U usually appears at `0x38`; keep the address configurable.

## Diagnostics

Desktop framebuffer:

```bash
.venv/bin/python scripts/diagnostics/display_test.py --config config/controller.example.yaml --display desktop
open .state/display.ppm
```

Physical display:

```bash
.venv/bin/python scripts/diagnostics/display_test.py --config /etc/travel-laser/controller.yaml --display st7796
```

Touch:

```bash
.venv/bin/python scripts/diagnostics/touch_test.py --config /etc/travel-laser/controller.yaml
```

Hardware inventory:

```bash
.venv/bin/python scripts/diagnostics/hardware_info.py --config /etc/travel-laser/controller.yaml
```

## Troubleshooting

- If `/dev/spidev*` is missing, SPI is not enabled or the OS image uses a different overlay/config mechanism.
- If `/dev/i2c-*` is missing, I2C is not enabled.
- If touch does not appear in `i2cdetect`, check power, ground, SDA/SCL wiring, and bus number.
- If the display is white or black, verify D/C, RESET, CS, and backlight wiring first.
- If colors are wrong, verify RGB565 byte order and ST7796U MADCTL rotation.
- If updates are slow, reduce redraw area or evaluate a kernel DRM/fbdev driver path.
