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
