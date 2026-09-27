# Deployment Placeholders

The display/touch bus assignments below are no longer placeholders on the validated Orange Pi Zero 3 installation.

Validated hardware values:

- SPI display: `/dev/spidev1.1`
- I2C touch: `/dev/i2c-2`
- Main H618 GPIO controller: `/dev/gpiochip1`
- Ethernet interface: `end0`
- Wi-Fi interface: `wlan0`

The remaining deployment-specific values still depend on the laser controller, camera, Tailscale assignment, and VirtualHere installation.

Run:

```bash
sudo /opt/travel-laser-controller/scripts/deploy.sh
```

The script creates `/etc/travel-laser/deployment.env` if needed, fills values it can identify safely, then applies them to `/etc/travel-laser/controller.yaml`.

## Usually Auto-Filled

| Env key | What deploy does | When it still needs help |
| --- | --- | --- |
| `TRAVEL_LASER_TAILSCALE_IP` | Uses `tailscale ip -4` when available. | Tailscale is not configured yet. |
| `CAMERA_DEVICE` | Uses the only `/dev/v4l/by-id/...` camera when exactly one exists. | More than one camera is present. |
| `LASER_USB_VID` / `LASER_USB_PID` / `LASER_USB_SERIAL` | Uses udev properties from the only `/dev/serial/by-id/...` device. | More than one serial device exists. |

## Hardware Values Already Validated

| Env key | Validated value |
| --- | --- |
| `DISPLAY_SPI_DEVICE` | `/dev/spidev1.1` |
| `TOUCH_I2C_BUS` | `2` |
| `ETH_IFACE` | `end0` |
| `WIFI_UPLINK_IFACE` | `wlan0` |

The ST7796U was validated at 10 MHz in 480x320 landscape mode with display inversion enabled. The FT6336U responds at address `0x38` and uses the landscape transform `x = raw_y`, `y = 319 - raw_x`.

## Touch Interrupt

CTP_INT is not used on this build. The FT6336U backend polls I2C, so the production configuration leaves the touch interrupt GPIO unset. PC8/GPIO72 remains dedicated to K1.

## Display Reset

LCD_RST is physically connected to PC9/GPIO73, but the running Orange Pi Zero 3 kernel reserves PC9 for the PMIC interrupt. The validated panel operates correctly without userspace control of LCD_RST, so production config leaves the LCD reset GPIO unset.

## Validation Rule

Before enabling services, confirm:

- Tailscale IP is known if Tailscale-only web binding is enabled;
- the camera path is identified;
- at least one laser USB identity value is known;
- `/dev/spidev1.1` exists;
- `/dev/i2c-2` exists and device `0x38` responds;
- `/dev/gpiochip1` is present.

Do not store passwords, keys, tokens, or other secrets in the deployment env file committed to Git.

## Runtime Status

Implemented in software: stable USB identity matching, laser USB disconnect/reconnect state handling, camera presence reporting, live diagnostics, touchscreen network controls, live Tailscale status, explicit fault reset, narrow privileged system actions, privileged USB log export, deploy preflight, and VirtualHere active-service verification.

Still deployment-specific: laser VID/PID/serial or description, camera identity/path, optional camera stream URL, current Tailscale address when binding the external portal, and the VirtualHere service name if VirtualHere mode is enabled.

Still pending physical deployment validation: real laser USB/GRBL reconnect on the Orange Pi, camera stream behavior, restart/reboot/shutdown helper invocation under systemd, USB log export from an actual flash drive, and VirtualHere ownership handoff. Fire hardware is not present; `fire.enabled=false` and `fire.sensor_enabled=false` mean fire trips are not accepted.
