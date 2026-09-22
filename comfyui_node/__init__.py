from __future__ import annotations

from pathlib import Path

from danbooru_prompt_tool.config import get_settings
from danbooru_prompt_tool import TagDatabase, build_prompt
from danbooru_prompt_tool.presets import preset_names


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
                "model_preset": (preset_names(), {"default": settings.model_preset}),
                "tag_matching": ("BOOLEAN", {"default": settings.tag_matching}),
                "use_ollama": ("BOOLEAN", {"default": settings.use_ollama}),
                "ollama_model": ("STRING", {"default": settings.ollama_model, "multiline": False}),
                "ollama_url": ("STRING", {"default": settings.ollama_url, "multiline": False}),
                "llm_provider": (["ollama", "openai"], {"default": settings.llm_provider}),
                "openai_model": ("STRING", {"default": settings.openai_model, "multiline": False}),
                "openai_base_url": ("STRING", {"default": settings.openai_base_url, "multiline": False}),
                "openai_api_key": ("STRING", {"default": settings.openai_api_key, "multiline": False}),
                "smart_formatting": ("BOOLEAN", {"default": settings.smart_formatting}),
                "smart_format_max_fragments": (
                    "INT",
                    {"default": settings.smart_format_max_fragments, "min": 0, "max": 100},
                ),
                "dynamic_smart_formatting": ("BOOLEAN", {"default": settings.dynamic_smart_formatting}),
                "dynamic_smart_format_min_fragments": (
                    "INT",
                    {"default": settings.dynamic_smart_format_min_fragments, "min": 1, "max": 100},
                ),
                "dynamic_smart_format_max_fragments": (
                    "INT",
                    {"default": settings.dynamic_smart_format_max_fragments, "min": 1, "max": 100},
                ),
                "include_defaults": ("BOOLEAN", {"default": settings.include_defaults}),
                "include_quality": ("BOOLEAN", {"default": True}),
                "include_negative": ("BOOLEAN", {"default": True}),
                "default_rating": (["", "general", "sensitive", "nsfw", "explicit"], {"default": settings.default_rating}),
                "negative_prompt_base": ("STRING", {"default": "", "multiline": True}),
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
        model_preset,
        tag_matching,
        use_ollama,
        ollama_model,
        ollama_url,
        llm_provider,
        openai_model,
        openai_base_url,
        openai_api_key,
        smart_formatting,
        smart_format_max_fragments,
        dynamic_smart_formatting,
        dynamic_smart_format_min_fragments,
        dynamic_smart_format_max_fragments,
        include_defaults,
        include_quality,
        include_negative,
        default_rating,
        negative_prompt_base="",
    ):
        db = TagDatabase(db_path)
        result = build_prompt(
            db,
            natural_language,
            limit=max_tags,
            min_count=min_post_count,
            include_quality=include_quality,
            model_preset=model_preset,
            tag_matching=tag_matching,
            use_ollama=use_ollama,
            ollama_model=ollama_model,
            ollama_url=ollama_url,
            llm_provider=llm_provider,
            openai_model=openai_model,
            openai_base_url=openai_base_url,
            openai_api_key=openai_api_key,
            smart_formatting=smart_formatting,
            smart_format_max_fragments=smart_format_max_fragments,
            dynamic_smart_formatting=dynamic_smart_formatting,
            dynamic_smart_format_min_fragments=dynamic_smart_format_min_fragments,
            dynamic_smart_format_max_fragments=dynamic_smart_format_max_fragments,
            include_defaults=include_defaults,
            include_negative=include_negative,
            default_rating=default_rating,
            negative_prompt_base=negative_prompt_base,
        )
        return (result.prompt, result.notes, result.negative_prompt)


NODE_CLASS_MAPPINGS = {
    "DanbooruPromptBuilder": DanbooruPromptBuilder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DanbooruPromptBuilder": "Danbooru Prompt Builder",
}
