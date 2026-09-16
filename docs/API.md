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

All local touchscreen screens target `480x320` landscape. Do not design portrait/mobile-style panels for the physical display.

- Home: machine state plus two large same-priority controls, `HOME` and `STOP`.
- Status: GRBL state, LightBurn TCP connection/stream state, Power, E-stop Sense, Safety Relay, and Laser USB connection.
- Network: `eth0` connection state and received IP, `wlan1` selected SSID/state and received IP, Wi-Fi scan, SSID selection, password prompt, connect, forget, and refresh.
- Mode: Network vs VirtualHere ownership. Selecting the inactive mode opens a confirmation popup before changing modes.
- System: display/touch test, diagnostics, service controls, reboot/shutdown.

Bottom navigation order is fixed as `Home`, `Status`, `Net`, `Mode`, `System`. `STOP` is not a navigation tab; it is a large Home-screen action.

Offline clickable walkthrough: `docs/ui/local-touchscreen-walkthrough.html`.

The local UI does not display the camera stream; camera viewing is web UI only. The local UI does not include a file browser or local job launcher. Jobs always originate from the external computer through LightBurn/GRBL. The local UI also must not depend on LightBurn-only metadata such as file name, job name, layer names, previews, or estimated time remaining.

Any text entry on the local touchscreen must open an on-screen keyboard. This includes Wi-Fi passwords and any future editable settings. The UI must not assume a physical keyboard.

System subpages:

- GPIO Status: list all configured GPIO users and logical high/low or active/inactive state.
- USB Identity: show detected laser, camera, and export-drive identities.
- SPI / I2C: show display/touch bus configuration and detection status.
- View Logs: show recent controller/service log lines.
- Export Logs to USB: report automatic export status. Actual export starts automatically when a filesystem USB drive larger than 200 MB is inserted.

## Network Settings

Network settings apply to uplink Wi-Fi on `wlan1`. Ethernet `eth0` remains preferred when both uplinks are connected.

Touchscreen Wi-Fi flow:

1. Tap `Scan`.
2. Select an SSID from the scan result list.
3. Tap `Connect`.
4. Enter the Wi-Fi password when prompted.
5. Confirm connection status on the Network screen.

## Mode Changes

The Mode screen does not show a persistent warning panel. If the user selects the inactive mode, the UI shows a confirmation popup explaining that only one mode can own the laser USB connection at a time and that switching modes releases the current USB owner.
