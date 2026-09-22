from __future__ import annotations


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
