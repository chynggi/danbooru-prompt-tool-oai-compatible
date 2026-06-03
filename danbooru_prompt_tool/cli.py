from __future__ import annotations

import argparse
from pathlib import Path

from .builder import build_prompt
from .database import TagDatabase


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="danbooru-prompt-tool")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_db(p):
        p.add_argument("--db", default="data/danbooru_tags.sqlite")

    p_seed = sub.add_parser("seed")
    add_db(p_seed)

    p_import = sub.add_parser("import-csv")
    add_db(p_import)
    p_import.add_argument("--csv", required=True)

    p_sync = sub.add_parser("sync-danbooru")
    add_db(p_sync)
    p_sync.add_argument("--min-count", type=int, default=0)
    p_sync.add_argument("--sleep", type=float, default=0.12)
    p_sync.add_argument("--max-pages", type=int, default=0)

    p_prompt = sub.add_parser("prompt")
    add_db(p_prompt)
    p_prompt.add_argument("text")
    p_prompt.add_argument("--limit", type=int, default=18)
    p_prompt.add_argument("--min-count", type=int, default=25)
    p_prompt.add_argument("--no-quality", action="store_true")
    p_prompt.add_argument("--no-defaults", action="store_true")
    p_prompt.add_argument("--no-negative", action="store_true")
    p_prompt.add_argument("--no-ollama", action="store_true")
    p_prompt.add_argument("--ollama-model")
    p_prompt.add_argument("--ollama-url")
    p_prompt.add_argument("--rating", default=None, help="general, sensitive, nsfw, explicit, or empty")
    p_prompt.add_argument("--no-smart-formatting", action="store_true")
    p_prompt.add_argument("--smart-format-max-fragments", type=int, default=None)

    p_search = sub.add_parser("search")
    add_db(p_search)
    p_search.add_argument("text")
    p_search.add_argument("--limit", type=int, default=10)
    p_search.add_argument("--min-count", type=int, default=25)

    args = parser.parse_args(argv)
    db = TagDatabase(args.db)

    if args.cmd == "seed":
        print(f"seeded {db.seed()} tags into {Path(args.db).resolve()}")
    elif args.cmd == "import-csv":
        print(f"imported {db.import_csv(args.csv)} tags into {Path(args.db).resolve()}")
    elif args.cmd == "sync-danbooru":
        count = db.sync_danbooru(args.min_count, args.sleep, max_pages=args.max_pages)
        print(f"synced {count} tags into {Path(args.db).resolve()}")
    elif args.cmd == "prompt":
        result = build_prompt(
            db,
            args.text,
            limit=args.limit,
            min_count=args.min_count,
            include_quality=not args.no_quality,
            include_defaults=not args.no_defaults,
            include_negative=not args.no_negative,
            use_ollama=not args.no_ollama,
            ollama_model=args.ollama_model,
            ollama_url=args.ollama_url,
            default_rating=args.rating,
            smart_formatting=False if args.no_ollama else not args.no_smart_formatting,
            smart_format_max_fragments=args.smart_format_max_fragments,
        )
        print(result.prompt)
        print("\n# negative")
        print(result.negative_prompt)
        if result.notes:
            print("\n# matches")
            print(result.notes)
    elif args.cmd == "search":
        for row in db.search(args.text, args.limit, args.min_count):
            print(f"{row['name']}\t{row['post_count']}\t{row['category_name']}")
    return 0
