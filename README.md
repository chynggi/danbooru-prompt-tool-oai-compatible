# Danbooru Prompt Tool

Offline Danbooru tag database and prompt helper for Illustrious/WAI-style image
generation.

Goals:

- Store Danbooru tags and post counts locally in SQLite.
- Let a user write natural language and get likely Danbooru tags back.
- Prefer common tags over obscure tags when several matches are possible.
- Add score tags only when the input contains `use scoring`.
- Expose the same logic as a CLI and as a ComfyUI custom node.

## Quick Start

Seed a small starter database:

```bash
python -m danbooru_prompt_tool seed --db data/danbooru_tags.sqlite
```

Build a prompt:

```bash
python -m danbooru_prompt_tool prompt \
  --db data/danbooru_tags.sqlite \
  "use scoring girl with long black hair red eyes standing at sunset"
```

Search tags directly:

```bash
python -m danbooru_prompt_tool search \
  --db data/danbooru_tags.sqlite \
  "long hair"
```

Sync from Danbooru's public API:

```bash
python -m danbooru_prompt_tool sync-danbooru \
  --db data/danbooru_tags.sqlite \
  --min-count 50
```

Import a CSV with `name`, `post_count`/`count`, and optional `category` columns:

```bash
python -m danbooru_prompt_tool import-csv \
  --db data/danbooru_tags.sqlite \
  --csv path/to/danbooru_tags.csv
```

This workspace currently has a local SQLite database at:

```text
data/danbooru_tags.sqlite
```

It was seeded from `data/danbooru_tags.csv`, then completed through the public
Danbooru tag API. Current local count: `1,031,377` tags.

## ComfyUI Connector

This workspace installs a lightweight loader at:

```text
../ComfyUI/custom_nodes/danbooru_prompt_tool/
```

After restarting ComfyUI, add:

```text
Danbooru Prompt Builder
```

Connect your natural-language `TextInputBasic` output into it, then connect
`prompt` into `CLIPTextEncode`.

The node is registered under:

```text
local/prompt
```

If your text contains `use scoring`, the output starts with:

```text
score_9, score_8_up, score_7_up, score_6_up
```

If not, score tags are omitted.

## Data Sources

Supported sources:

- Danbooru API `/tags.json`, paginated by tag id.
- Hugging Face or other CSV exports with tag names and counts.

Danbooru has read-rate limits. The sync command sleeps between requests and can
resume because it stores the last imported tag id in the database.

## Notes

The first version uses lexical matching, aliases, and post-count ranking. It is
designed to be predictable and easy to publish. A later version can add
embeddings or call an LLM with this database as a retrieval tool.
