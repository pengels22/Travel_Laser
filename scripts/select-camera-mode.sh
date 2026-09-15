#!/usr/bin/env bash
set -euo pipefail

DEVICE="${1:-}"

if [[ -z "${DEVICE}" ]]; then
  echo "Usage: $0 /dev/v4l/by-id/<camera>" >&2
  exit 1
fi

v4l2-ctl --device="${DEVICE}" --list-formats-ext |
  awk '
    /Pixel Format/ { fmt=$0 }
    /Size: Discrete/ {
      split($3, parts, "x")
      width=parts[1]
      height=parts[2]
      area=width*height
      if (area > best_area) {
        best_area=area
        best_width=width
        best_height=height
        best_fmt=fmt
      }
    }
    END {
      if (best_area == 0) {
        exit 1
      }
      printf "%sx%s\n", best_width, best_height
    }'
