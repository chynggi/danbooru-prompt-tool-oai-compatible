from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


TOOL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = TOOL_ROOT / ".env"
RATING_TAGS = {"", "general", "sensitive", "nsfw", "explicit"}


def load_env(path: str | Path = DEFAULT_ENV_PATH) -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        parsed = int(value.strip())
    except ValueError:
        return default
    return max(minimum, min(maximum, parsed))


@dataclass(frozen=True)
class Settings:
    model_preset: str
    use_ollama: bool
    ollama_model: str
    ollama_url: str
    smart_formatting: bool
    smart_format_max_fragments: int
    positive_defaults: list[str]
    negative_defaults: list[str]
    default_rating: str
    include_defaults: bool


def get_settings(env_path: str | Path = DEFAULT_ENV_PATH) -> Settings:
    load_env(env_path)
    return Settings(
        model_preset=os.environ.get("DANBOORU_PROMPT_MODEL_PRESET", "wai_illustrious"),
        use_ollama=env_bool("DANBOORU_PROMPT_USE_OLLAMA", True),
        ollama_model=os.environ.get("DANBOORU_PROMPT_OLLAMA_MODEL", "gemma4:e4b"),
        ollama_url=os.environ.get("DANBOORU_PROMPT_OLLAMA_URL", "http://127.0.0.1:11434"),
        smart_formatting=env_bool("DANBOORU_PROMPT_SMART_FORMATTING", True),
        smart_format_max_fragments=env_int("DANBOORU_PROMPT_SMART_FORMAT_MAX_FRAGMENTS", 4, 0, 10),
        positive_defaults=split_tags(
            os.environ.get(
                "DANBOORU_PROMPT_DEFAULT_POSITIVE",
                "masterpiece,best quality,amazing quality",
            )
        ),
        negative_defaults=split_tags(
            os.environ.get(
                "DANBOORU_PROMPT_DEFAULT_NEGATIVE",
                "bad quality,worst quality,worst detail,sketch,censor",
            )
        ),
        default_rating=normalize_rating(os.environ.get("DANBOORU_PROMPT_DEFAULT_RATING", "general")),
        include_defaults=env_bool("DANBOORU_PROMPT_INCLUDE_DEFAULTS", True),
    )


def split_tags(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def normalize_rating(value: str) -> str:
    for item in value.split(","):
        rating = item.strip().lower()
        if rating in RATING_TAGS:
            return rating
    return "general"
