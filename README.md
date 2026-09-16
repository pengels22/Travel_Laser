# travel-laser-controller

Orange Pi Zero 3 laser controller for the Travel-Laser build.

Active deployment path:

```text
LightBurn -> TCP port 23 -> Orange Pi GRBL proxy -> USB serial -> laser controller
Orange Pi -> SPI ST7796U display + I2C FT6336U touch -> local 480x320 UI
```

Service mode remains available through VirtualHere, but the GRBL proxy and VirtualHere must never own the laser USB device at the same time.

## Current Status

Implemented:

- Asyncio Python backend package.
- Central asyncio-safe controller state.
- Mock GPIO backend and config-driven Linux GPIO backend.
- Safety controller for the single K1 hard E-stop relay.
- Mockable GRBL TCP proxy with realtime command injection.
- Network vs VirtualHere mode manager with persistent mode file.
- aiohttp web portal with status, STOP, E-STOP, and camera viewer area.
- NetworkManager-backed `wlan1` Wi-Fi scan/connect/forget actions.
- MediaMTX/FFmpeg WebRTC camera service integration.
- Display/touch abstraction layer with desktop framebuffer, ST7796U SPI, and FT6336U I2C implementations.
- Local touchscreen app entry point and diagnostics utilities.

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
```

Run backend in mock mode:

```bash
.venv/bin/travel-laser-controller --mock --config config/controller.example.yaml
```

Render the local UI to a development framebuffer file:

```bash
.venv/bin/travel-laser-ui --config config/controller.example.yaml --display desktop --touch none
open .state/display.ppm
```

GRBL network mode is fixed to TCP port `23` for deployment. On macOS and many Linux systems, binding to port 23 may require elevated privileges; for local development, use a copied config with a high TCP port.

## Safety Model

- K1 is the only relay and is normally energized during operation.
- K1 drops out on E-stop conditions, killing the laser controller completely.
- E-stop sources include physical E-stop, local touchscreen E-stop, web E-stop, software E-stop, future fire logic, active LightBurn stream loss, and laser USB loss while K1 is expected on.
- Software E-stop clears only after cycling the physical E-stop input from active back to OK.
- No job auto-resume is implemented after E-stop, reboot, power failure, controller reset, or unexpected laser USB loss.
- Camera loss is non-fatal.

## Orange Pi Pinout

| Function | Orange Pi pin | Linux GPIO | Header pin | Direction | Active state |
| --- | --- | ---: | ---: | --- | --- |
| E-stop OK switch | PC15 | 79 | 16 | Input | High = OK, low = E-stop active |
| K1 hard E-stop relay | PC8 | 72 | 15 | Output | Active high |

These project GPIOs are configured on `gpiochip0`. PC15 uses `bias: none` because the switch signal is deterministic high/low from the wiring.

## Display And Touch

Target module: Hosyond 3.5-inch IPS capacitive touch LCD, ASIN `B0CMD7Y55M`.

| Module function | Driver | Bus | Config key | Status |
| --- | --- | --- | --- | --- |
| LCD | ST7796U | SPI | `display.spi_device` | TODO: confirm final Orange Pi SPI device |
| Touch | FT6336U | I2C | `touch.i2c_bus`, `touch.i2c_address` | TODO: confirm final Orange Pi I2C bus |
| D/C | GPIO | GPIO | `display.dc_gpio_line` | TODO: choose final pin |
| RESET | GPIO | GPIO | `display.reset_gpio_line` | TODO: choose final pin |
| Backlight | GPIO | GPIO | `display.backlight_gpio_line` | TODO: choose final pin or tie on |
| Touch interrupt | GPIO | GPIO | `touch.interrupt_gpio_line` | Optional TODO |

See `docs/hardware/display.md` for wiring placeholders, driver approach, setup commands, and troubleshooting.

## Orange Pi Install Notes

```bash
sudo apt-get update
sudo apt-get install -y curl ffmpeg git gpiod i2c-tools jq libgpiod-dev network-manager python3-dev python3-libgpiod python3-pip python3-smbus python3-venv rsync v4l-utils
sudo scripts/install.sh
sudo scripts/configure-network.sh
sudo systemctl start mediamtx.service travel-laser-camera.service travel-laser-controller.service travel-laser-ui.service
```

Enable SPI/I2C using the board image tooling, then reboot:

```bash
sudo armbian-config
# or, on Orange Pi OS images:
sudo orangepi-config
```

After reboot, verify:

```bash
ls /dev/spidev*
ls /dev/i2c-*
gpioinfo
i2cdetect -l
```

## Diagnostics

```bash
.venv/bin/python scripts/diagnostics/hardware_info.py --config config/controller.example.yaml
.venv/bin/python scripts/diagnostics/display_test.py --config config/controller.example.yaml --display desktop
.venv/bin/python scripts/diagnostics/display_test.py --config /etc/travel-laser/controller.yaml --display st7796
.venv/bin/python scripts/diagnostics/touch_test.py --config /etc/travel-laser/controller.yaml
```

## Remaining Hardware-Dependent Items

- Identify laser USB VID/PID/serial.
- Identify camera USB VID/PID/serial.
- Set `CAMERA_DEVICE` in `systemd/travel-laser-camera.service` to a stable `/dev/v4l/by-id/...` path after the camera is present.
- Confirm the highest stable camera mode reported by `v4l2-ctl --list-formats-ext`.
- Confirm exact SPI device, I2C bus, and GPIO lines for the Hosyond display/touch module.
- Confirm whether ST7796U userspace SPI is fast enough or whether a kernel DRM/fbdev route is better on the chosen OS image.
- Confirm the exact VirtualHere service name and whether backend-controlled mode switching should start/stop that service or leave it manual.
