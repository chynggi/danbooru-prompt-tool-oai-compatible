from __future__ import annotations

import re
from dataclasses import dataclass

from .config import get_settings, normalize_rating
from .database import TagDatabase, expand_candidates
from .ollama import ollama_smart_fragments, ollama_tag_candidates
from .presets import get_preset


SCORE_TAGS = ["score_9", "score_8_up", "score_7_up", "score_6_up"]
USE_SCORING_RE = re.compile(r"\buse\s+scoring\b", re.IGNORECASE)
NO_DEFAULTS_RE = re.compile(r"\b(no|without|disable)\s+(default|recommended)\s+tags?\b", re.IGNORECASE)
NO_QUALITY_RE = re.compile(r"\b(no|without|disable)\s+quality\s+tags?\b", re.IGNORECASE)
NO_NEGATIVE_RE = re.compile(r"\b(no|without|disable)\s+negative\s+(defaults?|tags?)\b", re.IGNORECASE)
NO_RATING_RE = re.compile(r"\b(no|without|disable)\s+(rating|safety)\s+tags?\b", re.IGNORECASE)
NO_SMART_FORMAT_RE = re.compile(r"\b(no|without|disable)\s+smart\s+format(?:ting)?\b", re.IGNORECASE)
NO_DYNAMIC_SMART_FORMAT_RE = re.compile(
    r"\b(no|without|disable)\s+dynamic\s+smart\s+format(?:ting)?\b",
    re.IGNORECASE,
)
RATING_TAGS = {"general", "sensitive", "nsfw", "explicit"}


@dataclass
class PromptResult:
    prompt: str
    negative_prompt: str
    matched_tags: list[str]
    notes: str


def build_prompt(
    db: TagDatabase,
    text: str,
    limit: int = 18,
    min_count: int = 25,
    include_quality: bool | None = None,
    use_ollama: bool | None = None,
    ollama_model: str | None = None,
    ollama_url: str | None = None,
    include_defaults: bool | None = None,
    include_negative: bool = True,
    default_rating: str | None = None,
    model_preset: str | None = None,
    smart_formatting: bool | None = None,
    smart_format_max_fragments: int | None = None,
    dynamic_smart_formatting: bool | None = None,
    dynamic_smart_format_min_fragments: int | None = None,
    dynamic_smart_format_max_fragments: int | None = None,
) -> PromptResult:
    settings = get_settings()
    use_scoring = bool(USE_SCORING_RE.search(text))
    no_defaults = bool(NO_DEFAULTS_RE.search(text))
    no_quality = bool(NO_QUALITY_RE.search(text))
    no_negative = bool(NO_NEGATIVE_RE.search(text))
    no_rating = bool(NO_RATING_RE.search(text))
    no_smart_format = bool(NO_SMART_FORMAT_RE.search(text))
    no_dynamic_smart_format = bool(NO_DYNAMIC_SMART_FORMAT_RE.search(text))
    clean_text = clean_control_phrases(text)

    if include_defaults is None:
        include_defaults = settings.include_defaults
    include_defaults = include_defaults and not no_defaults
    if include_quality is None:
        include_quality = include_defaults
    include_quality = include_quality and include_defaults and not no_quality
    include_negative = include_negative and include_defaults and not no_negative
    if use_ollama is None:
        use_ollama = settings.use_ollama
    if ollama_model is None:
        ollama_model = settings.ollama_model
    if ollama_url is None:
        ollama_url = settings.ollama_url
    if model_preset is None:
        model_preset = settings.model_preset
    preset = get_preset(model_preset)
    if default_rating is None:
        default_rating = settings.default_rating
    default_rating = normalize_rating(default_rating or "")
    if no_rating:
        default_rating = ""
    if smart_formatting is None:
        smart_formatting = settings.smart_formatting
    smart_formatting = smart_formatting and not no_smart_format
    if smart_format_max_fragments is None:
        smart_format_max_fragments = settings.smart_format_max_fragments
    if dynamic_smart_formatting is None:
        dynamic_smart_formatting = settings.dynamic_smart_formatting
    dynamic_smart_formatting = dynamic_smart_formatting and not no_dynamic_smart_format
    if dynamic_smart_format_min_fragments is None:
        dynamic_smart_format_min_fragments = settings.dynamic_smart_format_min_fragments
    if dynamic_smart_format_max_fragments is None:
        dynamic_smart_format_max_fragments = settings.dynamic_smart_format_max_fragments
    smart_format_max_fragments, dynamic_word_count, dynamic_chunk_count = resolve_smart_format_max_fragments(
        clean_text,
        smart_format_max_fragments,
        dynamic_smart_formatting,
        dynamic_smart_format_min_fragments,
        dynamic_smart_format_max_fragments,
    )

    phrases: list[str] = []
    notes: list[str] = []
    notes.append(f"model preset: {preset.label}")
    if smart_formatting and dynamic_smart_formatting and smart_format_max_fragments > 0:
        notes.append(
            "dynamic smart formatting fragments: "
            f"{smart_format_max_fragments} "
            f"(words: {dynamic_word_count}, chunks: {dynamic_chunk_count})"
        )
    if use_ollama:
        try:
            planned_tags = ollama_tag_candidates(clean_text, ollama_model, ollama_url)
            if planned_tags:
                phrases.extend(planned_tags)
                notes.append(f"ollama model: {ollama_model}")
                notes.append("ollama candidates: " + ", ".join(planned_tags))
        except RuntimeError as exc:
            notes.append(str(exc))
            notes.append("fallback: lexical phrase extraction")

    phrases.extend(extract_phrases(clean_text))
    phrases = dedupe(phrases)
    passthrough_tags = extract_passthrough_tags(clean_text, preset.name)

    tags: list[str] = []
    unresolved_phrases: list[str] = []
    seen = set()
    covered_words: set[str] = set()

    for phrase in phrases:
        if is_covered_single_word(phrase, covered_words):
            continue
        rows = db.search(phrase, limit=12, min_count=min_count)
        if not rows:
            notes.append(f"no tag match: {phrase}")
            unresolved_phrases.append(phrase)
            continue
        row = choose_row(phrase, rows)
        if row is None:
            notes.append(f"no precise tag match: {phrase}")
            unresolved_phrases.append(phrase)
            continue
        tag = row["name"]
        if tag in seen:
            continue
        if conflicts_with_existing(tag, seen):
            notes.append(f"skipped conflicting tag: {phrase} -> {tag} ({row['post_count']})")
            continue
        seen.add(tag)
        covered_words.update(words_for_phrase(phrase))
        covered_words.update(words_for_phrase(tag.replace("_", " ")))
        tags.append(tag)
        notes.append(f"{phrase} -> {tag} ({row['post_count']})")
        if len(tags) >= limit:
            break

    score_tags = list(preset.score_tags or SCORE_TAGS)
    positive_defaults = settings.positive_defaults
    negative_defaults = settings.negative_defaults
    if preset.name != "custom":
        positive_defaults = list(preset.positive_defaults)
        negative_defaults = list(preset.negative_defaults)

    prefix = []
    if include_quality:
        prefix.extend(positive_defaults)
    if use_scoring or (include_quality and preset.always_score):
        if preset.name == "wai_anima":
            prefix.extend(score_tags)
        else:
            prefix = score_tags + prefix
    mapped_rating = ""
    explicit_passthrough_rating = any(tag.startswith("rating_") for tag in passthrough_tags)
    if include_defaults and default_rating in RATING_TAGS and not explicit_passthrough_rating:
        mapped_rating = preset.rating_map.get(default_rating, default_rating)
        if mapped_rating:
            prefix.append(mapped_rating)

    prompt_tags = dedupe(prefix + passthrough_tags + tags)
    smart_fragments: list[str] = []
    if smart_formatting and smart_format_max_fragments > 0:
        filtered_unresolved = filter_unresolved_phrases(unresolved_phrases, covered_words)
        if filtered_unresolved:
            try:
                smart_fragments = ollama_smart_fragments(
                    clean_text,
                    prompt_tags,
                    filtered_unresolved,
                    ollama_model,
                    ollama_url,
                    smart_format_max_fragments,
                )
                if smart_fragments:
                    notes.append("smart formatting: " + ", ".join(smart_fragments))
            except RuntimeError as exc:
                notes.append(str(exc))
    prompt_tags = dedupe(prompt_tags + smart_fragments)
    negative_tags = negative_defaults if include_negative else []
    if mapped_rating:
        negative_tags = remove_conflicting_negative_ratings(negative_tags, mapped_rating)
    return PromptResult(", ".join(prompt_tags), ", ".join(dedupe(negative_tags)), tags, "\n".join(notes))


def clean_control_phrases(text: str) -> str:
    out = USE_SCORING_RE.sub(" ", text)
    out = NO_DEFAULTS_RE.sub(" ", out)
    out = NO_QUALITY_RE.sub(" ", out)
    out = NO_NEGATIVE_RE.sub(" ", out)
    out = NO_RATING_RE.sub(" ", out)
    out = NO_SMART_FORMAT_RE.sub(" ", out)
    out = NO_DYNAMIC_SMART_FORMAT_RE.sub(" ", out)
    return out


def resolve_smart_format_max_fragments(
    text: str,
    fixed_max: int | None,
    dynamic: bool,
    minimum: int | None,
    maximum: int | None,
) -> tuple[int, int, int]:
    fixed_max = clamp_int(fixed_max, 0, 100)
    if not dynamic or fixed_max <= 0:
        return fixed_max, 0, 0

    minimum = clamp_int(minimum, 1, 100)
    maximum = clamp_int(maximum, minimum, 100)
    words = re.findall(r"[a-zA-Z0-9_]+", text)
    chunks = [chunk for chunk in re.split(r"[,;\n]+", text) if chunk.strip()]
    estimated = ((len(words) + 11) // 12) + ((len(chunks) + 1) // 2)
    return clamp_int(estimated, minimum, maximum), len(words), len(chunks)


def clamp_int(value: int | None, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value if value is not None else minimum)
    except (TypeError, ValueError):
        parsed = minimum
    return max(minimum, min(maximum, parsed))


def extract_phrases(text: str) -> list[str]:
    text = text.lower().replace("-", " ")
    text = re.sub(r"[^\w\s,()]+", " ", text)
    chunks = [chunk.strip() for chunk in re.split(r"[,;\n]+", text) if chunk.strip()]
    phrases: list[str] = []
    stop = {
        "a",
        "an",
        "the",
        "with",
        "and",
        "or",
        "of",
        "in",
        "on",
        "at",
        "by",
        "to",
        "for",
        "getting",
        "being",
        "gets",
        "get",
        "image",
        "picture",
        "character",
    }
    for chunk in chunks:
        words = [word for word in chunk.split() if word not in stop]
        if not words:
            continue
        for concept in extract_concept_tags(words):
            if concept not in phrases:
                phrases.append(concept)
        for subject in ("girl", "woman", "female", "boy", "man", "male"):
            if subject in words and subject not in phrases:
                phrases.append(subject)
        for compound in extract_visual_compounds(words):
            if compound not in phrases:
                phrases.append(compound)
        phrases.append(" ".join(words))
        for size in (3, 2, 1):
            for i in range(0, max(0, len(words) - size + 1)):
                phrase = " ".join(words[i : i + size])
                if phrase not in phrases:
                    phrases.append(phrase)
    return phrases


def dedupe(values: list[str]) -> list[str]:
    out = []
    seen = set()
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def filter_unresolved_phrases(phrases: list[str], covered_words: set[str]) -> list[str]:
    filtered: list[str] = []
    seen = set()
    for phrase in phrases:
        words = words_for_phrase(phrase)
        if not words:
            continue
        if len(words) == 1 and words.intersection(covered_words):
            continue
        if len(words) == 1 and next(iter(words)) in {"guy", "man", "woman", "boy", "girl"}:
            continue
        if len(words) >= 2 and words.issubset(covered_words):
            continue
        key = " ".join(sorted(words))
        if key in seen:
            continue
        seen.add(key)
        filtered.append(phrase)
    return filtered[:32]


def extract_passthrough_tags(text: str, preset_name: str) -> list[str]:
    if preset_name != "pony_v6":
        return []
    allowed = (
        "source_anime",
        "source_cartoon",
        "source_furry",
        "source_pony",
        "rating_safe",
        "rating_questionable",
        "rating_explicit",
    )
    found: list[str] = []
    normalized = text.lower().replace("-", "_")
    for tag in allowed:
        if re.search(rf"\b{re.escape(tag)}\b", normalized):
            found.append(tag)
    return found


def remove_conflicting_negative_ratings(negative_tags: list[str], positive_rating: str) -> list[str]:
    conflicts = {positive_rating}
    if positive_rating in {"nsfw", "explicit", "rating_questionable", "rating_explicit"}:
        conflicts.update({"nsfw", "rating_questionable", "rating_explicit"})
    if positive_rating == "safe":
        conflicts.add("rating_safe")
    return [tag for tag in negative_tags if tag not in conflicts]


def conflicts_with_existing(tag: str, existing: set[str]) -> bool:
    groups = [
        {"red_eyes", "blue_eyes", "green_eyes", "yellow_eyes", "purple_eyes", "brown_eyes", "black_eyes"},
        {"black_hair", "blonde_hair", "brown_hair", "red_hair", "blue_hair", "white_hair", "pink_hair", "green_hair"},
        {"small_breasts", "medium_breasts", "large_breasts", "huge_breasts"},
    ]
    for group in groups:
        if tag in group and existing.intersection(group):
            return True
    return False


def extract_visual_compounds(words: list[str]) -> list[str]:
    compounds: list[str] = []
    hair_mods = {
        "long",
        "short",
        "black",
        "blonde",
        "brown",
        "red",
        "blue",
        "white",
        "pink",
        "green",
        "purple",
        "silver",
    }
    eye_mods = {"red", "blue", "green", "yellow", "purple", "brown", "black", "pink", "aqua", "grey", "gray"}
    animal_mods = {"cat", "dog", "fox", "wolf", "bunny", "rabbit", "bear", "mouse", "cow", "horse"}
    for index, word in enumerate(words):
        nearby = words[index + 1 : index + 4]
        if word in hair_mods and "hair" in nearby:
            compounds.append(f"{word} hair")
        if word in eye_mods and contains_before_blocker(nearby, "eyes", {"hair", "ears", "tail"}):
            compounds.append(f"{word} eyes")
        if word in animal_mods and "ears" in nearby:
            compounds.append(f"{word} ears")
        if word in animal_mods and "tail" in nearby:
            compounds.append(f"{word} tail")
        if word == "glowing" and "fish" in nearby:
            compounds.append("glowing fish")
    return compounds


def extract_concept_tags(words: list[str]) -> list[str]:
    word_set = set(words)
    concepts: list[str] = []
    if word_set.intersection({"isekai", "isekaid", "isekaied"}) and "truck" in word_set:
        concepts.extend(
            [
                "1boy",
                "truck",
                "road",
                "crash",
                "car_crash",
                "falling",
                "flying",
                "debris",
                "motion_lines",
                "speed_lines",
                "scared",
            ]
        )
    if word_set.intersection({"impact", "collision", "crash"}) and word_set.intersection({"truck", "car", "vehicle"}):
        concepts.extend(["crash", "car_crash", "road", "debris", "motion_lines"])
    if word_set.intersection({"dramatic", "action", "dynamic"}):
        concepts.extend(["motion_lines", "speed_lines"])
    if word_set.intersection({"catgirl", "nekomimi"}):
        concepts.extend(["cat_ears", "tail", "animal_ears"])
    if word_set.intersection({"foxgirl"}):
        concepts.extend(["fox_ears", "tail", "animal_ears"])
    if word_set.intersection({"motorcycle", "motorbike", "bike"}) and word_set.intersection({"girl", "woman", "1girl"}):
        concepts.extend(["1girl", "motorcycle", "on_motorcycle", "riding_motorcycle", "looking_at_viewer"])
    if "mermaid" in word_set and "fish" in word_set:
        concepts.extend(["mermaid", "fish", "underwater"])
    if "glowing" in word_set and "fish" in word_set:
        concepts.append("glowing_fish")
    if word_set.intersection({"boy", "1boy", "guy", "man"}) and "sword" in word_set:
        concepts.extend(["1boy", "sword", "holding_sword"])
    return concepts


def choose_row(phrase: str, rows) -> object | None:
    terms = words_for_phrase(phrase)
    if len(terms) == 1:
        precise = [row for row in rows if is_precise_single_match(phrase, row)]
        precise_general = [row for row in precise if row["category_name"] == "general"]
        if precise_general:
            return precise_general[0]
        return precise[0] if precise else None
    general = [row for row in rows if row["category_name"] == "general"]
    if general:
        return general[0]
    return rows[0]


def is_precise_single_match(phrase: str, row) -> bool:
    phrases = {candidate.lower().replace(" ", "_") for candidate in expand_candidates(phrase)}
    name = str(row["name"]).lower()
    aliases = [alias.strip().lower().replace(" ", "_") for alias in str(row["alias"]).split(",") if alias.strip()]
    return name in phrases or bool(phrases.intersection(aliases))


def is_covered_single_word(phrase: str, covered_words: set[str]) -> bool:
    words = words_for_phrase(phrase)
    return len(words) == 1 and next(iter(words)) in covered_words


def words_for_phrase(phrase: str) -> set[str]:
    return {word for word in re.split(r"[^a-z0-9]+", phrase.lower()) if word}


def contains_before_blocker(words: list[str], target: str, blockers: set[str]) -> bool:
    for word in words:
        if word == target:
            return True
        if word in blockers:
            return False
    return False
