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

TS1 settings Wi-Fi actions:

- `wifi_scan`
- `wifi_connect`
- `wifi_forget`

These actions apply only to uplink Wi-Fi on `wlan1`. They must not change or disable the hidden `wlan0` TS1 network.

## Web Portal

- `GET /api/status`
- `POST /api/stop`
- `POST /api/estop`

The web portal intentionally excludes jog, home, Wi-Fi settings, and mode switching.

The web portal is hosted on `0.0.0.0:8080` and embeds the configured WebRTC camera stream in a simple viewer.
