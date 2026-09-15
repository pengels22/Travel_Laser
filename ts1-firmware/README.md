# TS1 ESP32 Firmware Placeholder

This is a minimal PlatformIO scaffold for the future TS1 HMI firmware.

Planned behavior:

- Connect as a client to the hidden `TS1PE` network hosted by the Orange Pi `wlan0` adapter.
- Open WebSocket connection to `ws://10.42.0.1:8765/ws`.
- Send hello packet with shared token.
- Show three pages:
  - Main
  - Controls
  - Settings
- Use LVGL, TFT_eSPI, and capacitive touch after exact display and touch hardware pinout is confirmed.

Do not guess LCD, touch, or board pin mappings yet.
