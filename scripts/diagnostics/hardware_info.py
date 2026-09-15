#!/usr/bin/env python3
from __future__ import annotations

import glob
import subprocess
from pathlib import Path

from backend.config import load_config


def main() -> None:
    config = load_config(Path("config/controller.example.yaml"))
    print("Travel Laser hardware info")
    print(f"display: {config.display.controller} {config.display.width}x{config.display.height} rotation={config.display.rotation}")
    print(f"display spi_device: {config.display.spi_device}")
    print(f"touch: {config.touch.controller} bus={config.touch.i2c_bus} address=0x{config.touch.i2c_address:02x}")
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
    except FileNotFoundError:
        print("  command not found")


if __name__ == "__main__":
    main()

