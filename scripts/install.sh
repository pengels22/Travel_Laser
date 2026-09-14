#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/ts1-laser-controller"
CONFIG_DIR="/etc/ts1-controller"
STATE_DIR="/var/lib/ts1-controller"
LOG_DIR="/var/log/ts1-controller"
SERVICE_USER="ts1-controller"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer as root on the Orange Pi." >&2
  exit 1
fi

id "${SERVICE_USER}" >/dev/null 2>&1 || useradd --system --home "${STATE_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}"
mkdir -p "${CONFIG_DIR}" "${STATE_DIR}" "${LOG_DIR}" "${APP_DIR}"
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${STATE_DIR}" "${LOG_DIR}"

if [[ ! -f "${CONFIG_DIR}/controller.yaml" ]]; then
  cp config/controller.example.yaml "${CONFIG_DIR}/controller.yaml"
  echo "Created ${CONFIG_DIR}/controller.yaml"
else
  echo "Keeping existing ${CONFIG_DIR}/controller.yaml"
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .

cp systemd/ts1-controller.service /etc/systemd/system/ts1-controller.service
cp systemd/ts1-camera.service /etc/systemd/system/ts1-camera.service
systemctl daemon-reload
systemctl enable ts1-controller.service

echo "Install complete. Review ${CONFIG_DIR}/controller.yaml before starting the service."

