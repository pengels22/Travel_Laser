#!/usr/bin/env bash
set -euo pipefail

DEVICE="${CAMERA_DEVICE:-/dev/video0}"
STREAM_NAME="${CAMERA_STREAM_NAME:-cam}"
FPS="${CAMERA_FPS:-30}"
RESOLUTION="${CAMERA_RESOLUTION:-highest_available}"
RTSP_URL="${CAMERA_RTSP_URL:-rtsp://127.0.0.1:8554/${STREAM_NAME}}"

if [[ "${RESOLUTION}" == "highest_available" ]]; then
  RESOLUTION="$(scripts/select-camera-mode.sh "${DEVICE}")"
fi

WIDTH="${RESOLUTION%x*}"
HEIGHT="${RESOLUTION#*x}"

exec ffmpeg \
  -f v4l2 \
  -framerate "${FPS}" \
  -video_size "${WIDTH}x${HEIGHT}" \
  -i "${DEVICE}" \
  -an \
  -c:v libx264 \
  -preset ultrafast \
  -tune zerolatency \
  -pix_fmt yuv420p \
  -f rtsp \
  "${RTSP_URL}"
