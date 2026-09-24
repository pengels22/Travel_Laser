#!/usr/bin/env bash
set -euo pipefail

ARMBIAN_ENV="/boot/armbianEnv.txt"
OVERLAY_DIR="/boot/overlay-user"
OVERLAY_NAME="spi1-cs1-pins"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DTS_SOURCE="${SOURCE_DIR}/hardware/overlays/${OVERLAY_NAME}.dts"
DTBO_TARGET="${OVERLAY_DIR}/${OVERLAY_NAME}.dtbo"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root." >&2
  exit 1
fi

if [[ ! -f "${ARMBIAN_ENV}" ]]; then
  echo "${ARMBIAN_ENV} not found; this helper is for Armbian." >&2
  exit 1
fi

if [[ ! -f "${DTS_SOURCE}" ]]; then
  echo "Missing overlay source: ${DTS_SOURCE}" >&2
  exit 1
fi

command -v dtc >/dev/null 2>&1 || {
  echo "device-tree-compiler is required." >&2
  exit 1
}

backup="${ARMBIAN_ENV}.travel-laser.$(date +%Y%m%d-%H%M%S).bak"
cp "${ARMBIAN_ENV}" "${backup}"
echo "Backed up ${ARMBIAN_ENV} to ${backup}"

mkdir -p "${OVERLAY_DIR}"
dtc -@ -I dts -O dtb -o "${DTBO_TARGET}" "${DTS_SOURCE}"

python3 - "${ARMBIAN_ENV}" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
lines = path.read_text().splitlines()

def ensure_tokens(key: str, required: list[str]) -> None:
    global lines
    prefix = key + "="
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            tokens = line[len(prefix):].split()
            for token in required:
                if token not in tokens:
                    tokens.append(token)
            lines[i] = prefix + " ".join(tokens)
            return
    lines.append(prefix + " ".join(required))

ensure_tokens("overlays", ["i2c3-ph", "spidev1_1"])
ensure_tokens("user_overlays", ["spi1-cs1-pins"])

path.write_text("\n".join(lines) + "\n")
PY

echo
echo "Updated boot overlays:"
grep -E '^(overlays|user_overlays)=' "${ARMBIAN_ENV}"

echo
echo "Reboot is required before the changes take effect."
echo "After reboot verify:"
echo "  ls -l /dev/spidev1.1 /dev/i2c-2"
echo "  sudo grep -E 'PH6|PH7|PH8|PH9' /sys/kernel/debug/pinctrl/300b000.pinctrl/pinmux-pins"
