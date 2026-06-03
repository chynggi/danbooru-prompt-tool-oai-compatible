# Danbooru Prompt Tool

Offline Danbooru tag database and prompt helper for Illustrious/WAI-style image
generation.

Goals:

- Store Danbooru tags and post counts locally in SQLite.
- Let a user write natural language and get likely Danbooru tags back.
- Use a local Ollama model as a planner when enabled, then verify/rank tags
  against the local SQLite database.
- Prefer common tags over obscure tags when several matches are possible.
- Add score tags only when the input contains `use scoring`.
- Expose the same logic as a CLI and as a ComfyUI custom node.

## Configuration

Edit `.env` to choose the local model and defaults:

```env
DANBOORU_PROMPT_USE_OLLAMA=1
DANBOORU_PROMPT_OLLAMA_MODEL=gemma4:e4b
DANBOORU_PROMPT_OLLAMA_URL=http://127.0.0.1:11434
DANBOORU_PROMPT_SMART_FORMATTING=1
DANBOORU_PROMPT_SMART_FORMAT_MAX_FRAGMENTS=4
DANBOORU_PROMPT_INCLUDE_DEFAULTS=1
DANBOORU_PROMPT_DEFAULT_POSITIVE=masterpiece,best quality,amazing quality
DANBOORU_PROMPT_DEFAULT_NEGATIVE=bad quality,worst quality,worst detail,sketch,censor
DANBOORU_PROMPT_DEFAULT_RATING=general
```

Current prompt-building logic:

1. Remove control phrases such as `use scoring`, `no default tags`, and
   `no negative defaults`.
2. If Ollama is enabled, ask the configured model to turn the natural-language
   request into Danbooru-style candidate tags.
3. Resolve those candidates against the local SQLite Danbooru database.
4. Fall back to lexical phrase extraction if Ollama is disabled or unavailable.
5. Normalize common natural-language variants before matching, for example
   `butterflies -> butterfly` and `outdoor -> outdoors`.
6. Rank matches by Danbooru post count and reject obvious conflicts such as
   two different eye colors.
7. If Smart formatting is enabled, send unresolved details back to Ollama and
   append a few short natural-language fragments after the verified tags.
8. Add recommended Illustrious defaults unless the CLI/node disables them or
   the user prompt asks not to use them.

Prompt-level opt-outs:

```text
no default tags
no quality tags
no negative defaults
no rating tags
no smart formatting
```

## Smart Formatting

Smart formatting is the second Ollama pass. The first pass proposes Danbooru
tag candidates, SQLite resolves what it can, and Smart formatting asks Ollama
to recover the important unmatched parts as short prompt fragments.

Example output shape:

```text
score_9, score_8_up, score_7_up, score_6_up, masterpiece, best quality,
amazing quality, nsfw, cat_ears, sitting, bed, bedroom, black_hair, red_eyes,
oversized_sweater, tail, animal_ears, morning, soft morning light, cozy bedroom
```

Use it when a prompt contains relationships or atmosphere that Danbooru tags do
not represent cleanly, such as `facing a dragon`, `soft morning light`,
`peaceful expression`, or `glowing fish around her`.

Turn it off in any of these ways:

```bash
python -m danbooru_prompt_tool prompt --no-smart-formatting "..."
```

```text
no smart formatting
```

Or disable the `smart_formatting` checkbox in the ComfyUI node. The
`smart_format_max_fragments` value controls how many unmatched fragments may be
appended; `4` is the default.

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

The node outputs:

```text
prompt
debug_matches
negative_prompt
```

In the master workflows, `negative_prompt` is wired into the negative
`CLIPTextEncode` node.

The master workflows expose Smart formatting directly on the Danbooru node:

```text
smart_formatting
smart_format_max_fragments
```

The `debug_matches` output shows the exact fragments appended by the second
pass on a line beginning with `smart formatting:`.

## Illustrious / WAI Defaults

Recommended generation settings for Illustrious-family checkpoints:

```text
Steps: 25-40
CFG scale: 5-7
Sampler: Euler a / euler_ancestral
Original dimensions: larger than 1024x1024
Hires upscale: 1.5
Hires steps: 20
Hires upscaler: R-ESRGAN 4x+ Anime6B
Hires denoise: 0.35-0.5
```

The VAE is integrated in the checkpoint setup here; do not add a separate VAE
unless you are deliberately testing a different model family.

Recommended positive defaults:

```text
masterpiece,best quality,amazing quality
```

Recommended negative defaults:

```text
bad quality,worst quality,worst detail,sketch,censor
```

Safety/rating tags used by Illustrious-style datasets:

```text
general
sensitive
nsfw
explicit
```

This tool defaults to `general` as a positive rating tag. To filter
inappropriate content, consciously add `nsfw` to the negative prompt or set the
negative defaults accordingly. To generate with another rating, set
`DANBOORU_PROMPT_DEFAULT_RATING` or use the ComfyUI node's `default_rating`
field.

## Data Sources

Supported sources:

- Danbooru API `/tags.json`, paginated by tag id.
- Hugging Face or other CSV exports with tag names and counts.

Danbooru has read-rate limits. The sync command sleeps between requests and can
resume because it stores the last imported tag id in the database.

## Notes

The LLM does not directly decide the final prompt. It proposes candidates; the
local Danbooru database resolves and ranks the final tags. This keeps the output
predictable and makes the tool publishable without depending on a hosted API.
