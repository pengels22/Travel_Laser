# travel-laser-controller

Orange Pi Zero 3 laser controller for the Travel-Laser build.

Active deployment path:

```text
LightBurn -> TCP port 23 -> Orange Pi GRBL proxy -> USB serial -> laser controller
Orange Pi -> SPI ST7796U display + I2C FT6336U touch -> local 480x320 UI
```

LightBurn connects to the Travel-Laser IP address shown on the local touchscreen Network page using GRBL/TCP port `23`.

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
- NetworkManager-backed `wlan0` Wi-Fi scan/connect/forget actions.
- MediaMTX/FFmpeg WebRTC camera service integration.
- Display/touch abstraction layer with desktop framebuffer, ST7796U SPI, and FT6336U I2C implementations.
- Local touchscreen app entry point with Home, Status, Net, Mode, and System screens plus diagnostics utilities.
- Automatic USB log export when a filesystem flash drive larger than 200 MB is inserted.
- LightBurn TCP/GRBL network setup through TCP port `23`.

The Orange Pi touchscreen is a local control/status panel only. Camera viewing is web UI only, and the project does not expect LightBurn-specific metadata such as file name, job name, layer names, artwork preview, or estimated time remaining. The Pi does not store or launch local job files; jobs always originate from the external computer through LightBurn/GRBL.

User-facing touchscreen labels should use common names such as `Power`, `E-stop Sense`, `Safety Relay`, and `Laser USB`; PC/GPIO names stay in hardware/config documentation.

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

The local UI is designed for the LCD's `480x320` landscape dimensions. The native display renderer uses the same screen order, labels, colors, control layout, and scrollable content behavior defined in this README, with simple pixel-font drawing for the ST7796U framebuffer.

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
| Power sense input | PC14 | 78 | 18 | Input | High = laser input power present |
| E-stop power sense input | PC15 | 79 | 16 | Input | High = OK, low = E-stop active |
| K1 hard E-stop relay | PC8 | 72 | 15 | Output | Active high |

These project GPIOs are configured on `gpiochip0`. PC14 and PC15 use `bias: none` because the sense signals are deterministic high/low from the wiring.

## Display And Touch

Target module: Hosyond 3.5-inch IPS capacitive touch LCD, ASIN `B0CMD7Y55M`.

| Module function | Driver | Bus | Config key | Status |
| --- | --- | --- | --- | --- |
| LCD | ST7796U | SPI1 | `display.spi_device` | SPI1 CS/MOSI/MISO/CLK on PH9/PH7/PH8/PH6, pins 24/19/21/23, verify `/dev/spidev1.0` |
| Touch | FT6336U | I2C3 | `touch.i2c_bus`, `touch.i2c_address` | I2C3 SDA/SCL on PH5/PH4, pins 3/5, verify `/dev/i2c-3` |
| D/C | GPIO | GPIO | `display.dc_gpio_line` | PC6 / GPIO 70 / physical pin 11 |
| RESET | GPIO | GPIO | `display.reset_gpio_line` | PC9 / GPIO 73 / physical pin 7 |
| Backlight | GPIO | GPIO | `display.backlight_gpio_line` | Pending: choose final pin or tie on |
| Touch reset | GPIO | GPIO | `touch.reset_gpio_line` | PC5 / GPIO 69 / physical pin 13 |
| Touch interrupt | GPIO | GPIO | `touch.interrupt_gpio_line` | Optional PC11 / GPIO 75 / physical pin 12; touch falls back to polling |

## Architecture

`travel-laser-controller` is an asyncio Python backend intended for an Orange Pi Zero 3 running Armbian or Orange Pi OS. The deployed hostname is `Travel-Laser`.

Main services:

- GPIO safety service owns K1, the hard E-stop relay output, plus the physical power and E-stop sense inputs.
- USB manager discovers laser and camera devices by VID, PID, serial, or descriptive fallback.
- GRBL proxy exposes the laser to LightBurn as a TCP GRBL device on port `23`.
- Local UI renders machine controls and hardware status to the Hosyond ST7796U/FT6336U touchscreen.
- Web portal serves status, WebRTC camera, STOP, and E-STOP controls.
- Mode manager enforces exclusive Network vs VirtualHere ownership.

Network mode owns the laser USB serial device. VirtualHere mode is a backup/service path and must not run concurrently with the GRBL proxy. VirtualHere is expected to be installed on the Orange Pi, but configured separately unless `VIRTUALHERE_BACKEND_CONTROLS_SERVICE=true` is deliberately enabled after testing.

Retired vendor accessory/controller/display research is not part of the active architecture.

## Networking And LightBurn

The intended deployment uses normal uplink networking only. There is no private accessory AP in the active architecture.

- Ethernet uses `eth0` with route metric `100`.
- Uplink Wi-Fi uses `wlan0` with route metric `300`.
- `eth0` is preferred over `wlan0` when both are connected.
- `wlan0` is configurable from the local touchscreen Network screen and the web/network backend.
- Remote browser access is expected through Tailscale.
- The web portal binds only to the configured Tailscale IPv4 address on port `8080`.
- `scripts/configure-network.sh` applies route metrics for `eth0` and `wlan0` with `nmcli`.

LightBurn setup:

- Mode: Network mode.
- Protocol/device type: GRBL over TCP/network.
- Host/address: use the IP address shown on the local touchscreen Network page.
- Prefer Ethernet `eth0` when connected; use Wi-Fi `wlan0` only when Ethernet is unavailable.
- Port: `23`.

The GRBL proxy listens on `0.0.0.0:23` in deployment. Only one LightBurn TCP client is accepted at a time. The proxy is intended to be transparent GRBL transport and does not expose LightBurn file names, job names, layer names, artwork previews, or estimated time remaining.

## GRBL Proxy

Realtime injections:

- Pause: `!`
- Resume: `~`
- Stop: `0x18`
- Status poll: `?`

Idle-only commands such as `$H` and `$J=` are rejected while a job stream is active. If the active LightBurn TCP stream unexpectedly disconnects, K1 drops immediately.

## Local UI

The local touchscreen UI is rendered directly on the Orange Pi:

```bash
travel-laser-ui --config /etc/travel-laser/controller.yaml --display st7796 --touch ft6336
```

All local screens target `480x320` landscape:

- Home: machine state plus two large same-priority controls, `HOME` and `STOP`.
- Status: GRBL state, LightBurn TCP connection/stream state, Power, E-stop Sense, Safety Relay, Laser USB connection, and Tailscale state.
- Network: `eth0` connection state with received IP below it, `wlan0` SSID/state with received IP below it, Wi-Fi scan, SSID selection, password prompt, connect, forget, and refresh.
- Mode: Network vs VirtualHere ownership. Selecting the inactive mode opens a confirmation popup before changing modes.
- System: display/touch test, diagnostics, service controls, reboot/shutdown, GPIO Status, USB Identity, SPI/I2C status, View Logs, and Export Logs to USB status.

Bottom navigation order is fixed as `Home`, `Status`, `Net`, `Mode`, `System`. `STOP` is not a navigation tab; it is a large Home-screen action.

Any local page content beyond the fixed header/nav viewport must scroll vertically. Dragging within the content area scrolls the current page while nav taps remain fixed. If a drag starts on a button or control, the scroll gesture arms after a 300 ms hold so quick taps still activate controls.

After 20 seconds with no touch input, the deployed local touchscreen returns to the Home screen. Any text entry on the local touchscreen must open an on-screen keyboard, including Wi-Fi passwords and future editable settings.

The local UI does not display the camera stream, does not include a file browser, and does not launch local jobs. Jobs always originate from the external computer through LightBurn/GRBL.

## Web Portal And Camera

- Web portal: `GET /api/status`, `POST /api/stop`, `POST /api/estop`.
- Deployment uses `web.bind_to_tailscale: true`; startup intentionally fails until `network.tailscale.ip_address` is known.
- If no `camera.stream_url` is configured, the portal defaults to `http://<current-host>:8889/cam`.
- MediaMTX serves WebRTC on port `8889`.
- FFmpeg publishes the selected V4L2 camera mode to MediaMTX over RTSP on `127.0.0.1:8554/cam`.
- `scripts/select-camera-mode.sh` selects the largest advertised V4L2 resolution.
- Camera service starts at 30 FPS by default; confirm the highest stable resolution/FPS after the physical camera is present.
- Camera failure never stops the laser and must not affect K1.

## Hardware Details

Known relay meanings:

- K1: E-stop relay that kills the laser controller completely.

Display/touch module facts:

- Target module: Hosyond 3.5-inch IPS capacitive touch LCD, ASIN `B0CMD7Y55M`.
- LCD controller: ST7796U.
- Touch controller: FT6336U.
- Native portrait resolution: `320x480`.
- Application orientation: `480x320` landscape.
- Pixel format: RGB565.
- Module power: 5 V.
- Orange Pi GPIO logic: 3.3 V.
- Never apply 5 V to an Orange Pi GPIO signal pin.

Driver approach:

- `backend.display.st7796_display.ST7796Display` drives ST7796U over Linux `spidev`.
- `backend.input.ft6336_touch.FT6336Touch` reads FT6336U over Linux I2C with `smbus2`.
- `backend.display.desktop_display.DesktopDisplay` writes `.state/display.ppm` for development.
- If the final Orange Pi OS image exposes a reliable kernel DRM/fbdev/input stack, that path can be preferred later.

Final display/touch wiring:

| LCD module signal | Orange Pi Zero 3 signal | SoC pin | Header pin | Linux GPIO | Config |
| --- | --- | --- | ---: | ---: | --- |
| VCC | 5V | n/a | 2 or 4 | n/a | n/a |
| GND | Ground | n/a | 6 | n/a | n/a |
| LCD_CS | SPI1 CS | PH9 | 24 | n/a | `display.spi_device` |
| MOSI / SDI | SPI1 MOSI | PH7 | 19 | n/a | `display.spi_device` |
| MISO / SDO | SPI1 MISO | PH8 | 21 | n/a | `display.spi_device` |
| SCK / CLK | SPI1 CLK | PH6 | 23 | n/a | `display.spi_device` |
| LCD_DC / RS | GPIO | PC6 | 11 | 70 | `display.dc_gpio_line` |
| LCD_RST | GPIO | PC9 | 7 | 73 | `display.reset_gpio_line` |
| CTP_SDA | I2C3 SDA | PH5 | 3 | n/a | `touch.i2c_bus` |
| CTP_SCL | I2C3 SCL | PH4 | 5 | n/a | `touch.i2c_bus` |
| CTP_RST | GPIO | PC5 | 13 | 69 | `touch.reset_gpio_line` |
| CTP_INT | GPIO | PC11 | 12 | 75 | `touch.interrupt_gpio_line` |

CTP_INT on PC11 is optional. The current FT6336U backend polls over I2C, so touch remains usable and does not fail if CTP_INT is left disconnected. Do not wire CTP_INT to PC8; PC8 is reserved for K1.

Bus rules:

- Use SPI1 only for the ST7796U display.
- Use I2C3 only for the FT6336U touch controller.
- Do not bit-bang SPI or I2C.
- Use Linux SPI/I2C subsystems and libgpiod for LCD_RST, LCD_DC, CTP_RST, and optional CTP_INT.
- Keep gpiochip, SPI device path, and I2C bus number configurable until verified on the running OS.
- Do not substitute SPI0, SPI2, I2C0, I2C1, or another bus automatically.
- Do not use Raspberry Pi BCM GPIO numbering.

## Orange Pi Install Notes

```bash
sudo apt-get update
sudo apt-get install -y curl ffmpeg git gpiod i2c-tools jq libgpiod-dev network-manager python3-dev python3-libgpiod python3-pip python3-smbus python3-venv rsync v4l-utils
sudo scripts/deploy.sh
```

On the first run, `scripts/deploy.sh` creates `/etc/travel-laser/deployment.env` if it does not exist, auto-fills safe single-device values, and stops only if required hardware choices remain ambiguous. See `PLACEHOLDERS.md`. Rerun the same deploy script after resolving any missing values; it applies them to `/etc/travel-laser/controller.yaml`, configures network metrics, and starts services when `START_SERVICES=true`.

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

## Log Export

On deployed hardware, inserting a filesystem USB flash drive larger than 200 MB starts `travel-laser-log-export@.service` through udev. Logs are copied to:

```text
<USB drive>/Travel-Laser-Logs/<hostname>-<UTC timestamp>/
```

The export includes `/var/log/travel-laser` plus recent journals for the controller, local UI, camera, and MediaMTX services. Drives under 200 MB are ignored.

## Remaining Hardware-Dependent Items

- Let `scripts/deploy.sh` auto-fill Tailscale IP, camera path, and laser USB identity where the Orange Pi can identify a single safe candidate.
- Resolve any ambiguous deployment values listed in `PLACEHOLDERS.md`.
- Confirm the highest stable camera mode reported by `v4l2-ctl --list-formats-ext` if `highest_available` is unstable.
- Confirm the OS device names for SPI1 and I2C3 after enabling them.
- Confirm whether ST7796U userspace SPI is fast enough or whether a kernel DRM/fbdev route is better on the chosen OS image.
- Confirm the exact VirtualHere service name and whether backend-controlled mode switching should start/stop that service or leave it manual.

## Recovery Rules

No automatic job resume is allowed after E-stop, Pi reboot, power failure, controller reset, or unexpected laser USB loss. After recovery, LightBurn reconnects and homes the machine.

K1 is the hard E-stop path and kills the laser controller completely. If K1 is intentionally dropped, laser USB disappearance is expected and should not create a second critical USB fault.

Software E-stop clear requires the E-stop power sense input to cycle active and back to OK: PC15 low, then PC15 high. Returning PC15 high without a prior low transition does not clear a software E-stop.

## Testing

Run:

```bash
.venv/bin/python -m pytest
```

The suite uses mocks for GPIO, serial, USB, VirtualHere, and network behavior. Safety behavior should always have tests before changes are committed.

## References

- libgpiod documentation: https://libgpiod.readthedocs.io/en/master/
- Debian libgpiod packages: https://packages.debian.org/bookworm/source/libgpiod
- NetworkManager nmcli settings reference: https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nm-settings-nmcli.html
- MediaMTX WebRTC features: https://mediamtx.org/docs/features/webrtc-specific-features
- Linux kernel EDT/FocalTech touch driver docs: https://docs.kernel.org/input/devices/edt-ft5x06.html
- Linux kernel EDT/FocalTech touch driver source: https://github.com/torvalds/linux/blob/master/drivers/input/touchscreen/edt-ft5x06.c
- ST7796 LCD controller datasheet reference: https://orientdisplay.com/st7796-lcd-controller-datasheet/
- 3.5-inch ST7796 SPI module parameter reference: https://www.lcdwiki.com/3.5inch_IPS_SPI_Module_ST7796
