#!/usr/bin/env bash
set -euo pipefail

echo "== lsusb =="
lsusb || true

echo "== serial devices =="
ls -l /dev/serial/by-id 2>/dev/null || true

echo "== video devices =="
v4l2-ctl --list-devices || true
ls -l /dev/video* 2>/dev/null || true

echo "== udev properties: ttyUSB/ttyACM =="
for dev in /dev/ttyUSB* /dev/ttyACM*; do
  [[ -e "${dev}" ]] || continue
  echo "-- ${dev}"
  udevadm info --query=property --name="${dev}" || true
done

echo "== udev properties: video =="
for dev in /dev/video*; do
  [[ -e "${dev}" ]] || continue
  echo "-- ${dev}"
  udevadm info --query=property --name="${dev}" || true
done
