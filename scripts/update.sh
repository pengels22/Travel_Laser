#!/usr/bin/env bash
set -euo pipefail

if [[ ! -d .git ]]; then
  cat >&2 <<'EOF'
This directory is not a git checkout, so it cannot be updated with git pull.

/opt/travel-laser-controller is normally an installed copy created by
scripts/install.sh. Update from a real checkout or transfer the repository to
the Orange Pi first, then run:

  sudo ./scripts/install.sh
  sudo ./scripts/deploy.sh --check
  sudo ./scripts/deploy.sh

EOF
  exit 2
fi

git pull --ff-only
.venv/bin/python -m pip install -e .
sudo systemctl restart travel-laser-controller.service
sudo systemctl status --no-pager travel-laser-controller.service
