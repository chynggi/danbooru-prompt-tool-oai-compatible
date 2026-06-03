from __future__ import annotations

from pathlib import Path

from danbooru_prompt_tool import TagDatabase, build_prompt


DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "danbooru_tags.sqlite"


class DanbooruPromptBuilder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "natural_language": ("STRING", {"default": "", "multiline": True}),
                "db_path": ("STRING", {"default": str(DEFAULT_DB), "multiline": False}),
                "max_tags": ("INT", {"default": 18, "min": 1, "max": 80}),
                "min_post_count": ("INT", {"default": 25, "min": 0, "max": 10_000_000}),
                "include_quality": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "debug_matches")
    FUNCTION = "build"
    CATEGORY = "local/prompt"

    def build(self, natural_language, db_path, max_tags, min_post_count, include_quality):
        db = TagDatabase(db_path)
        result = build_prompt(db, natural_language, max_tags, min_post_count, include_quality)
        return (result.prompt, result.notes)


NODE_CLASS_MAPPINGS = {
    "DanbooruPromptBuilder": DanbooruPromptBuilder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DanbooruPromptBuilder": "Danbooru Prompt Builder",
}
