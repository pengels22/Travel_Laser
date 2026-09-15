# Architecture

`ts1-laser-controller` is an asyncio Python backend intended for an Orange Pi Zero 3 running Armbian. The deployed hostname is `Travel-Laser`.

Main services:

- GPIO safety service owns the K1 hard E-stop relay output and physical inputs.
- USB manager discovers laser and camera devices by identity.
- GRBL proxy exposes the laser to LightBurn as a TCP GRBL device on port `23`.
- WebSocket API serves the TS1 ESP32 HMI.
- Web portal serves WebRTC camera/status/STOP/E-STOP controls.
- Mode manager enforces exclusive Network vs VirtualHere ownership.

Network mode owns the laser USB serial device. VirtualHere mode is a service/backup path and must not run concurrently with the GRBL proxy. VirtualHere will be installed on the Orange Pi, but its detailed configuration is handled separately from this first-pass backend.

See `FIRMWARE.md` for notes from static inspection of the Sculpfun TS1 `v1.1.30` firmware update binary.
