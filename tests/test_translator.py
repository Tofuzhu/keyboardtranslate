import sys

import pytest
import requests
from unittest.mock import MagicMock, patch

import translator
from translator import (
    TranslationError,
    build_messages,
    call_llm,
    is_chinese,
    load_config,
    resolve_target_lang,
    translate,
)


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


def test_call_llm_invalid_json_response(monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "secret-key")
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.side_effect = ValueError("Expecting value: line 1 column 1")
    with patch("translator.requests.post", return_value=fake_response):
        with pytest.raises(TranslationError):
            call_llm([{"role": "user", "content": "hi"}], _fake_config())


def test_call_llm_null_content_response(monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "secret-key")
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "choices": [{"message": {"content": None}}]
    }
    with patch("translator.requests.post", return_value=fake_response):
        with pytest.raises(TranslationError):
            call_llm([{"role": "user", "content": "hi"}], _fake_config())


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
