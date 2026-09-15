#!/usr/bin/env bash
set -euo pipefail

git pull --ff-only
.venv/bin/python -m pip install -e .
sudo systemctl restart travel-laser-controller.service
sudo systemctl status --no-pager travel-laser-controller.service
