# Install

Deployment scaffolding is in `scripts/install.sh` and `systemd/`.

The install script is intended for an Orange Pi, not for development Macs. It creates config/state/log directories, installs Python/system packages, installs MediaMTX, installs service units, and does not overwrite an existing controller config.

VirtualHere is expected to be installed on the Orange Pi, but configured separately.

Deployment hostname should be set to `Travel-Laser`.
The install script runs `hostnamectl set-hostname Travel-Laser`.

Core packages installed by `scripts/install.sh`:

```bash
apt-get install -y curl ffmpeg git gpiod jq libgpiod-dev network-manager python3-dev python3-libgpiod python3-pip python3-venv rsync v4l-utils
```

Service units installed:

- `ts1-controller.service`
- `mediamtx.service`
- `ts1-camera.service`

The controller service runs as `ts1-controller` and uses `CAP_NET_BIND_SERVICE` so it can bind GRBL TCP port `23` without running as root.
