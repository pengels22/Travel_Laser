#!/usr/bin/env bash
set -euo pipefail

ETH_IFACE="${ETH_IFACE:-eth0}"
ETH_METRIC="${ETH_METRIC:-100}"
WIFI_UPLINK_IFACE="${WIFI_UPLINK_IFACE:-wlan0}"
WIFI_UPLINK_METRIC="${WIFI_UPLINK_METRIC:-300}"

if nmcli device status | awk '{print $1}' | grep -qx "${ETH_IFACE}"; then
  nmcli connection modify "${ETH_IFACE}" ipv4.route-metric "${ETH_METRIC}" ipv6.route-metric "${ETH_METRIC}" || true
fi

if nmcli device status | awk '{print $1}' | grep -qx "${WIFI_UPLINK_IFACE}"; then
  nmcli connection modify "${WIFI_UPLINK_IFACE}" ipv4.route-metric "${WIFI_UPLINK_METRIC}" ipv6.route-metric "${WIFI_UPLINK_METRIC}" || true
fi

echo "Configured uplink metrics: ${ETH_IFACE}=${ETH_METRIC}, ${WIFI_UPLINK_IFACE}=${WIFI_UPLINK_METRIC}."
