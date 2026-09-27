from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DialogKind(str, Enum):
    CONFIRMATION = "confirmation"
    BUSY = "busy"
    SUCCESS = "success"
    ERROR = "error"
    KEYBOARD = "keyboard"


@dataclass
class DialogState:
    kind: DialogKind
    title: str
    message: str
    confirm_label: str = "OK"
    cancel_label: str = "Cancel"
    severity: str = "normal"
    command: str | None = None
    payload: dict[str, str] | None = None

    @property
    def modal(self) -> bool:
        return True


@dataclass
class TextEntryState:
    value: str = ""
    masked: bool = False
    cursor_position: int = 0
    keyboard_layout: str = "lower"
    max_length: int = 128
    prompt: str = ""

    @property
    def shift_enabled(self) -> bool:
        return self.keyboard_layout == "upper"

    @shift_enabled.setter
    def shift_enabled(self, enabled: bool) -> None:
        self.keyboard_layout = "upper" if enabled else "lower"

    def insert(self, text: str) -> None:
        if len(self.value) + len(text) > self.max_length:
            return
        self.value = self.value[: self.cursor_position] + text + self.value[self.cursor_position :]
        self.cursor_position += len(text)

    def backspace(self) -> None:
        if self.cursor_position:
            self.value = self.value[: self.cursor_position - 1] + self.value[self.cursor_position :]
            self.cursor_position -= 1

    def clear(self) -> None:
        self.value = ""
        self.cursor_position = 0

    def display_value(self) -> str:
        return "*" * len(self.value) if self.masked else self.value


KEYBOARD_LAYOUTS = {
    "lower": (
        tuple("qwertyuiop"),
        tuple("asdfghjkl"),
        tuple("zxcvbnm"),
    ),
    "upper": (
        tuple("QWERTYUIOP"),
        tuple("ASDFGHJKL"),
        tuple("ZXCVBNM"),
    ),
    "numbers": (
        tuple("1234567890"),
        tuple("-/:;()$&@\""),
        tuple(".,?!'"),
    ),
    "symbols": (
        tuple("[]{}#%^*+="),
        tuple("_\\|~<>"),
        tuple("`"),
    ),
}
KEYBOARD_ROWS = KEYBOARD_LAYOUTS["lower"]
KEYBOARD_LAYOUT_ORDER = tuple(KEYBOARD_LAYOUTS.keys())
KEYBOARD_LAYOUT_LABELS = {
    "lower": "abc",
    "upper": "ABC",
    "numbers": "123",
    "symbols": "#+=",
}


def keyboard_key_text(key: str, entry: TextEntryState) -> str:
    return key
