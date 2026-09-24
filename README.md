# travel-laser-controller

Orange Pi Zero 3 controller for the Travel-Laser build.

Active path:

```text
LightBurn -> TCP port 23 -> Orange Pi GRBL proxy -> USB serial -> laser controller
Orange Pi -> SPI ST7796U display + I2C FT6336U touch -> local 480x320 UI
```

The vendor TS1 controller/display is retired from the active design.

## Validated Orange Pi Hardware

Validated on:

```text
Orange Pi Zero 3
Armbian_community 26.11.0-trunk.52 trixie
Debian 13
Linux 6.18.52-current-sunxi64
```

Current Linux device mapping:

```text
Main H618 GPIO: /dev/gpiochip1
SPI1 display:   /dev/spidev1.1
I2C3 touch:     /dev/i2c-2
Touch address:  0x38
Ethernet:       end0
Wi-Fi:          wlan0
```

### Display

Hosyond 3.5-inch IPS capacitive touch module, ASIN `B0CMD7Y55M`.

ST7796U settings physically validated:

```text
Native panel:     320x480
Application:      480x320 landscape
SPI:              SPI1 CS1
SPI speed:        10 MHz validated
Pixel format:     RGB565
Landscape MADCTL: 0x28
Display inversion: ON (0x21)
```

Wiring:

| LCD signal | Orange Pi signal | SoC pin | Header pin | Linux/config |
| --- | --- | --- | ---: | --- |
| VCC | 5 V | n/a | 2 or 4 | n/a |
| GND | Ground | n/a | 6 | n/a |
| SCK | SPI1 CLK | PH6 | 23 | `/dev/spidev1.1` |
| MOSI | SPI1 MOSI | PH7 | 19 | `/dev/spidev1.1` |
| MISO | SPI1 MISO | PH8 | 21 | `/dev/spidev1.1` |
| LCD_CS | SPI1 CS1 | PH9 | 24 | `/dev/spidev1.1` |
| LCD_DC | GPIO | PC6 | 11 | `/dev/gpiochip1`, line 70 |
| LCD_RST | GPIO | PC9 | 7 | physically connected only; do not claim in userspace |

PC9/GPIO73 is reserved by the Orange Pi Zero 3 PMIC interrupt on the validated kernel. The display works without userspace hardware-reset control.

### Touch

FT6336U settings physically validated:

```text
I2C bus:    /dev/i2c-2
Address:    0x38
CTP_RST:    /dev/gpiochip1 line 69 / PC5 / pin 13
Landscape:  x = raw_y
            y = 319 - raw_x
```

I2C3 wiring:

| Touch signal | Orange Pi signal | SoC pin | Header pin |
| --- | --- | --- | ---: |
| CTP_SCL | I2C3 SCL | PH4 | 5 |
| CTP_SDA | I2C3 SDA | PH5 | 3 |
| CTP_RST | GPIO | PC5 | 13 |

The application polls touch over I2C, so CTP_INT is not required.

## Touch Interrupt

CTP_INT is not used in this build. The FT6336U backend polls the controller over I2C, so the production configuration leaves:

```text
touch.interrupt_gpio_chip: null
touch.interrupt_gpio_line: null
```

PC8/GPIO72 therefore remains dedicated to the K1 hard E-stop relay output.

## SPI/I2C Boot Configuration

The validated Armbian boot environment uses:

```text
overlays=i2c3-ph spidev1_1
user_overlays=spi1-cs1-pins
```

The normal `spidev1_1` overlay creates `/dev/spidev1.1`, but on this image it did not assign the physical SPI1 header pins. The repository therefore contains:

```text
hardware/overlays/spi1-cs1-pins.dts
scripts/configure-display-buses.sh
```

Run once if the machine is not already configured:

```bash
sudo apt install -y device-tree-compiler
sudo ./scripts/configure-display-buses.sh
sudo reboot
```

After reboot verify:

```bash
ls -l /dev/spidev1.1 /dev/i2c-2

sudo grep -E 'PH6|PH7|PH8|PH9' \
  /sys/kernel/debug/pinctrl/300b000.pinctrl/pinmux-pins
```

Expected SPI1 pinmux:

```text
PH6 -> spi1
PH7 -> spi1
PH8 -> spi1
PH9 -> spi1
```

## GPIO Safety Hardware

Existing Travel-Laser project GPIO assignments:

| Function | SoC pin | Linux line | Header pin | Direction |
| --- | --- | ---: | ---: | --- |
| Power sense | PC14 | 78 | 18 | Input |
| E-stop sense | PC15 | 79 | 16 | Input |
| K1 relay | PC8 | 72 | 15 | Output |

These are configured on `/dev/gpiochip1` on the validated Armbian image.

PC14/PC15 are deterministic external sense signals and use `bias: none`.

## Software Architecture

`travel-laser-controller` owns:

- safety state;
- K1;
- GRBL serial/TCP proxy;
- USB discovery;
- networking;
- mode management;
- logging;
- web/API state.

`travel-laser-ui` owns:

- ST7796U rendering;
- FT6336U touch;
- local 480x320 UI;
- loopback API client.

The local touchscreen API binds only to `127.0.0.1:8081`.

The external web portal is intended to bind to the configured Tailscale IPv4 address on port `8080`.

LightBurn uses GRBL/TCP port `23`.

## Display Driver Notes

`backend/display/st7796_display.py` uses:

- Linux `spidev`;
- libgpiod v2 for LCD_DC and optional GPIO lines;
- validated ST7796U initialization;
- 10 MHz SPI by default;
- inversion command `0x21`;
- RGB565.

LCD hardware reset is optional. On this Orange Pi it is deliberately disabled in config because PC9 is reserved by the PMIC.

## Touch Driver Notes

`backend/input/ft6336_touch.py`:

- uses `/dev/i2c-2`;
- reads device `0x38`;
- pulses CTP_RST through `/dev/gpiochip1` line 69;
- polls rather than depending on CTP_INT;
- maps portrait raw coordinates to 480x320 landscape.

## libgpiod Version

The validated system provides libgpiod 2.2.x. Runtime GPIO code uses the v2 `request_lines()` API.

The installer creates the Python virtual environment with:

```bash
python3 -m venv --system-site-packages .venv
```

so the Debian `python3-libgpiod` package is available inside the application venv.

## Device Permissions

The app runs as the `travel-laser` service user rather than root.

`systemd/99-travel-laser-hardware.rules` grants group access only to the validated hardware nodes:

```text
/dev/spidev1.1 -> spi group
/dev/i2c-2     -> i2c group
/dev/gpiochip1 -> gpio group
```

The installer adds the service user to `gpio`, `i2c`, and `spi`.

## Installation

```bash
sudo apt-get update
sudo ./scripts/install.sh
```

If boot overlays have not already been configured:

```bash
sudo ./scripts/configure-display-buses.sh
sudo reboot
```

Then verify:

```bash
ls -l /dev/spidev1.1 /dev/i2c-2 /dev/gpiochip1
sudo /usr/sbin/i2cdetect -y 2
```

Address `38` should appear in the I2C scan.

## Diagnostics

```bash
.venv/bin/python scripts/diagnostics/hardware_info.py \
  --config /etc/travel-laser/controller.yaml

.venv/bin/python scripts/diagnostics/display_test.py \
  --config /etc/travel-laser/controller.yaml \
  --display st7796

.venv/bin/python scripts/diagnostics/touch_test.py \
  --config /etc/travel-laser/controller.yaml
```

The display diagnostic should render correct red, green, blue, white, and black colors in the correct 480x320 landscape orientation.

## Networking

Validated interface names:

```text
Ethernet: end0
Wi-Fi:    wlan0
```

Preferred route metrics:

```text
end0  = 100
wlan0 = 300
```

The Pi may have simultaneous addresses on Trusted Ethernet and IoT Wi-Fi during bring-up. Do not broaden firewall rules as a shortcut.

Remote administration should use Tailscale and the existing subnet-router path rather than WAN exposure.

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
```

Run backend in mock mode:

```bash
.venv/bin/travel-laser-controller \
  --mock \
  --config config/controller.example.yaml
```

Render the UI to a development framebuffer:

```bash
.venv/bin/travel-laser-ui \
  --config config/controller.example.yaml \
  --display desktop \
  --touch none
```

## Safety Model

- K1 is the hard E-stop relay.
- No automatic job resume after E-stop, reboot, power loss, controller reset, or unexpected laser USB loss.
- Network and VirtualHere modes must never own the laser USB device simultaneously.
- Camera failure is non-fatal.
- Fire logic remains disabled until real fire hardware is present.

## Deployment

`config/deployment.env.example` defaults to `START_SERVICES=true`.

After the remaining deployment placeholders are completed and the K1 safety wiring is verified, run:

```bash
sudo /opt/travel-laser-controller/scripts/deploy.sh
```

The deploy script can auto-fill Tailscale IP, a single camera device, and a single laser serial identity when unambiguous.

## Testing

```bash
.venv/bin/python -m pytest
```

Keep hardware assumptions in config and documentation synchronized with physically verified behavior.
