# Install

Deployment scaffolding is in `scripts/deploy.sh`, `scripts/install.sh`, and `systemd/`.

The deploy and install scripts are intended for an Orange Pi, not for development Macs. The deploy script runs the installer, creates config/state/log directories, installs Python/system packages, installs MediaMTX, installs service units, applies hardware placeholders, configures network metrics, and starts services only after required placeholders are set.

First run:

```bash
sudo scripts/deploy.sh
```

If `/etc/travel-laser/deployment.env` does not exist, the script creates it from `config/deployment.env.example` and stops. Fill the values listed in `docs/PLACEHOLDERS.md`, then rerun:

```bash
sudo /opt/travel-laser-controller/scripts/deploy.sh
```

VirtualHere is expected to be installed on the Orange Pi, but configured separately.

Deployment hostname should be set to `Travel-Laser`.
The install script runs `hostnamectl set-hostname Travel-Laser`.

Core packages installed by `scripts/install.sh`:

```bash
apt-get install -y curl ffmpeg git gpiod i2c-tools jq libgpiod-dev network-manager python3-dev python3-libgpiod python3-pip python3-smbus python3-venv rsync v4l-utils
```

Service units installed:

- `travel-laser-controller.service`
- `mediamtx.service`
- `travel-laser-camera.service`
- `travel-laser-ui.service`
- `travel-laser-log-export@.service`

The controller service runs as `travel-laser` and uses `CAP_NET_BIND_SERVICE` so it can bind GRBL TCP port `23` without running as root.

The installer also installs `/etc/udev/rules.d/99-travel-laser-log-export.rules`. When a filesystem USB partition appears, udev starts the log export service. The export script ignores drives smaller than 200 MB.
