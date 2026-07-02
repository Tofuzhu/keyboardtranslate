# Keyboard Translate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an LLM-backed translation tool usable from any Windows input box, via espanso trigger words (`:tr` for default-pair auto-direction, `:cn`/`:en`/`:es` for explicit targets — each also matching the full-width `：` colon) and a global hotkey that translates the current text selection in place.

**Architecture:** A single `translator.py` core module (language detection, prompt building, LLM call) is invoked two ways: (1) by espanso's `shell` extension for trigger-word matches, and (2) in-process by `hotkey_daemon.py`, a background script that captures the OS selection via simulated copy, calls `translator.py`, and writes the result back per a configurable output mode.

**Tech Stack:** Python 3.10+, `requests` (HTTP), `pyyaml` (config), `keyboard` + `pyperclip` (hotkey daemon), `pytest` (tests), espanso (trigger-word engine, external tool).

## Global Constraints

- Target platform: Windows only.
- Python 3.10+ (plan uses `X | None` union type hints).
- LLM provider is an OpenAI-compatible `/chat/completions` endpoint; config values: `base_url: https://maas-apigateway.dt.zte.com.cn/model-cop/qwen3-235b-a22b-instrust-2507-coclaw/v1/`, `model: Qwen3-235B-A22B`.
- API key is never hardcoded — read at runtime from the environment variable named by `config.yaml`'s `api_key_env` (default `KEYBOARDTRANSLATE_API_KEY`).
- `default_pair` (e.g. `[zh, en]`) drives auto-direction translation; auto-direction requires exactly one of the two codes to be a Chinese code (`zh` or `cn`, case-insensitive).
- `output_mode` is one of `replace | append | popup`, default `replace`.
- On any LLM/network failure, the original text/selection must be left untouched — never overwrite with an error or partial result.
- Secrets (`llm.txt`, `.env`, `config.local.yaml`) stay gitignored; only non-secret settings live in the committed `config.yaml`.

---

### Task 1: Language detection and target-language resolution

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `translator.py`
- Test: `tests/test_translator.py`

**Interfaces:**
- Produces: `is_chinese(text: str, threshold: float = 0.2) -> bool`
- Produces: `resolve_target_lang(text: str, to: str | None, default_pair: list[str]) -> str` (raises `ValueError` if `default_pair` has no Chinese code and `to` is `None`)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_translator.py`:

```python
import pytest

from translator import is_chinese, resolve_target_lang


def test_is_chinese_all_cjk():
    assert is_chinese("你好世界") is True


def test_is_chinese_all_latin():
    assert is_chinese("Hello world") is False


def test_is_chinese_mixed_above_threshold():
    assert is_chinese("你好 hello") is True


def test_is_chinese_empty_string():
    assert is_chinese("") is False


def test_resolve_target_lang_from_chinese():
    assert resolve_target_lang("你好", None, ["zh", "en"]) == "en"


def test_resolve_target_lang_from_other():
    assert resolve_target_lang("hello", None, ["zh", "en"]) == "zh"


def test_resolve_target_lang_explicit_override():
    assert resolve_target_lang("hello", "es", ["zh", "en"]) == "es"


def test_resolve_target_lang_pair_order_reversed():
    assert resolve_target_lang("你好", None, ["en", "zh"]) == "en"


def test_resolve_target_lang_no_chinese_code_raises():
    with pytest.raises(ValueError):
        resolve_target_lang("hello", None, ["en", "es"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_translator.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'translator'` (or `ImportError`)

- [ ] **Step 3: Create scaffolding files**

Create `requirements.txt`:

```
pyyaml
requests
pytest>=7.0
```

Create `pytest.ini`:

```ini
[pytest]
pythonpath = .
```

- [ ] **Step 4: Implement `translator.py`**

Create `translator.py`:

```python
import re

CJK_PATTERN = re.compile(r"[一-鿿]")
ZH_CODES = {"zh", "cn", "zh-cn", "zh-hans"}


def is_chinese(text: str, threshold: float = 0.2) -> bool:
    if not text:
        return False
    cjk_count = len(CJK_PATTERN.findall(text))
    return (cjk_count / len(text)) >= threshold


def _is_zh_code(code: str) -> bool:
    return code.lower() in ZH_CODES


def resolve_target_lang(text: str, to: str | None, default_pair: list[str]) -> str:
    if to:
        return to

    a, b = default_pair
    if _is_zh_code(a):
        zh_code, other_code = a, b
    elif _is_zh_code(b):
        zh_code, other_code = b, a
    else:
        raise ValueError(
            "default_pair must include a Chinese language code (zh/cn) "
            "for auto-direction detection"
        )

    return other_code if is_chinese(text) else zh_code
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_translator.py -v`
Expected: PASS (9 passed)

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pytest.ini translator.py tests/test_translator.py
git commit -m "feat: add language detection and target-language resolution"
```

---

### Task 2: Prompt building

**Files:**
- Modify: `translator.py`
- Test: `tests/test_translator.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `build_messages(text: str, target_lang: str) -> list[dict]`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_translator.py`:

```python
from translator import build_messages


def test_build_messages_structure():
    messages = build_messages("你好", "en")
    assert messages == [
        {
            "role": "system",
            "content": (
                "You are a professional translator. Translate the user's "
                "text into en. Output ONLY the translation, with no "
                "explanations, quotes, or additional commentary."
            ),
        },
        {"role": "user", "content": "你好"},
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_translator.py::test_build_messages_structure -v`
Expected: FAIL with `ImportError: cannot import name 'build_messages'`

- [ ] **Step 3: Implement `build_messages`**

Append to `translator.py`:

```python
def build_messages(text: str, target_lang: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": (
                "You are a professional translator. Translate the user's "
                f"text into {target_lang}. Output ONLY the translation, "
                "with no explanations, quotes, or additional commentary."
            ),
        },
        {"role": "user", "content": text},
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_translator.py -v`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
git add translator.py tests/test_translator.py
git commit -m "feat: add LLM prompt building"
```

---

### Task 3: Config loading

**Files:**
- Modify: `translator.py`
- Create: `config.yaml`
- Test: `tests/test_translator.py`

**Interfaces:**
- Produces: `DEFAULT_CONFIG_PATH: str`, `load_config(path: str = DEFAULT_CONFIG_PATH) -> dict`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_translator.py`:

```python
from translator import load_config


def test_load_config_reads_yaml(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "provider: custom\n"
        "base_url: https://example.invalid/v1/\n"
        "model: test-model\n"
        "api_key_env: TEST_API_KEY\n"
        "default_pair: [zh, en]\n"
        "output_mode: replace\n"
        "hotkey: ctrl+alt+t\n",
        encoding="utf-8",
    )
    config = load_config(str(config_file))
    assert config["model"] == "test-model"
    assert config["default_pair"] == ["zh", "en"]
    assert config["output_mode"] == "replace"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_translator.py::test_load_config_reads_yaml -v`
Expected: FAIL with `ImportError: cannot import name 'load_config'`

- [ ] **Step 3: Implement `load_config`**

Append to `translator.py` (add `import yaml` to the top of the file alongside the existing `import re`):

```python
import yaml

DEFAULT_CONFIG_PATH = "config.yaml"


def load_config(path: str = DEFAULT_CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
```

- [ ] **Step 4: Create the committed `config.yaml`**

Create `config.yaml`:

```yaml
provider: custom
base_url: https://maas-apigateway.dt.zte.com.cn/model-cop/qwen3-235b-a22b-instrust-2507-coclaw/v1/
model: Qwen3-235B-A22B
api_key_env: KEYBOARDTRANSLATE_API_KEY
default_pair: [zh, en]
output_mode: replace
hotkey: ctrl+alt+t
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_translator.py -v`
Expected: PASS (11 passed)

- [ ] **Step 6: Commit**

```bash
git add translator.py config.yaml tests/test_translator.py
git commit -m "feat: add config.yaml loading"
```

---

### Task 4: LLM call wrapper

**Files:**
- Modify: `translator.py`
- Test: `tests/test_translator.py`

**Interfaces:**
- Consumes: a config dict shaped `{"base_url": str, "model": str, "api_key_env": str}`
- Produces: `TranslationError(Exception)`, `call_llm(messages: list[dict], config: dict, timeout: float = 15.0) -> str`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_translator.py`:

```python
from unittest.mock import patch, MagicMock

import requests

from translator import call_llm, TranslationError


def _fake_config():
    return {
        "base_url": "https://example.invalid/v1/",
        "model": "test-model",
        "api_key_env": "TEST_API_KEY",
    }


def test_call_llm_success(monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "secret-key")
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "choices": [{"message": {"content": " Hello "}}]
    }
    with patch("translator.requests.post", return_value=fake_response) as mock_post:
        result = call_llm([{"role": "user", "content": "你好"}], _fake_config())
    assert result == "Hello"
    called_url = mock_post.call_args.args[0]
    assert called_url == "https://example.invalid/v1/chat/completions"
    called_headers = mock_post.call_args.kwargs["headers"]
    assert called_headers["Authorization"] == "Bearer secret-key"


def test_call_llm_missing_api_key_env(monkeypatch):
    monkeypatch.delenv("TEST_API_KEY", raising=False)
    with pytest.raises(TranslationError):
        call_llm([{"role": "user", "content": "hi"}], _fake_config())


def test_call_llm_request_exception(monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "secret-key")
    with patch(
        "translator.requests.post",
        side_effect=requests.RequestException("boom"),
    ):
        with pytest.raises(TranslationError):
            call_llm([{"role": "user", "content": "hi"}], _fake_config())


def test_call_llm_malformed_response(monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "secret-key")
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {"unexpected": "shape"}
    with patch("translator.requests.post", return_value=fake_response):
        with pytest.raises(TranslationError):
            call_llm([{"role": "user", "content": "hi"}], _fake_config())
```

Add `import pytest` at the top of `tests/test_translator.py` if not already present.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_translator.py -k call_llm -v`
Expected: FAIL with `ImportError: cannot import name 'call_llm'`

- [ ] **Step 3: Implement `call_llm`**

Append to `translator.py` (add `import os` and `import requests` to the top of the file):

```python
import os

import requests


class TranslationError(Exception):
    pass


def call_llm(messages: list[dict], config: dict, timeout: float = 15.0) -> str:
    api_key = os.environ.get(config["api_key_env"])
    if not api_key:
        raise TranslationError(
            f"Environment variable {config['api_key_env']} is not set"
        )

    url = config["base_url"].rstrip("/") + "/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": config["model"],
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.2,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        raise TranslationError(f"LLM request failed: {e}") from e

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as e:
        raise TranslationError(f"Unexpected LLM response shape: {data}") from e
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_translator.py -v`
Expected: PASS (15 passed)

- [ ] **Step 5: Commit**

```bash
git add translator.py tests/test_translator.py
git commit -m "feat: add LLM call wrapper with error handling"
```

---

### Task 5: `translate()` orchestration and CLI entry point

**Files:**
- Modify: `translator.py`
- Test: `tests/test_translator.py`

**Interfaces:**
- Consumes: `resolve_target_lang`, `build_messages`, `call_llm`, `load_config`, `TranslationError` (all from this same module, Tasks 1-4)
- Produces: `translate(text: str, to: str | None = None, config: dict | None = None) -> str`, `main() -> None` (CLI entry point)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_translator.py`:

```python
import sys

import translator
from translator import translate


def test_translate_uses_resolved_lang_and_calls_llm(monkeypatch):
    captured = {}

    def fake_call_llm(messages, config, timeout=15.0):
        captured["messages"] = messages
        return "Hello"

    monkeypatch.setattr(translator, "call_llm", fake_call_llm)
    config = {"default_pair": ["zh", "en"]}
    result = translate("你好", config=config)
    assert result == "Hello"
    assert captured["messages"][0]["content"].endswith("into en. Output ONLY the translation, with no explanations, quotes, or additional commentary.")


def test_translate_loads_config_when_not_provided(monkeypatch, tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "default_pair: [zh, en]\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(translator, "DEFAULT_CONFIG_PATH", str(config_file))
    monkeypatch.setattr(translator, "call_llm", lambda messages, config, timeout=15.0: "Hi")
    result = translate("你好")
    assert result == "Hi"


def test_cli_main_prints_translation(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["translator.py", "--text", "你好", "--to", "en"])
    monkeypatch.setattr(translator, "load_config", lambda path=translator.DEFAULT_CONFIG_PATH: {"default_pair": ["zh", "en"]})
    monkeypatch.setattr(translator, "translate", lambda text, to=None, config=None: "Hello")
    translator.main()
    captured = capsys.readouterr()
    assert captured.out.strip() == "Hello"


def test_cli_main_reports_translation_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["translator.py", "--text", "你好"])
    monkeypatch.setattr(translator, "load_config", lambda path=translator.DEFAULT_CONFIG_PATH: {"default_pair": ["zh", "en"]})

    def raise_error(text, to=None, config=None):
        raise translator.TranslationError("network down")

    monkeypatch.setattr(translator, "translate", raise_error)
    with pytest.raises(SystemExit) as exc_info:
        translator.main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "network down" in captured.err
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_translator.py -k "translate or cli_main" -v`
Expected: FAIL with `ImportError: cannot import name 'translate'`

- [ ] **Step 3: Implement `translate()` and CLI `main()`**

Append to `translator.py` (add `import argparse` and `import sys` to the top of the file):

```python
import argparse
import sys


def translate(text: str, to: str | None = None, config: dict | None = None) -> str:
    if config is None:
        config = load_config()
    target_lang = resolve_target_lang(text, to, config["default_pair"])
    messages = build_messages(text, target_lang)
    return call_llm(messages, config)


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate text via LLM")
    parser.add_argument("--text", required=True)
    parser.add_argument("--to", default=None)
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()

    config = load_config(args.config)
    try:
        result = translate(args.text, to=args.to, config=config)
    except TranslationError as e:
        print(f"[translate error] {e}", file=sys.stderr)
        sys.exit(1)
    print(result)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_translator.py -v`
Expected: PASS (19 passed)

- [ ] **Step 5: Commit**

```bash
git add translator.py tests/test_translator.py
git commit -m "feat: add translate() orchestration and CLI entry point"
```

---

### Task 6: espanso trigger-word configuration

**Files:**
- Create: `espanso/translate.yml`
- Create: `docs/espanso-setup.md`

**Interfaces:** None (declarative espanso config, not a Python module; espanso itself is an external tool and cannot be exercised in an automated test suite here).

- [ ] **Step 1: Create the espanso match file**

Create `espanso/translate.yml`. Triggers use `[:：]` so either the ASCII
colon or the full-width Chinese colon (produced by IMEs in Chinese
punctuation mode) works without switching input method state. The
language-specific triggers (`:cn`, `:en`, `:es`) don't need a `tr` prefix
because the leading colon itself is what makes the trigger safe from
accidental matches in normal text; the bare default-direction trigger
keeps `tr` (`:tr`) since a bare `:t` would be too easy to type by accident:

```yaml
matches:
  - regex: "[:：]cn (?P<text>.+)$"
    replace: "{{output}}"
    vars:
      - name: output
        type: shell
        params:
          cmd: 'python translator.py --text "{{text}}" --to cn'

  - regex: "[:：]en (?P<text>.+)$"
    replace: "{{output}}"
    vars:
      - name: output
        type: shell
        params:
          cmd: 'python translator.py --text "{{text}}" --to en'

  - regex: "[:：]es (?P<text>.+)$"
    replace: "{{output}}"
    vars:
      - name: output
        type: shell
        params:
          cmd: 'python translator.py --text "{{text}}" --to es'

  - regex: "[:：]tr (?P<text>.+)$"
    replace: "{{output}}"
    vars:
      - name: output
        type: shell
        params:
          cmd: 'python translator.py --text "{{text}}"'
```

- [ ] **Step 2: Write the manual verification checklist**

Create `docs/espanso-setup.md`:

```markdown
# espanso Setup and Manual Verification

## Install

1. Install espanso for Windows: https://espanso.org/install/windows/
2. Find your espanso match directory: `espanso path`
3. Copy (or symlink) `espanso/translate.yml` from this repo into that directory's `match/` folder.
4. Ensure `python` and `translator.py` are on your PATH / working directory matches, or edit the `cmd` in `translate.yml` to use an absolute path, e.g. `python D:\pythonProject2\keyboardtranslate\translator.py --text "{{text}}"`.
5. Set the `KEYBOARDTRANSLATE_API_KEY` environment variable (System Properties -> Environment Variables), then restart espanso: `espanso restart`.

## Manual verification checklist

- [ ] Type `:tr 你好世界` in any text box (e.g. Notepad) and confirm it expands to an English translation.
- [ ] Type `:tr hello world` and confirm it expands to a Chinese translation.
- [ ] Type `:en 你好` and confirm it expands to an English translation (explicit target).
- [ ] Type `:cn hello` and confirm it expands to a Chinese translation (explicit target).
- [ ] Type `:es hello` and confirm it expands to a Spanish translation (explicit target).
- [ ] With your IME in Chinese punctuation mode, type `：cn hello` (full-width colon) and confirm it triggers the same as `:cn hello` — no need to switch to English punctuation mode first.
- [ ] Unset `KEYBOARDTRANSLATE_API_KEY` temporarily and confirm the trigger does not silently insert garbage (the shell command should fail visibly or insert an error string, not corrupt the input box).
```

- [ ] **Step 3: Commit**

```bash
git add espanso/translate.yml docs/espanso-setup.md
git commit -m "feat: add espanso trigger-word configuration"
```

---

### Task 7: Hotkey daemon core functions (selection capture, output application)

**Files:**
- Create: `hotkey_daemon.py`
- Test: `tests/test_hotkey_daemon.py`

**Interfaces:**
- Consumes: nothing from other project modules yet
- Produces: `capture_selection(paste_delay: float = 0.15) -> str`, `apply_output(original: str, translation: str, output_mode: str) -> None` (raises `ValueError` on unknown `output_mode`)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_hotkey_daemon.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_hotkey_daemon.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hotkey_daemon'`

- [ ] **Step 3: Implement core functions in `hotkey_daemon.py`**

Create `hotkey_daemon.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_hotkey_daemon.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add hotkey_daemon.py tests/test_hotkey_daemon.py
git commit -m "feat: add hotkey daemon selection capture and output application"
```

---

### Task 8: Hotkey daemon integration (`on_hotkey`, `main`)

**Files:**
- Modify: `hotkey_daemon.py`
- Test: `tests/test_hotkey_daemon.py`

**Interfaces:**
- Consumes: `translate(text, to=None, config=None) -> str` and `TranslationError` from `translator.py` (Task 5); `load_config` from `translator.py` (Task 3); `capture_selection`, `apply_output`, `_notify_error` from this module (Task 7)
- Produces: `on_hotkey(config: dict) -> None`, `main() -> None`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_hotkey_daemon.py`:

```python
from translator import TranslationError


def test_on_hotkey_no_selection_notifies_and_skips(monkeypatch):
    monkeypatch.setattr(hotkey_daemon, "capture_selection", lambda: "   ")
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_hotkey_daemon.py -k on_hotkey -v`
Expected: FAIL with `AttributeError: module 'hotkey_daemon' has no attribute 'on_hotkey'`

- [ ] **Step 3: Implement `on_hotkey` and `main`**

Append to `hotkey_daemon.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_hotkey_daemon.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add hotkey_daemon.py tests/test_hotkey_daemon.py
git commit -m "feat: add hotkey daemon integration and CLI entry point"
```

---

### Task 9: Finalize dependencies and top-level README

**Files:**
- Modify: `requirements.txt`
- Create: `README.md`

**Interfaces:** None (documentation and dependency manifest only).

- [ ] **Step 1: Add remaining runtime dependencies**

Update `requirements.txt`:

```
pyyaml
requests
keyboard
pyperclip
pytest>=7.0
```

- [ ] **Step 2: Write the README**

Create `README.md`:

```markdown
# keyboardtranslate

LLM-backed translation for any Windows input box, via two entry points that
share one `translator.py` core:

- **espanso trigger words** (`:tr` for auto-direction, `:cn`/`:en`/`:es` for
  explicit targets — `：` full-width colon also works) — see
  `docs/espanso-setup.md` for installation and manual verification steps.
- **Global hotkey on a text selection** — run `python hotkey_daemon.py` in
  the background; select text anywhere and press `Ctrl+Alt+T` (configurable
  in `config.yaml`) to translate it in place.

## Setup

1. `pip install -r requirements.txt`
2. Set the `KEYBOARDTRANSLATE_API_KEY` environment variable to your LLM
   gateway's API key. Never put it in `config.yaml` or any committed file.
3. Adjust `config.yaml` if needed: `default_pair`, `output_mode`
   (`replace` | `append` | `popup`), `hotkey`.
4. Run `pytest` to verify the core logic.
5. For the hotkey daemon: `python hotkey_daemon.py`.
6. For espanso trigger words: follow `docs/espanso-setup.md`.

## Design

See `docs/superpowers/specs/2026-07-01-keyboard-translate-design.md` for the
full design rationale.
```

- [ ] **Step 3: Run the full test suite**

Run: `pytest -v`
Expected: PASS (27 passed)

- [ ] **Step 4: Commit**

```bash
git add requirements.txt README.md
git commit -m "docs: add README and finalize dependencies"
```
