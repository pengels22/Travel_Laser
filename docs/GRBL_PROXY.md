# GRBL Proxy

The GRBL proxy listens on TCP port `23` in deployment and allows one LightBurn client at a time.

Static inspection of the TS1 `v1.1.30` firmware shows `Grbl_ESP32` and standard GRBL alarm/error/status strings, so the proxy should remain transparent and conservative.

Realtime injections:

- Pause: `!`
- Resume: `~`
- Stop: `0x18`
- Status poll: `?`

Idle-only commands such as `$H` and `$J=` are rejected while a job stream is active. If the LightBurn TCP stream disappears during an active job, K1 must drop immediately.
