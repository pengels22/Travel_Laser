# ts1-laser-controller

Orange Pi Zero 3 backend for a Sculpfun TS1 laser controller retrofit.

Normal network mode:

```text
LightBurn -> TCP port 23 -> Orange Pi GRBL proxy -> USB serial -> laser controller
```

Service mode:

```text
Mac or service computer -> VirtualHere -> Orange Pi USB -> laser controller
```

The TS1 ESP32 HMI is planned to connect over a dedicated private Wi-Fi AP and talk to the backend through WebSocket at `ws://10.42.0.1:8765/ws`.

## Current Status

This is a first major implementation pass. It runs in development/mock mode on macOS or Linux without GPIO, laser hardware, camera hardware, or VirtualHere installed.

Implemented:

- Asyncio Python backend package.
- Central asyncio-safe controller state.
- Mock GPIO backend and Linux GPIO placeholder.
- Safety controller for K1/K2 behavior.
- Mockable GRBL TCP proxy with realtime command injection.
- Network vs VirtualHere mode manager with persistent mode file.
- TS1-style WebSocket packet handling.
- aiohttp web portal with status, STOP, and E-STOP.
- USB identity abstractions.
- Structured event logging support.
- Example config, docs, scripts, systemd units, and tests.

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

## Hardware TODOs

- Confirm Orange Pi GPIO chip/line mapping.
- Identify laser USB VID/PID/serial.
- Identify camera USB VID/PID/serial.
- Confirm VirtualHere installation/service behavior.
- Confirm camera streamer command and service.
- Confirm TS1 display, touch, and ESP32 pinout before firmware UI work.
