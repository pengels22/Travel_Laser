#!/usr/bin/env bash
set -euo pipefail

# Keep networking/control services alive; trim optional peripherals and desktop-adjacent daemons.
# Missing units are ignored so the same script works across Armbian and Orange Pi OS images.

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root on the Orange Pi." >&2
  exit 1
fi

unit_exists() {
  local unit="$1"
  systemctl list-unit-files --full --no-legend "${unit}" 2>/dev/null | awk '{print $1}' | grep -qx "${unit}"
}

disable_unit() {
  local unit="$1"
  unit_exists "${unit}" || return 0
  systemctl disable --now "${unit}" >/dev/null 2>&1 || true
  echo "Disabled ${unit}"
}

mask_unit() {
  local unit="$1"
  unit_exists "${unit}" || return 0
  systemctl disable --now "${unit}" >/dev/null 2>&1 || true
  systemctl mask "${unit}" >/dev/null 2>&1 || true
  echo "Disabled and masked ${unit}"
}

BLUETOOTH_UNITS=(
  bluetooth.service
  hciuart.service
)

OPTIONAL_POWER_UNITS=(
  avahi-daemon.service
  avahi-daemon.socket
  brltty.service
  cups.service
  cups.socket
  cups-browsed.service
  ModemManager.service
)

for unit in "${BLUETOOTH_UNITS[@]}"; do
  mask_unit "${unit}"
done

for unit in "${OPTIONAL_POWER_UNITS[@]}"; do
  disable_unit "${unit}"
done

echo "Power-service cleanup complete. Networking services are left enabled."
