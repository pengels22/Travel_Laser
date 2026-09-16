# GRBL Proxy

The GRBL proxy listens on TCP port `23` in deployment and allows one LightBurn client at a time.

The proxy should remain transparent and conservative around GRBL alarm/error/status strings.

LightBurn should connect to the Travel-Laser IP address shown on the local touchscreen Network page, using TCP port `23`. See `LIGHTBURN.md` for setup notes.

Realtime injections:

- Pause: `!`
- Resume: `~`
- Stop: `0x18`
- Status poll: `?`

Idle-only commands such as `$H` and `$J=` are rejected while a job stream is active. If the LightBurn TCP stream disappears during an active job, K1 must drop immediately.
