#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/travel-laser-controller"
CONFIG_DIR="/etc/travel-laser"
STATE_DIR="/var/lib/travel-laser"
LOG_DIR="/var/log/travel-laser"
SERVICE_USER="travel-laser"
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
  i2c-tools \
  libgpiod-dev \
  network-manager \
  python3-dev \
  python3-libgpiod \
  python3-smbus \
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
scripts/disable-power-services.sh

cp systemd/travel-laser-controller.service /etc/systemd/system/travel-laser-controller.service
cp systemd/travel-laser-camera.service /etc/systemd/system/travel-laser-camera.service
cp systemd/mediamtx.service /etc/systemd/system/mediamtx.service
cp systemd/travel-laser-ui.service /etc/systemd/system/travel-laser-ui.service
cp systemd/travel-laser-log-export@.service /etc/systemd/system/travel-laser-log-export@.service
cp systemd/99-travel-laser-log-export.rules /etc/udev/rules.d/99-travel-laser-log-export.rules
systemctl daemon-reload
udevadm control --reload-rules
systemctl enable travel-laser-controller.service
systemctl enable mediamtx.service
systemctl enable travel-laser-camera.service
systemctl enable travel-laser-ui.service

echo "Install complete. Review ${CONFIG_DIR}/controller.yaml before starting the service."
