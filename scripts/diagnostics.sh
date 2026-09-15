#!/usr/bin/env bash
set -euo pipefail

echo "== ts1-controller service =="
systemctl status --no-pager ts1-controller.service || true

echo "== recent journal =="
journalctl -u ts1-controller.service -n 80 --no-pager || true

echo "== ip addresses =="
ip addr || ifconfig || true

echo "== tailscale =="
tailscale status || true

echo "== usb =="
lsusb || true
v4l2-ctl --list-devices || true
ls -l /dev/serial/by-id 2>/dev/null || true
ls -l /dev/video* 2>/dev/null || true

echo "== camera formats =="
for dev in /dev/video*; do
  [[ -e "${dev}" ]] || continue
  echo "-- ${dev}"
  v4l2-ctl --device="${dev}" --list-formats-ext || true
done

echo "== mode =="
cat /var/lib/ts1-controller/mode.json 2>/dev/null || true
