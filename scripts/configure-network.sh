#!/usr/bin/env bash
set -euo pipefail

ETH_IFACE="${ETH_IFACE:-eth0}"
ETH_METRIC="${ETH_METRIC:-100}"
WIFI_UPLINK_IFACE="${WIFI_UPLINK_IFACE:-wlan0}"
WIFI_UPLINK_METRIC="${WIFI_UPLINK_METRIC:-300}"

connection_for_interface() {
  local interface="$1"
  nmcli -t -f GENERAL.CONNECTION device show "${interface}" 2>/dev/null |
    sed -n 's/^GENERAL.CONNECTION://p' | sed 's/:.*$//' | grep -v '^--$' | head -n 1
}

if nmcli device status | awk '{print $1}' | grep -qx "${ETH_IFACE}"; then
  connection="$(connection_for_interface "${ETH_IFACE}" || true)"
  if [[ -n "${connection}" ]]; then
    nmcli connection modify "${connection}" ipv4.route-metric "${ETH_METRIC}" ipv6.route-metric "${ETH_METRIC}"
  fi
fi

if nmcli device status | awk '{print $1}' | grep -qx "${WIFI_UPLINK_IFACE}"; then
  connection="$(connection_for_interface "${WIFI_UPLINK_IFACE}" || true)"
  if [[ -n "${connection}" ]]; then
    nmcli connection modify "${connection}" ipv4.route-metric "${WIFI_UPLINK_METRIC}" ipv6.route-metric "${WIFI_UPLINK_METRIC}"
  fi
fi

echo "Configured uplink metrics: ${ETH_IFACE}=${ETH_METRIC}, ${WIFI_UPLINK_IFACE}=${WIFI_UPLINK_METRIC}."
