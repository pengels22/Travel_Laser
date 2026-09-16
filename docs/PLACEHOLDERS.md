# Deployment Placeholders

These are the values that cannot be known until the Orange Pi, laser controller, camera, and Tailscale account are available.

Fill `/etc/travel-laser/deployment.env` on the Orange Pi, then rerun:

```bash
sudo /opt/travel-laser-controller/scripts/deploy.sh
```

The tracked template is `config/deployment.env.example`. The deploy script applies filled values to `/etc/travel-laser/controller.yaml` through `scripts/apply-placeholders.py`.

## Required Before Services Start

| Env key | Purpose | How to find it | Applied to |
| --- | --- | --- | --- |
| `TRAVEL_LASER_TAILSCALE_IP` | Web portal bind IP. The portal should listen only on Tailscale. | `tailscale ip -4` after joining the tailnet. `scripts/deploy.sh` tries to fill this automatically if Tailscale is already up. | `network.tailscale.ip_address`; web host resolver |
| `CAMERA_DEVICE` | Stable camera device path for FFmpeg. | `scripts/identify-usb.sh`, then choose a `/dev/v4l/by-id/...` camera path. | `travel-laser-camera.service` through `/etc/travel-laser/deployment.env` |
| One laser USB identity value | Lets the backend match the laser controller without assuming `/dev/ttyUSB0`. | `scripts/identify-usb.sh`; prefer VID/PID plus serial when available, otherwise use a descriptive fallback. | `laser.usb.*` |

At least one of these must be filled for laser USB identity:

- `LASER_USB_VID`
- `LASER_USB_PID`
- `LASER_USB_SERIAL`
- `LASER_USB_DESCRIPTION`

## Strongly Recommended

| Env key | Purpose | How to find it | Applied to |
| --- | --- | --- | --- |
| `CAMERA_USB_VID` / `CAMERA_USB_PID` / `CAMERA_USB_SERIAL` / `CAMERA_USB_DESCRIPTION` | Camera identity documentation and future device matching. | `scripts/identify-usb.sh` | `camera.usb.*` |
| `CAMERA_RESOLUTION` | Camera stream mode. | `scripts/select-camera-mode.sh /dev/v4l/by-id/<camera>` | `travel-laser-camera.service` |
| `CAMERA_STREAM_URL` | Explicit web portal camera URL, if the default `http://<host>:8889/cam` is not correct. | Confirm after MediaMTX is running. | `camera.stream_url` |

## Hardware Confirmation

| Env key | Current expected value | Notes |
| --- | --- | --- |
| `DISPLAY_SPI_DEVICE` | `/dev/spidev1.0` | Confirm after enabling SPI1 with board config tooling. |
| `TOUCH_I2C_BUS` | `3` | Confirm `/dev/i2c-3` exists after enabling I2C3. |
| `BACKLIGHT_GPIO_CHIP` / `BACKLIGHT_GPIO_LINE` | blank | Leave blank if the LCD backlight is tied on. Fill only if a GPIO controls backlight. |
| `VIRTUALHERE_SERVICE_NAME` | `virtualhere` | Confirm the real service name after VirtualHere is installed. |
| `VIRTUALHERE_BACKEND_CONTROLS_SERVICE` | `false` | Keep false unless we decide backend-controlled service switching is safe on deployed hardware. |

## Deployment Notes

- Do not put secrets or the filled deployment env file in git.
- The web portal will not fall back to `0.0.0.0` when `web.bind_to_tailscale: true`; missing `TRAVEL_LASER_TAILSCALE_IP` is a deployment blocker by design.
- The GRBL proxy still listens on TCP port `23` for LightBurn. That is separate from the web portal binding.
- Fire logic remains present but inactive by default because `fire.enabled` and `fire.sensor_enabled` are false.
