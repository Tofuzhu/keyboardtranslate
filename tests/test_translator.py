import pytest

from translator import is_chinese, resolve_target_lang, build_messages


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
