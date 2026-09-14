# Architecture

`ts1-laser-controller` is an asyncio Python backend intended for an Orange Pi Zero 3 running Armbian.

Main services:

- GPIO safety service owns K1/K2 relay outputs and physical inputs.
- USB manager discovers laser and camera devices by identity.
- GRBL proxy exposes the laser to LightBurn as a TCP GRBL device on port `23`.
- WebSocket API serves the TS1 ESP32 HMI.
- Web portal serves camera/status/STOP/E-STOP controls.
- Mode manager enforces exclusive Network vs VirtualHere ownership.

Network mode owns the laser USB serial device. VirtualHere mode is a service/backup path and must not run concurrently with the GRBL proxy.

