#!/usr/bin/env bash
set -euo pipefail

ARCH="$(uname -m)"
case "${ARCH}" in
  aarch64|arm64) ASSET_PATTERN='linux_arm64.*tar.gz' ;;
  armv7l|armhf) ASSET_PATTERN='linux_armv7.*tar.gz|linux_armv6.*tar.gz' ;;
  *) echo "Unsupported MediaMTX architecture: ${ARCH}" >&2; exit 1 ;;
esac

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

URL="$(curl -fsSL https://api.github.com/repos/bluenviron/mediamtx/releases/latest \
  | jq -r '.assets[].browser_download_url' \
  | grep -E "${ASSET_PATTERN}" \
  | head -n 1)"

if [[ -z "${URL}" ]]; then
  echo "Could not find a matching MediaMTX release asset." >&2
  exit 1
fi

curl -fL "${URL}" -o "${TMP_DIR}/mediamtx.tar.gz"
tar -xzf "${TMP_DIR}/mediamtx.tar.gz" -C "${TMP_DIR}"
install -m 0755 "${TMP_DIR}/mediamtx" /usr/local/bin/mediamtx
install -d /etc/travel-laser
install -m 0644 config/mediamtx.example.yml /etc/travel-laser/mediamtx.yml

echo "Installed MediaMTX from ${URL}"
