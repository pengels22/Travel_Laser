# Networking

The intended deployment has a dedicated private TS1 AP and a separate uplink path.

- TS1 private AP: hidden `TS1PE`, Pi address `10.42.0.1/24`.
- TS1 private AP runs on built-in `wlan0`.
- TS1 private AP is hidden, always enabled, and named `TS1PE`.
- TS1 private AP password is `AsDfGhJkL13579!`.
- The built-in TS1 AP should remain enabled regardless of uplink state.
- Uplink Wi-Fi: configurable, should not modify the TS1 AP.
- Ethernet: preferred when connected.
- Remote browser access is expected through Tailscale.

Do not change or disable `wlan0` when configuring uplink Wi-Fi.
