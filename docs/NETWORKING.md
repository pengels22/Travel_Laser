# Networking

The intended deployment uses normal uplink networking only. There is no private accessory AP in the active architecture.

- Uplink Wi-Fi uses `wlan1` with route metric `300`.
- `wlan1` is configurable from the local touchscreen Network screen and the web/network backend.
- Ethernet uses `eth0` with route metric `100`.
- `eth0` is preferred over `wlan1` when both uplinks are connected.
- Remote browser access is expected through Tailscale.

`scripts/configure-network.sh` applies route metrics for `eth0` and `wlan1` with `nmcli`.
