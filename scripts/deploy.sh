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
  echo "Created ${DEPLOY_ENV}. Fill the hardware values, then rerun: sudo ${SOURCE_DIR}/scripts/deploy.sh" >&2
  exit 2
fi

PYTHON_BIN="${APP_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

if command -v tailscale >/dev/null 2>&1 && ! grep -Eq '^TRAVEL_LASER_TAILSCALE_IP=.+' "${DEPLOY_ENV}"; then
  TAILSCALE_IP="$(tailscale ip -4 2>/dev/null | head -n 1 || true)"
  if [[ -n "${TAILSCALE_IP}" ]]; then
    sed -i "s/^TRAVEL_LASER_TAILSCALE_IP=.*/TRAVEL_LASER_TAILSCALE_IP=${TAILSCALE_IP}/" "${DEPLOY_ENV}"
    echo "Filled TRAVEL_LASER_TAILSCALE_IP=${TAILSCALE_IP}"
  fi
fi

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
