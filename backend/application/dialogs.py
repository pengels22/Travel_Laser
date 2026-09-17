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
    masked: bool = True
    cursor_position: int = 0
    shift_enabled: bool = False
    max_length: int = 128
    prompt: str = ""

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


KEYBOARD_ROWS = (
    tuple("1234567890"),
    tuple("qwertyuiop"),
    tuple("asdfghjkl"),
    tuple("zxcvbnm"),
    tuple("!@#$%^&*()-_=+[]{};:'\",./?\\|"),
)


def keyboard_key_text(key: str, entry: TextEntryState) -> str:
    if len(key) == 1 and key.isalpha() and entry.shift_enabled:
        return key.upper()
    return key
