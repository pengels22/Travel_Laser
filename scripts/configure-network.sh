#!/usr/bin/env bash
set -euo pipefail

TS1_IFACE="${TS1_IFACE:-wlan0}"
TS1_SSID="${TS1_SSID:-TS1PE}"
TS1_PASSWORD="${TS1_PASSWORD:-AsDfGhJkL13579!}"
TS1_ADDRESS="${TS1_ADDRESS:-10.42.0.1/24}"
ETH_IFACE="${ETH_IFACE:-eth0}"
ETH_METRIC="${ETH_METRIC:-100}"
WIFI_UPLINK_IFACE="${WIFI_UPLINK_IFACE:-wlan1}"
WIFI_UPLINK_METRIC="${WIFI_UPLINK_METRIC:-300}"

nmcli connection delete ts1-link >/dev/null 2>&1 || true
nmcli connection add type wifi ifname "${TS1_IFACE}" con-name ts1-link ssid "${TS1_SSID}"
nmcli connection modify ts1-link \
  802-11-wireless.mode ap \
  802-11-wireless.hidden yes \
  802-11-wireless.band bg \
  wifi-sec.key-mgmt wpa-psk \
  wifi-sec.psk "${TS1_PASSWORD}" \
  ipv4.method shared \
  ipv4.addresses "${TS1_ADDRESS}" \
  ipv6.method ignore \
  connection.autoconnect yes
nmcli connection up ts1-link

if nmcli device status | awk '{print $1}' | grep -qx "${ETH_IFACE}"; then
  nmcli connection modify "${ETH_IFACE}" ipv4.route-metric "${ETH_METRIC}" ipv6.route-metric "${ETH_METRIC}" || true
fi

if nmcli device status | awk '{print $1}' | grep -qx "${WIFI_UPLINK_IFACE}"; then
  nmcli connection modify "${WIFI_UPLINK_IFACE}" ipv4.route-metric "${WIFI_UPLINK_METRIC}" ipv6.route-metric "${WIFI_UPLINK_METRIC}" || true
fi

echo "Configured ${TS1_IFACE} as hidden ${TS1_SSID}; uplink metrics ${ETH_IFACE}=${ETH_METRIC}, ${WIFI_UPLINK_IFACE}=${WIFI_UPLINK_METRIC}."
