#!/usr/bin/env bash
set -euo pipefail

DEVICE_NAME="${1:-}"
MIN_BYTES="${TRAVEL_LASER_LOG_EXPORT_MIN_BYTES:-209715200}"
LOG_SOURCE="${TRAVEL_LASER_LOG_SOURCE:-/var/log/travel-laser}"
EXPORT_ROOT_NAME="${TRAVEL_LASER_LOG_EXPORT_DIR:-Travel-Laser-Logs}"
MOUNT_ROOT="${TRAVEL_LASER_USB_MOUNT_ROOT:-/run/travel-laser-usb-export}"
SERVICES=(
  travel-laser-controller.service
  travel-laser-ui.service
  travel-laser-camera.service
  mediamtx.service
)

if [[ -z "${DEVICE_NAME}" ]]; then
  echo "Usage: $0 <block-device-name>" >&2
  exit 2
fi

DEVICE="/dev/${DEVICE_NAME}"
if [[ ! -b "${DEVICE}" ]]; then
  echo "Skipping ${DEVICE}: not a block device" >&2
  exit 0
fi

SIZE_BYTES="$(blockdev --getsize64 "${DEVICE}" 2>/dev/null || echo 0)"
if (( SIZE_BYTES < MIN_BYTES )); then
  echo "Skipping ${DEVICE}: ${SIZE_BYTES} bytes is below ${MIN_BYTES}" >&2
  exit 0
fi

MOUNTED_BY_SCRIPT=0
MOUNT_POINT="$(findmnt -nr -S "${DEVICE}" -o TARGET | head -n 1 || true)"
if [[ -z "${MOUNT_POINT}" ]]; then
  MOUNT_POINT="${MOUNT_ROOT}/${DEVICE_NAME}"
  mkdir -p "${MOUNT_POINT}"
  mount -o rw,sync "${DEVICE}" "${MOUNT_POINT}"
  MOUNTED_BY_SCRIPT=1
fi

HOST="$(hostname 2>/dev/null || echo Travel-Laser)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="${MOUNT_POINT}/${EXPORT_ROOT_NAME}/${HOST}-${STAMP}"
mkdir -p "${DEST}"

if [[ -d "${LOG_SOURCE}" ]]; then
  rsync -a --ignore-missing-args "${LOG_SOURCE}/" "${DEST}/travel-laser-log-dir/"
fi

if [[ -f "${LOG_SOURCE}/events.jsonl" ]]; then
  cp "${LOG_SOURCE}/events.jsonl" "${DEST}/events.jsonl"
fi

for service in "${SERVICES[@]}"; do
  journalctl -u "${service}" --no-pager -n 2000 > "${DEST}/${service}.journal.log" 2>/dev/null || true
done

cat > "${DEST}/manifest.txt" <<EOF
Travel-Laser log export
Device: ${DEVICE}
UTC: ${STAMP}
Minimum size bytes: ${MIN_BYTES}
Device size bytes: ${SIZE_BYTES}
EOF

sync "${MOUNT_POINT}" || true
echo "Exported Travel-Laser logs to ${DEST}"

if (( MOUNTED_BY_SCRIPT == 1 )); then
  umount "${MOUNT_POINT}"
  rmdir "${MOUNT_POINT}" 2>/dev/null || true
fi
