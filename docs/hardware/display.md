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
  spi_device: null
  spi_speed_hz: 24000000
  dc_gpio_chip: gpiochip0
  dc_gpio_line: null
  reset_gpio_chip: gpiochip0
  reset_gpio_line: null
  backlight_gpio_chip: gpiochip0
  backlight_gpio_line: null

touch:
  controller: FT6336U
  i2c_bus: null
  i2c_address: 0x38
  rotation: 90
  interrupt_gpio_chip: gpiochip0
  interrupt_gpio_line: null
```

## Wiring Table

Final Orange Pi header pins are intentionally TBD until the display is physically wired and the enabled buses are confirmed.

| Module signal | Orange Pi signal | Config key | Status |
| --- | --- | --- | --- |
| 5V | 5V | n/a | TODO |
| GND | GND | n/a | TODO |
| LCD SCK | SPI SCLK | `display.spi_device` | TODO |
| LCD MOSI/SDA | SPI MOSI | `display.spi_device` | TODO |
| LCD CS | SPI CS | `display.spi_device` or GPIO if split later | TODO |
| LCD D/C | GPIO | `display.dc_gpio_line` | TODO |
| LCD RESET | GPIO | `display.reset_gpio_line` | TODO |
| LCD BL | GPIO or 3.3 V enable | `display.backlight_gpio_line` | TODO |
| Touch SDA | I2C SDA | `touch.i2c_bus` | TODO |
| Touch SCL | I2C SCL | `touch.i2c_bus` | TODO |
| Touch INT | GPIO | `touch.interrupt_gpio_line` | Optional TODO |

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
