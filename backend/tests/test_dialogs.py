from backend.application.dialogs import DialogKind, DialogState, TextEntryState, keyboard_key_text


def test_confirmation_dialog_is_modal() -> None:
    dialog = DialogState(DialogKind.CONFIRMATION, "Reboot", "Reboot Travel Laser?", command="/system/reboot")
    assert dialog.modal is True
    assert dialog.command == "/system/reboot"


def test_text_entry_supports_masking_shift_backspace_and_clear() -> None:
    entry = TextEntryState(prompt="Wi-Fi password")
    entry.insert("ab")
    entry.shift_enabled = True
    entry.insert(keyboard_key_text("c", entry))
    entry.backspace()
    assert entry.value == "ab"
    assert entry.display_value() == "**"
    entry.clear()
    assert entry.value == ""
