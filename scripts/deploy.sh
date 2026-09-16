#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${APP_DIR:-/opt/travel-laser-controller}"
CONFIG_DIR="${CONFIG_DIR:-/etc/travel-laser}"
DEPLOY_ENV="${DEPLOY_ENV:-${CONFIG_DIR}/deployment.env}"
CONTROLLER_CONFIG="${CONTROLLER_CONFIG:-${CONFIG_DIR}/controller.yaml}"
START_SERVICES="${START_SERVICES:-true}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this deploy script as root on the Orange Pi." >&2
  exit 1
fi

mkdir -p "${CONFIG_DIR}"

if [[ "${SOURCE_DIR}" != "${APP_DIR}" ]]; then
  "${SOURCE_DIR}/scripts/install.sh"
else
  echo "Running from ${APP_DIR}; skipping install sync step."
fi

if [[ ! -f "${DEPLOY_ENV}" ]]; then
  cp "${SOURCE_DIR}/config/deployment.env.example" "${DEPLOY_ENV}"
  chmod 600 "${DEPLOY_ENV}"
  echo "Created ${DEPLOY_ENV}."
fi

PYTHON_BIN="${APP_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

env_has_value() {
  local key="$1"
  grep -Eq "^${key}=.+" "${DEPLOY_ENV}"
}

set_env_value() {
  local key="$1"
  local value="$2"
  local escaped_value
  escaped_value="$(printf '%s' "${value}" | sed 's/[&|\\]/\\&/g')"
  if grep -Eq "^${key}=" "${DEPLOY_ENV}"; then
    sed -i "s|^${key}=.*|${key}=${escaped_value}|" "${DEPLOY_ENV}"
  else
    printf '%s=%s\n' "${key}" "${value}" >> "${DEPLOY_ENV}"
  fi
}

udev_property() {
  local dev="$1"
  local key="$2"
  udevadm info --query=property --name="${dev}" 2>/dev/null |
    awk -F= -v wanted="${key}" '$1 == wanted {print $2; exit}'
}

auto_fill_tailscale_ip() {
  env_has_value TRAVEL_LASER_TAILSCALE_IP && return
  command -v tailscale >/dev/null 2>&1 || return
  local TAILSCALE_IP
  TAILSCALE_IP="$(tailscale ip -4 2>/dev/null | head -n 1 || true)"
  if [[ -n "${TAILSCALE_IP}" ]]; then
    set_env_value TRAVEL_LASER_TAILSCALE_IP "${TAILSCALE_IP}"
    echo "Filled TRAVEL_LASER_TAILSCALE_IP=${TAILSCALE_IP}"
  fi
}

auto_fill_camera_device() {
  env_has_value CAMERA_DEVICE && return
  local -a cameras
  mapfile -t cameras < <(find /dev/v4l/by-id -maxdepth 1 -type l 2>/dev/null | sort)
  if [[ "${#cameras[@]}" -eq 1 ]]; then
    set_env_value CAMERA_DEVICE "${cameras[0]}"
    echo "Filled CAMERA_DEVICE=${cameras[0]}"
  elif [[ "${#cameras[@]}" -gt 1 ]]; then
    echo "Multiple camera candidates found; choose CAMERA_DEVICE manually in ${DEPLOY_ENV}:"
    printf '  %s\n' "${cameras[@]}"
  fi
}

auto_fill_laser_usb_identity() {
  if env_has_value LASER_USB_VID || env_has_value LASER_USB_PID || env_has_value LASER_USB_SERIAL || env_has_value LASER_USB_DESCRIPTION; then
    return
  fi
  local dev vid pid serial
  local -a serials
  mapfile -t serials < <(find /dev/serial/by-id -maxdepth 1 -type l 2>/dev/null | sort)
  if [[ "${#serials[@]}" -eq 1 ]]; then
    dev="${serials[0]}"
    vid="$(udev_property "${dev}" ID_VENDOR_ID)"
    pid="$(udev_property "${dev}" ID_MODEL_ID)"
    serial="$(udev_property "${dev}" ID_SERIAL_SHORT)"
    [[ -n "${vid}" ]] && set_env_value LASER_USB_VID "${vid}"
    [[ -n "${pid}" ]] && set_env_value LASER_USB_PID "${pid}"
    [[ -n "${serial}" ]] && set_env_value LASER_USB_SERIAL "${serial}"
    echo "Filled laser USB identity from ${dev}"
  elif [[ "${#serials[@]}" -gt 1 ]]; then
    echo "Multiple serial candidates found; choose laser USB identity manually in ${DEPLOY_ENV}:"
    printf '  %s\n' "${serials[@]}"
  fi
}

auto_fill_tailscale_ip
auto_fill_camera_device
auto_fill_laser_usb_identity

"${PYTHON_BIN}" "${SOURCE_DIR}/scripts/apply-placeholders.py" --env "${DEPLOY_ENV}" --config "${CONTROLLER_CONFIG}"

set -a
# shellcheck disable=SC1090
source "${DEPLOY_ENV}"
set +a

ETH_IFACE="${ETH_IFACE:-eth0}" \
ETH_METRIC="${ETH_METRIC:-100}" \
WIFI_UPLINK_IFACE="${WIFI_UPLINK_IFACE:-wlan1}" \
WIFI_UPLINK_METRIC="${WIFI_UPLINK_METRIC:-300}" \
  "${SOURCE_DIR}/scripts/configure-network.sh"

systemctl daemon-reload
if [[ "${START_SERVICES}" == "true" ]]; then
  systemctl enable --now mediamtx.service
  systemctl enable --now travel-laser-camera.service
  systemctl enable --now travel-laser-controller.service
  systemctl enable --now travel-laser-ui.service
  systemctl status --no-pager travel-laser-controller.service
else
  echo "START_SERVICES is not true; services were installed but not started."
fi
