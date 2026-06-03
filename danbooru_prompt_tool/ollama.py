from __future__ import annotations

import json
import urllib.error
import urllib.request


SYSTEM_PROMPT = """You convert a user's natural-language image request into Danbooru-style tag candidates for Illustrious/WAI SDXL.
Return only comma-separated tag candidates. No sentences, no markdown, no explanations.
Use simple visual tags where possible, for example 1girl, long_hair, black_hair, red_eyes, standing, sunset.
Do not invent character names, franchises, artist names, or copyrighted names unless the user explicitly names them.
Preserve rating tags only if the user explicitly asks for them: general, sensitive, nsfw, explicit.
If the user says "use scoring", do not output score tags; the local tool handles those separately.
"""


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


def parse_tag_list(raw: str) -> list[str]:
    raw = raw.replace("\n", ",")
    tags = []
    seen = set()
    for item in raw.split(","):
        tag = item.strip().strip("`").strip()
        if not tag:
            continue
        tag = tag.replace(" ", "_")
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        tags.append(tag)
    return tags
