# Install

First-pass deployment scaffolding is in `scripts/install.sh` and `systemd/`.

The install script is intended for an Orange Pi, not for development Macs. It creates config/state/log directories, installs the service unit, and does not overwrite an existing controller config.

