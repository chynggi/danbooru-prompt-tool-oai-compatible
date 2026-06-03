from __future__ import annotations

from pathlib import Path

from danbooru_prompt_tool.config import get_settings
from danbooru_prompt_tool import TagDatabase, build_prompt


DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "danbooru_tags.sqlite"


class DanbooruPromptBuilder:
    @classmethod
    def INPUT_TYPES(cls):
        settings = get_settings()
        return {
            "required": {
                "natural_language": ("STRING", {"default": "", "multiline": True}),
                "db_path": ("STRING", {"default": str(DEFAULT_DB), "multiline": False}),
                "max_tags": ("INT", {"default": 18, "min": 1, "max": 80}),
                "min_post_count": ("INT", {"default": 25, "min": 0, "max": 10_000_000}),
                "use_ollama": ("BOOLEAN", {"default": settings.use_ollama}),
                "ollama_model": ("STRING", {"default": settings.ollama_model, "multiline": False}),
                "ollama_url": ("STRING", {"default": settings.ollama_url, "multiline": False}),
                "include_defaults": ("BOOLEAN", {"default": settings.include_defaults}),
                "include_quality": ("BOOLEAN", {"default": True}),
                "include_negative": ("BOOLEAN", {"default": True}),
                "default_rating": (["", "general", "sensitive", "nsfw", "explicit"], {"default": settings.default_rating}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("prompt", "debug_matches", "negative_prompt")
    FUNCTION = "build"
    CATEGORY = "local/prompt"

    def build(
        self,
        natural_language,
        db_path,
        max_tags,
        min_post_count,
        use_ollama,
        ollama_model,
        ollama_url,
        include_defaults,
        include_quality,
        include_negative,
        default_rating,
    ):
        db = TagDatabase(db_path)
        result = build_prompt(
            db,
            natural_language,
            limit=max_tags,
            min_count=min_post_count,
            include_quality=include_quality,
            use_ollama=use_ollama,
            ollama_model=ollama_model,
            ollama_url=ollama_url,
            include_defaults=include_defaults,
            include_negative=include_negative,
            default_rating=default_rating,
        )
        return (result.prompt, result.notes, result.negative_prompt)


NODE_CLASS_MAPPINGS = {
    "DanbooruPromptBuilder": DanbooruPromptBuilder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DanbooruPromptBuilder": "Danbooru Prompt Builder",
}
