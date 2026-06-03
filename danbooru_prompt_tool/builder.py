from __future__ import annotations

import re
from dataclasses import dataclass

from .database import TagDatabase


SCORE_TAGS = ["score_9", "score_8_up", "score_7_up", "score_6_up"]
QUALITY_TAGS = ["masterpiece", "best quality", "amazing quality", "newest"]
USE_SCORING_RE = re.compile(r"\buse\s+scoring\b", re.IGNORECASE)


@dataclass
class PromptResult:
    prompt: str
    matched_tags: list[str]
    notes: str


def build_prompt(
    db: TagDatabase,
    text: str,
    limit: int = 18,
    min_count: int = 25,
    include_quality: bool = True,
) -> PromptResult:
    use_scoring = bool(USE_SCORING_RE.search(text))
    clean_text = USE_SCORING_RE.sub(" ", text)
    phrases = extract_phrases(clean_text)

    tags: list[str] = []
    notes: list[str] = []
    seen = set()
    covered_words: set[str] = set()

    for phrase in phrases:
        if is_covered_single_word(phrase, covered_words):
            continue
        rows = db.search(phrase, limit=4, min_count=min_count)
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
        prefix.extend(QUALITY_TAGS)

    prompt_tags = dedupe(prefix + tags)
    return PromptResult(", ".join(prompt_tags), tags, "\n".join(notes))


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
        "to",
        "for",
        "image",
        "picture",
        "character",
    }
    for chunk in chunks:
        words = [word for word in chunk.split() if word not in stop]
        if not words:
            continue
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


def choose_row(phrase: str, rows) -> object | None:
    terms = words_for_phrase(phrase)
    if len(terms) == 1:
        precise = [row for row in rows if is_precise_single_match(phrase, row)]
        return precise[0] if precise else None
    return rows[0]


def is_precise_single_match(phrase: str, row) -> bool:
    phrase = phrase.lower().replace(" ", "_")
    name = str(row["name"]).lower()
    aliases = [alias.strip().lower().replace(" ", "_") for alias in str(row["alias"]).split(",") if alias.strip()]
    return name == phrase or phrase in aliases


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
