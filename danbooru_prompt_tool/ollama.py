from __future__ import annotations

import json
import urllib.error
import urllib.request

from .llm import SMART_FORMAT_SYSTEM_PROMPT, SYSTEM_PROMPT, parse_fragment_list, parse_tag_list


def ollama_tag_candidates(text: str, model: str, base_url: str, timeout: int = 60) -> list[str]:
    url = base_url.rstrip("/") + "/api/generate"
    body = {
        "model": model,
        "system": SYSTEM_PROMPT,
        "prompt": text,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.8,
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Ollama unavailable: {exc}") from exc
    raw = str(payload.get("response", ""))
    return parse_tag_list(raw)


def ollama_smart_fragments(
    original_text: str,
    matched_tags: list[str],
    unresolved_phrases: list[str],
    model: str,
    base_url: str,
    max_fragments: int = 4,
    timeout: int = 60,
) -> list[str]:
    if max_fragments <= 0:
        return []
    url = base_url.rstrip("/") + "/api/generate"
    prompt = "\n".join(
        [
            f"Original request: {original_text}",
            "Matched Danbooru tags: " + ", ".join(matched_tags),
            "Unresolved phrases: " + ", ".join(unresolved_phrases[:24]),
            f"Return up to {max_fragments} missing visual fragments.",
        ]
    )
    body = {
        "model": model,
        "system": SMART_FORMAT_SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.15,
            "top_p": 0.8,
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Ollama smart formatting unavailable: {exc}") from exc
    raw = str(payload.get("response", ""))
    return parse_fragment_list(raw, max_fragments)
