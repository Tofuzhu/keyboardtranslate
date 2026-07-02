import pytest

import hotkey_daemon


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
