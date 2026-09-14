# Networking

The intended deployment has a dedicated private TS1 AP and a separate uplink path.

- TS1 private AP: hidden `TS1-LINK`, Pi address `10.42.0.1/24`.
- Uplink Wi-Fi: configurable, should not modify the TS1 AP.
- Ethernet: preferred when connected.
- Remote browser access is expected through Tailscale.

Do not hardcode `wlan0` or `wlan1`; use interface identity/config mapping.

