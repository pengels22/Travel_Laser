# Deployment Placeholders

These are the few values that still depend on the real Orange Pi, laser controller, camera, and Tailscale setup.

Run the deploy script on the Orange Pi:

```bash
sudo /opt/travel-laser-controller/scripts/deploy.sh
```

The script creates `/etc/travel-laser/deployment.env`, fills anything it can safely identify, and then applies the values to `/etc/travel-laser/controller.yaml`. If there are multiple possible devices, it prints the candidates and stops so the laser or camera is not guessed incorrectly.

The tracked template is `config/deployment.env.example`.

## Usually Auto-Filled By Deploy

| Env key | What deploy does | When it still needs help |
| --- | --- | --- |
| `TRAVEL_LASER_TAILSCALE_IP` | Uses `tailscale ip -4` when Tailscale is installed and logged in. | Tailscale is not set up yet. |
| `CAMERA_DEVICE` | Uses the only `/dev/v4l/by-id/...` camera path when exactly one camera is present. | More than one camera/video device is present. |
| `LASER_USB_VID` / `LASER_USB_PID` / `LASER_USB_SERIAL` | Uses udev properties from the only `/dev/serial/by-id/...` device when exactly one serial USB device is present. | More than one serial USB device is present, or the laser does not expose VID/PID/serial clearly. |

## <span style="color: #128a2e;">Manual Decision If Deploy Stops</span>

Green items are the ones you may need to decide manually after the hardware is plugged in.

| Env key | Why it may need a person | Good value |
| --- | --- | --- |
| <span style="color: #128a2e;">`LASER_USB_VID` / `LASER_USB_PID` / `LASER_USB_SERIAL` / `LASER_USB_DESCRIPTION`</span> | Needed when multiple serial USB devices exist. | Prefer VID/PID plus serial. Use `LASER_USB_DESCRIPTION` only as a fallback. |
| <span style="color: #128a2e;">`CAMERA_DEVICE`</span> | Needed when multiple camera/video devices exist. | A stable `/dev/v4l/by-id/...` path for the actual camera. |
| <span style="color: #128a2e;">`CAMERA_RESOLUTION`</span> | Defaults to `highest_available`; change only if the camera is unstable at the highest mode. | Keep `highest_available`, or use a mode from `scripts/select-camera-mode.sh`. |
| <span style="color: #128a2e;">`BACKLIGHT_GPIO_CHIP` / `BACKLIGHT_GPIO_LINE`</span> | Only needed if the LCD backlight is wired to a GPIO. | Leave blank if the backlight is tied on. |
| <span style="color: #128a2e;">`DISPLAY_SPI_DEVICE`</span> | Expected to be `/dev/spidev1.0`, but the OS image must confirm it after SPI1 is enabled. | The SPI1 device from `ls /dev/spidev*`. |
| <span style="color: #128a2e;">`TOUCH_I2C_BUS`</span> | Expected to be `3`, but the OS image must confirm it after I2C3 is enabled. | The I2C3 bus number from `i2cdetect -l`. |
| <span style="color: #128a2e;">`VIRTUALHERE_SERVICE_NAME`</span> | VirtualHere may install under a different service name. | The real systemd unit name after VirtualHere install. |
| <span style="color: #128a2e;">`VIRTUALHERE_BACKEND_CONTROLS_SERVICE`</span> | Determines whether the app starts/stops VirtualHere during mode changes. | Keep `false` unless service switching is verified safe. |

## Validation Rule

Before services start, these must be known:

- Tailscale IP for the web portal bind address.
- Stable camera device path.
- At least one laser USB identity value: VID, PID, serial, or description fallback.

## Deployment Notes

- Do not put secrets or the filled deployment env file in git.
- The web portal will not fall back to `0.0.0.0` when `web.bind_to_tailscale: true`; missing `TRAVEL_LASER_TAILSCALE_IP` is a deployment blocker by design.
- The GRBL proxy still listens on TCP port `23` for LightBurn. That is separate from the web portal binding.
- Network mode opens the matched laser USB device at `115200` baud. If the configured identity matches zero or multiple `/dev/serial/by-id/...` devices, the controller service stays failed until the identity is corrected.
- Automatic log export is limited to newly added USB filesystem partitions larger than 200 MB; internal disks and whole-disk udev events are ignored.
- Fire logic remains present but inactive by default because `fire.enabled` and `fire.sensor_enabled` are false.
