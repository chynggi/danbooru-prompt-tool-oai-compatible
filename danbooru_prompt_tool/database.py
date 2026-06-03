from __future__ import annotations

import csv
import json
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


CATEGORY_NAMES = {
    0: "general",
    1: "artist",
    3: "copyright",
    4: "character",
    5: "meta",
}


TAG_SYNONYMS = {
    "outdoor": ["outdoors"],
    "outside": ["outdoors"],
    "open_air": ["outdoors"],
    "butterflies": ["butterfly"],
    "flowers": ["flower"],
    "trees": ["tree"],
    "clouds": ["cloud"],
    "stars": ["starry_sky", "star"],
    "woods": ["forest"],
    "woodland": ["forest"],
    "grassland": ["field", "grass"],
    "impact": ["collision", "imminent_collision", "crash"],
    "hit": ["imminent_hit", "collision"],
    "struck": ["collision", "imminent_collision"],
    "dramatic": ["motion_lines", "speed_lines"],
    "drama": ["motion_lines"],
    "action": ["dynamic_pose", "motion_lines", "speed_lines"],
    "dynamic": ["dynamic_pose", "motion_lines"],
    "movement": ["motion_lines", "motion_blur"],
    "isekai": ["fantasy"],
    "isekaid": ["fantasy"],
    "truck-kun": ["truck", "road", "car_crash"],
    "truckkun": ["truck", "road", "car_crash"],
    "truck_kun": ["truck", "road", "car_crash"],
    "guy": ["1boy", "male"],
    "man": ["1boy", "male"],
    "catgirl": ["cat_ears", "tail", "animal_ears"],
    "cat_girl": ["cat_ears", "tail", "animal_ears"],
    "foxgirl": ["fox_ears", "tail", "animal_ears"],
    "fox_girl": ["fox_ears", "tail", "animal_ears"],
    "wolfgirl": ["wolf_ears", "tail", "animal_ears"],
    "wolf_girl": ["wolf_ears", "tail", "animal_ears"],
    "nekomimi": ["cat_ears"],
    "bike": ["motorcycle"],
    "motorbike": ["motorcycle"],
    "riding_bike": ["riding_motorcycle", "on_motorcycle"],
    "riding_motorbike": ["riding_motorcycle", "on_motorcycle"],
    "glow": ["glowing"],
    "glowing_fish": ["glowing", "fish"],
}


STARTER_TAGS = [
    ("1girl", 0, 4_900_000, "girl,woman,female"),
    ("1boy", 0, 1_400_000, "boy,man,male"),
    ("solo", 0, 4_000_000, "alone,single person"),
    ("long_hair", 0, 3_600_000, "long hair"),
    ("short_hair", 0, 2_500_000, "short hair"),
    ("black_hair", 0, 2_000_000, "black hair"),
    ("blonde_hair", 0, 1_500_000, "blonde hair"),
    ("red_eyes", 0, 1_300_000, "red eyes"),
    ("blue_eyes", 0, 2_200_000, "blue eyes"),
    ("looking_at_viewer", 0, 3_000_000, "looking at viewer,eye contact"),
    ("standing", 0, 1_600_000, "standing"),
    ("sitting", 0, 1_300_000, "sitting,seated"),
    ("dynamic_pose", 0, 80_000, "dynamic pose,action pose"),
    ("smile", 0, 2_000_000, "smile,smiling"),
    ("dress", 0, 1_300_000, "dress"),
    ("school_uniform", 0, 1_100_000, "school uniform"),
    ("outdoors", 0, 1_200_000, "outside,outdoors"),
    ("sunset", 0, 250_000, "sunset,dusk"),
    ("bedroom", 0, 220_000, "bedroom"),
    ("full_body", 0, 800_000, "full body,full-body"),
    ("upper_body", 0, 900_000, "upper body"),
    ("cowboy_shot", 0, 450_000, "cowboy shot,thigh up"),
    ("from_above", 0, 250_000, "from above"),
    ("from_below", 0, 200_000, "from below"),
    ("cat_ears", 0, 650_000, "cat ears,nekomimi"),
    ("tail", 0, 900_000, "tail"),
    ("animal_ears", 0, 1_000_000, "animal ears"),
    ("thick_thighs", 0, 260_000, "thick thighs"),
    ("small_breasts", 0, 520_000, "small breasts"),
    ("large_breasts", 0, 1_300_000, "large breasts,big breasts"),
    ("muscular", 0, 140_000, "muscular,muscles"),
    ("abs", 0, 250_000, "abs,abdominal muscles"),
    ("nude", 0, 1_000_000, "nude,naked"),
]


@dataclass(frozen=True)
class Tag:
    name: str
    category: int
    post_count: int
    alias: str = ""


class TagDatabase:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()

    def init_schema(self) -> None:
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                category INTEGER NOT NULL DEFAULT 0,
                category_name TEXT NOT NULL DEFAULT 'general',
                post_count INTEGER NOT NULL DEFAULT 0,
                alias TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS tags_fts USING fts5(
                name,
                alias,
                content='tags',
                content_rowid='id'
            );
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TRIGGER IF NOT EXISTS tags_ai AFTER INSERT ON tags BEGIN
                INSERT INTO tags_fts(rowid, name, alias) VALUES (new.id, new.name, new.alias);
            END;
            CREATE TRIGGER IF NOT EXISTS tags_ad AFTER DELETE ON tags BEGIN
                INSERT INTO tags_fts(tags_fts, rowid, name, alias)
                VALUES('delete', old.id, old.name, old.alias);
            END;
            CREATE TRIGGER IF NOT EXISTS tags_au AFTER UPDATE ON tags BEGIN
                INSERT INTO tags_fts(tags_fts, rowid, name, alias)
                VALUES('delete', old.id, old.name, old.alias);
                INSERT INTO tags_fts(rowid, name, alias) VALUES (new.id, new.name, new.alias);
            END;
            """
        )
        self.conn.commit()

    def upsert_many(self, tags: Iterable[Tag], source: str) -> int:
        count = 0
        with self.conn:
            for tag in tags:
                category_name = CATEGORY_NAMES.get(tag.category, str(tag.category))
                self.conn.execute(
                    """
                    INSERT INTO tags(name, category, category_name, post_count, alias, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        category=excluded.category,
                        category_name=excluded.category_name,
                        post_count=excluded.post_count,
                        alias=CASE
                            WHEN excluded.alias != '' THEN excluded.alias
                            ELSE tags.alias
                        END,
                        source=excluded.source,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (tag.name, tag.category, category_name, tag.post_count, tag.alias, source),
                )
                count += 1
        return count

    def seed(self) -> int:
        return self.upsert_many((Tag(*row) for row in STARTER_TAGS), "starter")

    def import_csv(self, csv_path: str | Path) -> int:
        def rows():
            with Path(csv_path).open("r", encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    name = row.get("name") or row.get("tag") or row.get("tag string") or row.get("tag_string")
                    if not name:
                        continue
                    count = row.get("post_count") or row.get("count") or row.get("posts") or 0
                    category = row.get("category") or row.get("category_id") or 0
                    alias = row.get("alias") or row.get("aliases") or ""
                    yield Tag(clean_tag(name), int(category), int(float(count or 0)), alias)

        return self.upsert_many(rows(), f"csv:{csv_path}")

    def sync_danbooru(self, min_count: int = 0, sleep: float = 0.12, limit: int = 1000, max_pages: int = 0) -> int:
        before_id = int(self.get_meta("danbooru_before_id", "0"))
        imported = 0
        page = 0
        while True:
            params = {
                "limit": str(limit),
                "search[order]": "date",
                "search[hide_empty]": "yes",
                "search[is_deprecated]": "false",
            }
            if before_id > 0:
                params["search[id]"] = f"<{before_id}"
            if min_count > 0:
                params["search[post_count]"] = f">{min_count - 1}"
            url = "https://danbooru.donmai.us/tags.json?" + urllib.parse.urlencode(params)
            with urllib.request.urlopen(url, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if not data:
                break
            tags = [
                Tag(clean_tag(item["name"]), int(item.get("category") or 0), int(item.get("post_count") or 0), "")
                for item in data
            ]
            imported += self.upsert_many(tags, "danbooru-api")
            before_id = min(int(item["id"]) for item in data)
            self.set_meta("danbooru_before_id", str(before_id))
            page += 1
            if max_pages and page >= max_pages:
                break
            time.sleep(sleep)
        return imported

    def search(self, text: str, limit: int = 8, min_count: int = 25) -> list[sqlite3.Row]:
        text = clean_phrase(text)
        if not text:
            return []
        candidates = []
        for candidate in expand_candidates(text):
            if candidate and candidate not in candidates:
                candidates.append(candidate)
        terms = [part for part in re.split(r"[^a-z0-9_]+", text.lower()) if len(part) > 1]
        if len(terms) == 1:
            for term in expand_candidates(terms[0]):
                if term not in candidates:
                    candidates.append(term)

        rows = []
        seen = set()
        for candidate in candidates:
            exact = self.conn.execute(
                """
                SELECT * FROM tags
                WHERE (name = ? OR alias LIKE ?) AND post_count >= ?
                ORDER BY post_count DESC
                LIMIT ?
                """,
                (candidate, f"%{candidate.replace('_', ' ')}%", min_count, limit),
            ).fetchall()
            for row in exact:
                if row["name"] not in seen:
                    seen.add(row["name"])
                    rows.append(row)

        if len(rows) < limit:
            if len(terms) > 1:
                fts_query = " OR ".join(escape_fts(candidate) for candidate in candidates[:2])
            else:
                fts_query = " OR ".join(escape_fts(term) for term in terms[:6])
            if fts_query:
                fts_rows = self.conn.execute(
                    """
                    SELECT tags.*
                    FROM tags_fts
                    JOIN tags ON tags.id = tags_fts.rowid
                    WHERE tags_fts MATCH ? AND tags.post_count >= ?
                    ORDER BY tags.post_count DESC
                    LIMIT ?
                    """,
                    (fts_query, min_count, limit * 2),
                ).fetchall()
                for row in fts_rows:
                    if row["name"] not in seen:
                        seen.add(row["name"])
                        rows.append(row)
                    if len(rows) >= limit:
                        break
        return rows[:limit]

    def get_meta(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_meta(self, key: str, value: str) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )


def clean_tag(value: str) -> str:
    return clean_phrase(value).replace(" ", "_")


def clean_phrase(value: str) -> str:
    value = value.strip().lower().replace("-", " ")
    value = re.sub(r"[^\w\s()]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def expand_candidates(text: str) -> list[str]:
    clean = clean_phrase(text)
    if not clean:
        return []
    raw = [clean, clean.replace(" ", "_")]
    expanded: list[str] = []
    for candidate in raw:
        for value in expand_single_candidate(candidate):
            if value and value not in expanded:
                expanded.append(value)
    return expanded


def expand_single_candidate(candidate: str) -> list[str]:
    candidate = candidate.lower()
    out = [candidate]
    out.extend(TAG_SYNONYMS.get(candidate, []))
    singular = singularize(candidate)
    if singular != candidate:
        out.append(singular)
        out.extend(TAG_SYNONYMS.get(singular, []))
    return out


def singularize(value: str) -> str:
    if value.endswith("ies") and len(value) > 4:
        return value[:-3] + "y"
    if value.endswith("ves") and len(value) > 4:
        return value[:-3] + "f"
    if value.endswith("ses") and len(value) > 4:
        return value[:-2]
    if value.endswith("s") and not value.endswith(("ss", "us")) and len(value) > 3:
        return value[:-1]
    return value


def escape_fts(value: str) -> str:
    value = re.sub(r'["\']', " ", value)
    return f'"{value}"'
