# ts1-laser-controller

Orange Pi Zero 3 backend for a Sculpfun TS1 laser controller retrofit. The deployed hostname is `Travel-Laser`.

Normal network mode:

```text
LightBurn -> TCP port 23 -> Orange Pi GRBL proxy -> USB serial -> laser controller
```

Service mode:

```text
Mac or service computer -> VirtualHere -> Orange Pi USB -> laser controller
```

The TS1 ESP32 HMI connects as a client to the hidden `TS1PE` network hosted by the Orange Pi built-in `wlan0`, then talks to the backend through WebSocket at `ws://10.42.0.1:8765/ws`.

## Current Status

This is a first major implementation pass. It runs in development/mock mode on macOS or Linux without GPIO, laser hardware, camera hardware, or VirtualHere installed.

Implemented:

- Asyncio Python backend package.
- Central asyncio-safe controller state.
- Mock GPIO backend and config-driven Linux GPIO backend.
- Safety controller for K1/K2 behavior.
- Mockable GRBL TCP proxy with realtime command injection.
- Network vs VirtualHere mode manager with persistent mode file.
- TS1-style WebSocket packet handling.
- aiohttp web portal with status, STOP, and E-STOP.
- USB identity abstractions.
- Structured event logging support.
- Example config, docs, scripts, systemd units, and tests.
- NetworkManager-backed `wlan1` Wi-Fi scan/connect/forget actions.
- MediaMTX/FFmpeg WebRTC camera service integration.

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
```

Run in mock mode:

```bash
.venv/bin/ts1-controller --mock --config config/controller.example.yaml
```

Note: GRBL network mode is fixed to TCP port `23`. On macOS and many Linux systems, binding to port 23 may require elevated privileges. For development, use a copied local config with a high TCP port while preserving `23` in deployment config.

## Safety Model

- K1 controls laser power relay behavior.
- K2 is normally energized and drops out on E-stop conditions, killing the laser controller completely.
- K1 remains on during E-stop when the power switch is on, except enabled fire detection may drop K1.
- E-stop sources include physical E-stop, TS1 WebSocket E-stop, web E-stop, software E-stop, future fire logic, active LightBurn stream loss, and laser USB loss while K2 is expected on.
- No job auto-resume is implemented after E-stop, reboot, power failure, controller reset, or unexpected laser USB loss.
- Camera loss and TS1 disconnect alone are non-fatal.

## Orange Pi Pinout

| Function | Orange Pi pin | Linux GPIO | Header pin | Direction | Active state |
| --- | --- | ---: | ---: | --- | --- |
| Laser power switch | PC14 | 78 | 18 | Input | High = power on |
| E-stop OK switch | PC15 | 79 | 16 | Input | High = OK, low = E-stop active |
| K1 laser power relay | PC5 | 69 | 13 | Output | Active high |
| K2 hard E-stop relay | PC8 | 72 | 15 | Output | Active high |

All four project GPIOs are configured on `gpiochip0`. PC14 and PC15 use `bias: none` because the switch signals are deterministic high/low from the wiring.

## Remaining Hardware-Dependent Items

- Identify laser USB VID/PID/serial.
- Identify camera USB VID/PID/serial.
- Replace `CAMERA_DEVICE=/dev/video0` in `systemd/ts1-camera.service` with a stable `/dev/v4l/by-id/...` path after the camera is present.
- Confirm the highest stable camera mode reported by `v4l2-ctl --list-formats-ext`; the service currently selects the largest advertised resolution and starts at 30 FPS.
- Confirm the exact VirtualHere service name and whether backend-controlled mode switching should start/stop that service or leave it manual.
- Set final WebSocket shared token, currently `CHANGE_ME`.
- Confirm Tailscale device name/IP after first login.
- TS1 firmware remains a placeholder scaffold until display, touch, and ESP32 pinout are confirmed.

## Install Notes

The Orange Pi install path uses Debian/Armbian package tooling for Python, NetworkManager, libgpiod, FFmpeg, and V4L2 utilities. MediaMTX is installed from the latest Linux ARM release via GitHub.

Useful deployment commands:

```bash
sudo apt-get update
sudo apt-get install -y curl ffmpeg git gpiod jq libgpiod-dev network-manager python3-dev python3-libgpiod python3-pip python3-venv rsync v4l-utils
sudo scripts/install.sh
sudo scripts/configure-network.sh
sudo systemctl start mediamtx.service ts1-camera.service ts1-controller.service
```
