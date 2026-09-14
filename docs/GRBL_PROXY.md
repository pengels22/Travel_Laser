# GRBL Proxy

The GRBL proxy listens on TCP port `23` in deployment and allows one LightBurn client at a time.

Realtime injections:

- Pause: `!`
- Resume: `~`
- Stop: `0x18`
- Status poll: `?`

Idle-only commands such as `$H` and `$J=` are rejected while a job stream is active. If the LightBurn TCP stream disappears during an active job, K2 must drop immediately.

