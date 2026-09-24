#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Travel Laser hardware inventory")
    parser.add_argument("--config", type=Path, default=Path("config/controller.example.yaml"))
    args = parser.parse_args()
    config = load_config(args.config)

    print("Travel Laser hardware info")
    print(
        f"display: {config.display.controller} "
        f"{config.display.width}x{config.display.height} "
        f"rotation={config.display.rotation}"
    )
    print(f"SPI device: {config.display.spi_device}")
    print(
        "Display GPIO: "
        f"LCD_DC={config.display.dc_gpio_chip}:{config.display.dc_gpio_line}, "
        f"LCD_RST={config.display.reset_gpio_chip}:{config.display.reset_gpio_line}, "
        f"backlight={config.display.backlight_gpio_chip}:{config.display.backlight_gpio_line}"
    )
    print(
        f"touch: {config.touch.controller} "
        f"I2C bus={config.touch.i2c_bus} "
        f"address=0x{config.touch.i2c_address:02x}"
    )
    print(
        "Touch GPIO: "
        f"CTP_RST={config.touch.reset_gpio_chip}:{config.touch.reset_gpio_line}, "
        f"CTP_INT={config.touch.interrupt_gpio_chip}:{config.touch.interrupt_gpio_line}"
    )

    print("\nSPI devices:")
    for item in sorted(glob.glob("/dev/spidev*")):
        print(f"  {item}")

    print("\nI2C buses:")
    for item in sorted(glob.glob("/dev/i2c-*")):
        print(f"  {item}")

    _run(_find_command("gpiodetect"))
    _run(_find_command("gpioinfo"), "-c", "gpiochip1")
    _run(_find_command("i2cdetect"), "-l")

    if config.touch.i2c_bus is not None:
        _run(_find_command("i2cdetect"), "-y", str(config.touch.i2c_bus))


def _find_command(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found

    for candidate in (f"/usr/sbin/{name}", f"/usr/bin/{name}"):
        if Path(candidate).exists():
            return candidate

    return name


def _run(*cmd: str) -> None:
    print(f"\n$ {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=False)
    except OSError as exc:
        print(f"  unavailable: {exc}")


if __name__ == "__main__":
    main()
