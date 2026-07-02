import pytest

import hotkey_daemon
from translator import TranslationError


def test_capture_selection_copies_then_reads_clipboard(monkeypatch):
    calls = []
    monkeypatch.setattr(hotkey_daemon.pyperclip, "copy", lambda text: calls.append(("copy", text)))
    monkeypatch.setattr(hotkey_daemon.pyperclip, "paste", lambda: "selected text")
    monkeypatch.setattr(hotkey_daemon.keyboard, "send", lambda combo: calls.append(("send", combo)))
    monkeypatch.setattr(hotkey_daemon.time, "sleep", lambda seconds: None)

    result = hotkey_daemon.capture_selection()

    assert result == "selected text"
    assert calls[0] == ("copy", "")
    assert calls[1] == ("send", "ctrl+c")


def test_apply_output_replace_mode(monkeypatch):
    calls = []
    monkeypatch.setattr(hotkey_daemon.pyperclip, "copy", lambda text: calls.append(("copy", text)))
    monkeypatch.setattr(hotkey_daemon.keyboard, "send", lambda combo: calls.append(("send", combo)))

    hotkey_daemon.apply_output("original", "translated", "replace")

    assert calls == [("copy", "translated"), ("send", "ctrl+v")]


def test_apply_output_append_mode(monkeypatch):
    calls = []
    monkeypatch.setattr(hotkey_daemon.pyperclip, "copy", lambda text: calls.append(("copy", text)))
    monkeypatch.setattr(hotkey_daemon.keyboard, "send", lambda combo: calls.append(("send", combo)))

    hotkey_daemon.apply_output("original", "translated", "append")

    assert calls == [("copy", "original\ntranslated"), ("send", "ctrl+v")]


def test_apply_output_popup_mode(monkeypatch):
    popup_calls = []
    monkeypatch.setattr(hotkey_daemon, "_show_popup", lambda text: popup_calls.append(text))

    hotkey_daemon.apply_output("original", "translated", "popup")

    assert popup_calls == ["translated"]


def test_apply_output_unknown_mode_raises():
    with pytest.raises(ValueError):
        hotkey_daemon.apply_output("original", "translated", "bogus")


def test_on_hotkey_no_selection_notifies_and_skips(monkeypatch):
    monkeypatch.setattr(hotkey_daemon, "capture_selection", lambda: "   ")
    monkeypatch.setattr(
        hotkey_daemon,
        "translate",
        lambda *a, **k: pytest.fail("translate should not be called when there is no selection"),
    )
    notify_calls = []
    monkeypatch.setattr(hotkey_daemon, "_notify_error", lambda msg: notify_calls.append(msg))
    apply_calls = []
    monkeypatch.setattr(hotkey_daemon, "apply_output", lambda *a, **k: apply_calls.append((a, k)))

    hotkey_daemon.on_hotkey({"output_mode": "replace"})

    assert len(notify_calls) == 1
    assert apply_calls == []


def test_on_hotkey_success_applies_output(monkeypatch):
    monkeypatch.setattr(hotkey_daemon, "capture_selection", lambda: "hello")
    monkeypatch.setattr(hotkey_daemon, "translate", lambda text, config=None: "你好")
    apply_calls = []
    monkeypatch.setattr(hotkey_daemon, "apply_output", lambda *a, **k: apply_calls.append(a))

    hotkey_daemon.on_hotkey({"output_mode": "append"})

    assert apply_calls == [("hello", "你好", "append")]


def test_on_hotkey_translation_error_notifies(monkeypatch):
    monkeypatch.setattr(hotkey_daemon, "capture_selection", lambda: "hello")

    def raise_error(text, config=None):
        raise TranslationError("no network")

    monkeypatch.setattr(hotkey_daemon, "translate", raise_error)
    notify_calls = []
    monkeypatch.setattr(hotkey_daemon, "_notify_error", lambda msg: notify_calls.append(msg))
    apply_calls = []
    monkeypatch.setattr(hotkey_daemon, "apply_output", lambda *a, **k: apply_calls.append(a))

    hotkey_daemon.on_hotkey({"output_mode": "replace"})

    assert notify_calls == ["no network"]
    assert apply_calls == []


def test_on_hotkey_unexpected_error_notifies(monkeypatch):
    monkeypatch.setattr(hotkey_daemon, "capture_selection", lambda: "hello")

    def raise_error(text, config=None):
        raise ValueError("bad default_pair")

    monkeypatch.setattr(hotkey_daemon, "translate", raise_error)
    notify_calls = []
    monkeypatch.setattr(hotkey_daemon, "_notify_error", lambda msg: notify_calls.append(msg))
    apply_calls = []
    monkeypatch.setattr(hotkey_daemon, "apply_output", lambda *a, **k: apply_calls.append(a))

    hotkey_daemon.on_hotkey({"output_mode": "replace"})

    assert notify_calls == ["bad default_pair"]
    assert apply_calls == []
