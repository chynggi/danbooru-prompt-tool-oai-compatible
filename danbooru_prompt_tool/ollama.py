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


SMART_FORMAT_SYSTEM_PROMPT = """You are a Stable Diffusion prompt repair step for Illustrious/WAI SDXL.
You receive the original request, the matched Danbooru tags, and unresolved phrases that did not map cleanly to tags.
Return only short comma-separated visual prompt fragments that preserve important missing details.
Do not repeat details already clearly covered by the matched tags.
Do not output labels, markdown, explanations, or full sentences.
Use natural language fragments with spaces, not underscores.
Prefer concrete visual relationships, subject visibility, direction, pose, composition, lighting, and missing objects.
Keep each fragment under 10 words.
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


def parse_fragment_list(raw: str, limit: int) -> list[str]:
    raw = raw.replace("\n", ",")
    fragments = []
    seen = set()
    for item in raw.split(","):
        fragment = item.strip().strip("`").strip()
        if not fragment:
            continue
        fragment = " ".join(fragment.split())
        fragment = fragment.rstrip(".")
        key = fragment.lower()
        if key in seen:
            continue
        seen.add(key)
        fragments.append(fragment)
        if len(fragments) >= limit:
            break
    return fragments
