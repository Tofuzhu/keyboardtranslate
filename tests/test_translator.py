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
