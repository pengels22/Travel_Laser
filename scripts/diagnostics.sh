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
ls -l /dev/serial/by-id 2>/dev/null || true
ls -l /dev/video* 2>/dev/null || true

echo "== mode =="
cat /var/lib/ts1-controller/mode.json 2>/dev/null || true

