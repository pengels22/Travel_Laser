from __future__ import annotations

from pathlib import Path

from .interface import DisplayConfig


class DesktopDisplay:
    """Development display that writes the latest framebuffer to a PPM file."""

    def __init__(self, config: DisplayConfig, output: Path = Path(".state/display.ppm")) -> None:
        self.width = config.width
        self.height = config.height
        self.output = output
        self._buffer = bytearray(self.width * self.height * 2)

    async def initialize(self) -> None:
        self.output.parent.mkdir(parents=True, exist_ok=True)
        await self.clear()

    async def clear(self, color: int = 0x0000) -> None:
        pixel = color.to_bytes(2, "big")
        self._buffer[:] = pixel * (self.width * self.height)
        self._write_ppm()

    async def draw_rgb565(self, x: int, y: int, width: int, height: int, data: bytes) -> None:
        _check_bounds(self.width, self.height, x, y, width, height, data)
        for row in range(height):
            src_start = row * width * 2
            src_end = src_start + width * 2
            dst_start = ((y + row) * self.width + x) * 2
            self._buffer[dst_start : dst_start + width * 2] = data[src_start:src_end]
        self._write_ppm()

    async def close(self) -> None:
        self._write_ppm()

    def _write_ppm(self) -> None:
        with self.output.open("wb") as handle:
            handle.write(f"P6\n{self.width} {self.height}\n255\n".encode())
            for index in range(0, len(self._buffer), 2):
                value = int.from_bytes(self._buffer[index : index + 2], "big")
                red = ((value >> 11) & 0x1F) << 3
                green = ((value >> 5) & 0x3F) << 2
                blue = (value & 0x1F) << 3
                handle.write(bytes((red, green, blue)))


def _check_bounds(display_width: int, display_height: int, x: int, y: int, width: int, height: int, data: bytes) -> None:
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ValueError("invalid display rectangle")
    if x + width > display_width or y + height > display_height:
        raise ValueError("display update outside bounds")
    if len(data) != width * height * 2:
        raise ValueError("RGB565 data length does not match rectangle")

