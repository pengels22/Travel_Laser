# API

## WebSocket

Default endpoint: `ws://10.42.0.1:8765/ws`

Handshake from TS1:

```json
{"type":"hello","device":"ts1","protocol":1,"token":"CHANGE_ME"}
```

Supported packet groups:

- `hello`
- `status`
- `stop`
- `command`
- `settings`

Every command, stop, or settings request returns an `ack` with `ok` and optional `reason`.

## Web Portal

- `GET /api/status`
- `POST /api/stop`
- `POST /api/estop`

The web portal intentionally excludes jog, home, Wi-Fi settings, and mode switching.

