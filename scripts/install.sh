#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/ts1-laser-controller"
CONFIG_DIR="/etc/ts1-controller"
STATE_DIR="/var/lib/ts1-controller"
LOG_DIR="/var/log/ts1-controller"
SERVICE_USER="ts1-controller"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer as root on the Orange Pi." >&2
  exit 1
fi

id "${SERVICE_USER}" >/dev/null 2>&1 || useradd --system --home "${STATE_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}"
mkdir -p "${CONFIG_DIR}" "${STATE_DIR}" "${LOG_DIR}" "${APP_DIR}"
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${STATE_DIR}" "${LOG_DIR}"

apt-get update
apt-get install -y \
  curl \
  ffmpeg \
  git \
  gpiod \
  jq \
  libgpiod-dev \
  network-manager \
  python3-dev \
  python3-libgpiod \
  python3-pip \
  python3-venv \
  rsync \
  v4l-utils

hostnamectl set-hostname Travel-Laser

rsync -a --delete \
  --exclude .git \
  --exclude .venv \
  "${SOURCE_DIR}/" "${APP_DIR}/"
cd "${APP_DIR}"

usermod -aG dialout,video "${SERVICE_USER}"
if getent group gpio >/dev/null; then
  usermod -aG gpio "${SERVICE_USER}"
fi

if [[ ! -f "${CONFIG_DIR}/controller.yaml" ]]; then
  cp config/controller.example.yaml "${CONFIG_DIR}/controller.yaml"
  echo "Created ${CONFIG_DIR}/controller.yaml"
else
  echo "Keeping existing ${CONFIG_DIR}/controller.yaml"
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .

scripts/install-mediamtx.sh

cp systemd/ts1-controller.service /etc/systemd/system/ts1-controller.service
cp systemd/ts1-camera.service /etc/systemd/system/ts1-camera.service
cp systemd/mediamtx.service /etc/systemd/system/mediamtx.service
systemctl daemon-reload
systemctl enable ts1-controller.service
systemctl enable mediamtx.service
systemctl enable ts1-camera.service

echo "Install complete. Review ${CONFIG_DIR}/controller.yaml before starting the service."
