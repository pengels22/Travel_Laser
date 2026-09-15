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

Expected screens are Home/Status, Files/Jobs, Jog/Position, Laser Controls, Network, Settings, and System/Diagnostics. The first implementation pass includes the display/touch abstraction and a minimal home/status surface; the full screen flows are still TODO.

## Network Settings

Network settings apply to uplink Wi-Fi on `wlan1`. Ethernet `eth0` remains preferred when both uplinks are connected.
