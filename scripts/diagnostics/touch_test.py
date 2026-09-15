#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from backend.config import load_config
from backend.input.ft6336_touch import FT6336Touch


async def main() -> None:
    parser = argparse.ArgumentParser(description="Travel Laser FT6336 touch diagnostic")
    parser.add_argument("--config", type=Path, default=Path("config/controller.example.yaml"))
    args = parser.parse_args()
    config = load_config(args.config)
    if config.touch.i2c_bus is None:
        raise SystemExit("touch.i2c_bus is not configured")
    touch = FT6336Touch(
        i2c_bus=config.touch.i2c_bus,
        address=config.touch.i2c_address,
        width=config.display.width,
        height=config.display.height,
        rotation=config.touch.rotation,
    )
    await touch.initialize()
    print("Touch test running. Press Ctrl+C to exit.")
    try:
        while True:
            event = await touch.read_event()
            if event:
                print(event)
    finally:
        await touch.close()


if __name__ == "__main__":
    asyncio.run(main())

