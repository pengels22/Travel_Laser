#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
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
    print(f"display: {config.display.controller} {config.display.width}x{config.display.height} rotation={config.display.rotation}")
    print(f"display spi_device: {config.display.spi_device}")
    print(f"display dc/reset/backlight: {config.display.dc_gpio_line}/{config.display.reset_gpio_line}/{config.display.backlight_gpio_line}")
    print(f"touch: {config.touch.controller} bus={config.touch.i2c_bus} address=0x{config.touch.i2c_address:02x}")
    print(f"touch reset/optional interrupt: {config.touch.reset_gpio_line}/{config.touch.interrupt_gpio_line}")
    print("SPI devices:")
    for item in sorted(glob.glob("/dev/spidev*")):
        print(f"  {item}")
    print("I2C buses:")
    for item in sorted(glob.glob("/dev/i2c-*")):
        print(f"  {item}")
    _run("gpioinfo")
    _run("i2cdetect", "-l")


def _run(*cmd: str) -> None:
    print(f"\n$ {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=False)
    except OSError as exc:
        print(f"  unavailable: {exc}")


if __name__ == "__main__":
    main()
