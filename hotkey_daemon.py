import ctypes
import time

import keyboard
import pyperclip


def capture_selection(paste_delay: float = 0.15) -> str:
    pyperclip.copy("")
    keyboard.send("ctrl+c")
    time.sleep(paste_delay)
    return pyperclip.paste()


def apply_output(original: str, translation: str, output_mode: str) -> None:
    if output_mode == "replace":
        pyperclip.copy(translation)
        keyboard.send("ctrl+v")
    elif output_mode == "append":
        pyperclip.copy(f"{original}\n{translation}")
        keyboard.send("ctrl+v")
    elif output_mode == "popup":
        _show_popup(translation)
    else:
        raise ValueError(f"Unknown output_mode: {output_mode}")


def _show_popup(text: str) -> None:
    ctypes.windll.user32.MessageBoxW(0, text, "Translation", 0)


def _notify_error(message: str) -> None:
    ctypes.windll.user32.MessageBoxW(0, message, "Translation Error", 0x10)


from translator import translate, TranslationError, load_config


def on_hotkey(config: dict) -> None:
    original = capture_selection()
    if not original.strip():
        _notify_error("No text detected. Select text before pressing the hotkey.")
        return
    try:
        translation = translate(original, config=config)
    except TranslationError as e:
        _notify_error(str(e))
        return
    apply_output(original, translation, config.get("output_mode", "replace"))


def main() -> None:
    config = load_config()
    hotkey = config.get("hotkey", "ctrl+alt+t")
    keyboard.add_hotkey(hotkey, lambda: on_hotkey(config))
    print(f"Listening for {hotkey}. Press Ctrl+C in this terminal to quit.")
    keyboard.wait()


if __name__ == "__main__":
    main()
