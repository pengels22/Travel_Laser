#!/usr/bin/env bash
set -euo pipefail

git pull --ff-only
.venv/bin/python -m pip install -e .
sudo systemctl restart ts1-controller.service
sudo systemctl status --no-pager ts1-controller.service

