from __future__ import annotations

import re
from dataclasses import dataclass

from .config import get_settings, normalize_rating
from .database import TagDatabase, expand_candidates
from .ollama import ollama_tag_candidates


SCORE_TAGS = ["score_9", "score_8_up", "score_7_up", "score_6_up"]
USE_SCORING_RE = re.compile(r"\buse\s+scoring\b", re.IGNORECASE)
NO_DEFAULTS_RE = re.compile(r"\b(no|without|disable)\s+(default|recommended)\s+tags?\b", re.IGNORECASE)
NO_QUALITY_RE = re.compile(r"\b(no|without|disable)\s+quality\s+tags?\b", re.IGNORECASE)
NO_NEGATIVE_RE = re.compile(r"\b(no|without|disable)\s+negative\s+(defaults?|tags?)\b", re.IGNORECASE)
NO_RATING_RE = re.compile(r"\b(no|without|disable)\s+(rating|safety)\s+tags?\b", re.IGNORECASE)
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
) -> PromptResult:
    settings = get_settings()
    use_scoring = bool(USE_SCORING_RE.search(text))
    no_defaults = bool(NO_DEFAULTS_RE.search(text))
    no_quality = bool(NO_QUALITY_RE.search(text))
    no_negative = bool(NO_NEGATIVE_RE.search(text))
    no_rating = bool(NO_RATING_RE.search(text))
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
    if default_rating is None:
        default_rating = settings.default_rating
    default_rating = normalize_rating(default_rating or "")
    if no_rating:
        default_rating = ""

    phrases: list[str] = []
    notes: list[str] = []
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

    tags: list[str] = []
    seen = set()
    covered_words: set[str] = set()

    for phrase in phrases:
        if is_covered_single_word(phrase, covered_words):
            continue
        rows = db.search(phrase, limit=12, min_count=min_count)
        if not rows:
            notes.append(f"no tag match: {phrase}")
            continue
        row = choose_row(phrase, rows)
        if row is None:
            notes.append(f"no precise tag match: {phrase}")
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

    prefix = []
    if use_scoring:
        prefix.extend(SCORE_TAGS)
    if include_quality:
        prefix.extend(settings.positive_defaults)
    if include_defaults and default_rating in RATING_TAGS:
        prefix.append(default_rating)

    prompt_tags = dedupe(prefix + tags)
    negative_tags = settings.negative_defaults if include_negative else []
    return PromptResult(", ".join(prompt_tags), ", ".join(dedupe(negative_tags)), tags, "\n".join(notes))


def clean_control_phrases(text: str) -> str:
    out = USE_SCORING_RE.sub(" ", text)
    out = NO_DEFAULTS_RE.sub(" ", out)
    out = NO_QUALITY_RE.sub(" ", out)
    out = NO_NEGATIVE_RE.sub(" ", out)
    out = NO_RATING_RE.sub(" ", out)
    return out


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
