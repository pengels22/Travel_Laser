# Networking

The intended deployment has a dedicated private TS1 AP and a separate uplink path.

- The Orange Pi built-in `wlan0` hosts the hidden always-enabled TS1 network.
- The TS1 device should not run its own AP mode; it should connect as a client to `wlan0`.
- TS1 network name: `TS1PE`.
- TS1 private AP address: `10.42.0.1/24`.
- TS1 private AP password is `AsDfGhJkL13579!`.
- The built-in TS1 AP should remain enabled regardless of uplink state.
- Uplink Wi-Fi uses `wlan1` with route metric `300`.
- `wlan1` is configurable from the TS1 Settings menus for scan, connect/change, and forget.
- Ethernet uses `eth0` with route metric `100`.
- `eth0` is preferred over `wlan1` when both uplinks are connected.
- Remote browser access is expected through Tailscale.

Do not change or disable `wlan0` when configuring uplink Wi-Fi from TS1 menus.

`scripts/configure-network.sh` creates the hidden `wlan0` TS1 network with `nmcli` and applies route metrics for `eth0` and `wlan1`.
