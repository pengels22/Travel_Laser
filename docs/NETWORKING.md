# Networking

The intended deployment uses normal uplink networking only. There is no private accessory AP in the active architecture.

- Uplink Wi-Fi uses `wlan1` with route metric `300`.
- `wlan1` is configurable from the local touchscreen Network screen and the web/network backend.
- Ethernet uses `eth0` with route metric `100`.
- `eth0` is preferred over `wlan1` when both uplinks are connected.
- Remote browser access is expected through Tailscale.
- The web portal must bind only to the Orange Pi's configured Tailscale IPv4 address on port `8080`.
- The Tailscale IPv4 address is hardware/network dependent and remains unset until the Orange Pi joins the tailnet.
- The local touchscreen Network screen shows the received IP address for both `eth0` and `wlan1`. Use that IP address for LightBurn's GRBL/TCP connection on port `23`.

`scripts/configure-network.sh` applies route metrics for `eth0` and `wlan1` with `nmcli`.
