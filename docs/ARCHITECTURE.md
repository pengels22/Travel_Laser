# Architecture

`travel-laser-controller` is an asyncio Python backend intended for an Orange Pi Zero 3 running Armbian. The deployed hostname is `Travel-Laser`.

Main services:

- GPIO safety service owns the K1 hard E-stop relay output and physical inputs.
- USB manager discovers laser and camera devices by identity.
- GRBL proxy exposes the laser to LightBurn as a TCP GRBL device on port `23`.
- Local UI renders machine controls and hardware status to the Hosyond ST7796U/FT6336U touchscreen stack.
- Web portal serves WebRTC camera/status/STOP/E-STOP controls.
- Mode manager enforces exclusive Network vs VirtualHere ownership.

Network mode owns the laser USB serial device. VirtualHere mode is a service/backup path and must not run concurrently with the GRBL proxy. VirtualHere will be installed on the Orange Pi, but its detailed configuration is handled separately from this first-pass backend.

LightBurn is treated as a GRBL TCP client. The Orange Pi does not store, select, or launch local job files; jobs always originate from the external computer. Do not depend on LightBurn metadata that is not exposed through GRBL/TCP, such as file name, job name, layer names, artwork preview, or estimated time remaining.

Retired vendor accessory/controller research is not part of the active architecture.
