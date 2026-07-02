import os
import re

import requests
import yaml

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


DEFAULT_CONFIG_PATH = "config.yaml"


def load_config(path: str = DEFAULT_CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


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

    data = None
    try:
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError, ValueError) as e:
        raise TranslationError(f"Unexpected LLM response shape: {data}") from e
