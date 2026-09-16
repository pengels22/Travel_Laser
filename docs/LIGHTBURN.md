# LightBurn Network Setup

Travel-Laser presents the laser controller to LightBurn as a GRBL device over TCP.

## Connection Target

- Mode: Network mode
- Protocol/device type: GRBL over TCP/network
- Host/address: use the IP address shown on the local touchscreen Network page
  - Prefer Ethernet `eth0` when connected.
  - Use Wi-Fi `wlan0` only when Ethernet is unavailable.
- Port: `23`

The GRBL proxy listens on `0.0.0.0:23` in deployment, so either received Ethernet or Wi-Fi IP can be used by LightBurn as long as the computer can reach that network.

## Ground Rules

- Only one LightBurn TCP client is accepted at a time.
- The Orange Pi owns the laser USB serial device in Network mode.
- VirtualHere service mode must be off when LightBurn connects through TCP.
- The proxy is intended to be transparent GRBL transport. It does not expose LightBurn file names, job names, layer names, artwork previews, or estimated time remaining.
- If an active LightBurn stream unexpectedly disconnects, K1 drops immediately.

## Local Touchscreen Support

The local Network page must show the received IP address for both interfaces:

- Ethernet `eth0`: connection state and received IP address
- Wi-Fi `wlan0`: selected SSID, connection state, and received IP address

The IP address shown there is the address to enter in LightBurn.
