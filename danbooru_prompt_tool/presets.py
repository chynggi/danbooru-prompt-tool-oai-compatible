from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptPreset:
    name: str
    label: str
    family: str
    positive_defaults: tuple[str, ...]
    negative_defaults: tuple[str, ...]
    rating_map: dict[str, str]
    score_tags: tuple[str, ...] = ()
    always_score: bool = False


IDENTITY_RATINGS = {
    "": "",
    "general": "general",
    "sensitive": "sensitive",
    "nsfw": "nsfw",
    "explicit": "explicit",
}

SAFE_RATINGS = {
    "": "",
    "general": "safe",
    "sensitive": "sensitive",
    "nsfw": "nsfw",
    "explicit": "explicit",
}

PONY_RATINGS = {
    "": "",
    "general": "rating_safe",
    "sensitive": "rating_questionable",
    "nsfw": "rating_questionable",
    "explicit": "rating_explicit",
}

PONY_SCORE_TAGS = (
    "score_9",
    "score_8_up",
    "score_7_up",
    "score_6_up",
    "score_5_up",
    "score_4_up",
)

PRESETS: dict[str, PromptPreset] = {
    "custom": PromptPreset(
        name="custom",
        label="Custom .env defaults",
        family="Custom",
        positive_defaults=(),
        negative_defaults=(),
        rating_map=IDENTITY_RATINGS,
    ),
    "wai_illustrious": PromptPreset(
        name="wai_illustrious",
        label="WAI / Illustrious finetune",
        family="Illustrious",
        positive_defaults=("masterpiece", "best quality", "amazing quality"),
        negative_defaults=("bad quality", "worst quality", "worst detail", "sketch", "censor"),
        rating_map=IDENTITY_RATINGS,
    ),
    "illustrious_base": PromptPreset(
        name="illustrious_base",
        label="Illustrious XL base",
        family="Illustrious",
        positive_defaults=("masterpiece", "best quality"),
        negative_defaults=(
            "worst quality",
            "comic",
            "multiple views",
            "bad quality",
            "low quality",
            "lowres",
            "displeasing",
            "very displeasing",
            "bad anatomy",
            "bad hands",
            "scan artifacts",
            "monochrome",
            "greyscale",
            "signature",
            "twitter username",
            "jpeg artifacts",
            "2koma",
            "4koma",
            "guro",
            "extra digits",
            "fewer digits",
        ),
        rating_map=IDENTITY_RATINGS,
    ),
    "noobai_xl": PromptPreset(
        name="noobai_xl",
        label="NoobAI XL",
        family="NoobAI",
        positive_defaults=("masterpiece", "best quality", "newest", "absurdres", "highres"),
        negative_defaults=(
            "nsfw",
            "worst quality",
            "old",
            "early",
            "low quality",
            "lowres",
            "signature",
            "username",
            "logo",
            "bad hands",
            "mutated hands",
            "mammal",
            "anthro",
            "furry",
            "ambiguous form",
            "feral",
            "semi-anthro",
        ),
        rating_map=SAFE_RATINGS,
    ),
    "animagine_xl_4": PromptPreset(
        name="animagine_xl_4",
        label="Animagine XL 4.0",
        family="Animagine",
        positive_defaults=("masterpiece", "high score", "great score", "absurdres"),
        negative_defaults=(
            "lowres",
            "bad anatomy",
            "bad hands",
            "text",
            "error",
            "missing finger",
            "extra digits",
            "fewer digits",
            "cropped",
            "worst quality",
            "low quality",
            "low score",
            "bad score",
            "average score",
            "signature",
            "watermark",
            "username",
            "blurry",
        ),
        rating_map=SAFE_RATINGS,
    ),
    "kohaku_xl": PromptPreset(
        name="kohaku_xl",
        label="Kohaku XL",
        family="Kohaku",
        positive_defaults=("masterpiece", "best quality", "great quality"),
        negative_defaults=("low quality", "worst quality", "lowres", "bad anatomy", "bad hands", "signature", "watermark"),
        rating_map=SAFE_RATINGS,
    ),
    "wai_anima": PromptPreset(
        name="wai_anima",
        label="WAI-Anima / Anima preview",
        family="Anima",
        positive_defaults=("masterpiece", "best quality"),
        negative_defaults=(
            "worst quality",
            "low quality",
            "score_1",
            "score_2",
            "score_3",
            "artist name",
            "blurry",
            "jpeg artifacts",
            "lowres",
            "censor",
        ),
        rating_map=IDENTITY_RATINGS,
        score_tags=("score_9", "score_8", "score_7"),
        always_score=True,
    ),
    "pony_v6": PromptPreset(
        name="pony_v6",
        label="Pony Diffusion V6 XL / Pony derivatives",
        family="Pony",
        positive_defaults=(),
        negative_defaults=(),
        rating_map=PONY_RATINGS,
        score_tags=PONY_SCORE_TAGS,
        always_score=True,
    ),
}


def preset_names() -> list[str]:
    return list(PRESETS)


def get_preset(name: str | None) -> PromptPreset:
    if not name:
        return PRESETS["wai_illustrious"]
    return PRESETS.get(name, PRESETS["custom"])
