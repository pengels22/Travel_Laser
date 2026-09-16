# API

## Web Portal

- `GET /api/status`
- `POST /api/stop`
- `POST /api/estop`

The web portal is hosted on `0.0.0.0:8080` and embeds the configured WebRTC camera stream in a simple viewer. If no camera stream URL is configured, it defaults to `http://<current-host>:8889/cam`.

## Local UI

The local touchscreen UI is rendered directly on the Orange Pi. The current first-pass executable is:

```bash
travel-laser-ui --config /etc/travel-laser/controller.yaml --display st7796 --touch ft6336
```

Expected local screens:

- Home: machine state, Home command, Status, Network, Mode, and Stop controls.
- Status: LightBurn TCP connection/stream state, PC14 power sense, PC15 E-stop sense, K1 relay, laser USB connection, and GRBL state.
- Network: `eth0`, `wlan1`, IP address, Wi-Fi scan/connect/forget.
- Mode: Network vs VirtualHere ownership.
- Settings/System: display/touch test, diagnostics, service controls, reboot/shutdown.

The local UI does not display the camera stream; camera viewing is web UI only. The local UI does not include a file browser or local job launcher. Jobs always originate from the external computer through LightBurn/GRBL. The local UI also must not depend on LightBurn-only metadata such as file name, job name, layer names, previews, or estimated time remaining.

## Network Settings

Network settings apply to uplink Wi-Fi on `wlan1`. Ethernet `eth0` remains preferred when both uplinks are connected.
