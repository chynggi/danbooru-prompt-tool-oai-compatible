from __future__ import annotations

import json
import urllib.error
import urllib.request

from .llm import SMART_FORMAT_SYSTEM_PROMPT, SYSTEM_PROMPT, parse_fragment_list, parse_tag_list


def openai_tag_candidates(
    text: str,
    model: str,
    base_url: str,
    api_key: str = "",
    timeout: int = 60,
) -> list[str]:
    raw = chat_completion(
        SYSTEM_PROMPT,
        text,
        model,
        base_url,
        api_key,
        temperature=0.1,
        timeout=timeout,
        error_label="OpenAI-compatible endpoint unavailable",
    )
    return parse_tag_list(raw)


def openai_smart_fragments(
    original_text: str,
    matched_tags: list[str],
    unresolved_phrases: list[str],
    model: str,
    base_url: str,
    api_key: str = "",
    max_fragments: int = 4,
    timeout: int = 60,
) -> list[str]:
    if max_fragments <= 0:
        return []
    prompt = "\n".join(
        [
            f"Original request: {original_text}",
            "Matched Danbooru tags: " + ", ".join(matched_tags),
            "Unresolved phrases: " + ", ".join(unresolved_phrases[:24]),
            f"Return up to {max_fragments} missing visual fragments.",
        ]
    )
    raw = chat_completion(
        SMART_FORMAT_SYSTEM_PROMPT,
        prompt,
        model,
        base_url,
        api_key,
        temperature=0.15,
        timeout=timeout,
        error_label="OpenAI-compatible smart formatting unavailable",
    )
    return parse_fragment_list(raw, max_fragments)


def chat_completion(
    system: str,
    user: str,
    model: str,
    base_url: str,
    api_key: str,
    temperature: float,
    timeout: int,
    error_label: str,
) -> str:
    headers = {"Content-Type": "application/json"}
    api_key = (api_key or "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "top_p": 0.8,
        "stream": False,
    }
    request = urllib.request.Request(
        chat_completions_url(base_url),
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{error_label}: {exc}") from exc
    return extract_message_content(payload)


def chat_completions_url(base_url: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    if not base:
        base = "http://127.0.0.1:1234/v1"
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def extract_message_content(payload: dict) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if isinstance(message, dict) and message.get("content") is not None:
        return str(message["content"])
    return ""
