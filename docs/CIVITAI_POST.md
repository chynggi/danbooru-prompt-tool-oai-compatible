# Civitai Post Draft - Auto Danbooru Builder

## Title

```text
Auto Danbooru Builder - ComfyUI Prompt Helper for WAI-Illustrious, WAI-Anima, Pony, NoobAI, and Animagine
```

## Short Description

```text
A local ComfyUI custom node and CLI tool that turns natural-language image ideas into cleaner Danbooru-style prompts using a local tag database, optional Ollama planning, model presets, Smart Formatting, and visible debug output.
```

## Suggested Tags

```text
ComfyUI, Custom Node, Danbooru, Prompt Helper, Ollama, WAI-Illustrious, WAI-Anima, Pony, NoobAI, Animagine, Anime, Booru Tags
```

## Post Body

Auto Danbooru Builder is a local prompt helper for ComfyUI.

It is designed for anime/booru-trained models where prompt vocabulary matters a lot:

- WAI-Illustrious
- WAI-Anima
- Illustrious derivatives
- NoobAI
- Animagine
- Kohaku XL
- Pony-style models

The node appears in ComfyUI as:

```text
Danbooru Prompt Builder
```

It takes a normal text idea and turns it into a cleaner prompt structure using:

- a local Danbooru SQLite tag database
- optional local Ollama tag planning
- model-specific presets
- positive quality defaults
- negative defaults
- rating tags
- score tag rules
- Smart Formatting for unmatched details
- debug output for every match and miss

## Screenshot

Attach:

```text
Danboruu-tag-builder.png
```

Suggested caption:

```text
The Danbooru Prompt Builder node inside ComfyUI with model preset controls, tag matching, Smart Formatting, editable negative prompt base, and debug output.
```

## Why I Built It

Older SD 1.5 prompting habits do not always transfer cleanly to newer SDXL/anime models.

Long natural-language prompts can be vague. Short tag prompts can be too sparse.

This tool splits the job:

1. Use a local LLM only to suggest possible tags.
2. Verify tags against a local Danbooru database.
3. Add synonyms and common concept expansions.
4. Preserve model-specific control tags.
5. Recover unmatched details with Smart Formatting.
6. Show the final prompt and debug output so nothing is hidden.

The LLM does not get final authority over the prompt. The local tag database remains the source of truth for tag matching.

## Main Features

- Natural language to Danbooru-style tags.
- Local SQLite tag lookup.
- Optional Ollama candidate generation.
- Dynamic Smart Formatting for hard-to-match scene details.
- Model presets for several popular booru-trained model families.
- Anima `@style` tag preservation.
- Pony source/rating tag preservation.
- `use scoring` control phrase for WAI/Illustrious score tags.
- `tag_matching` toggle for manual comma-separated prompts.
- Editable negative prompt base.
- Separate positive, negative, and debug outputs.
- CLI support outside ComfyUI.

## The New Tag Matching Toggle

The node can now skip tag matching while staying active.

Use this when you already wrote a clean comma-separated prompt and only want the node to add:

- quality defaults
- rating tags
- model-specific score tags
- negative output

In the node, disable:

```text
tag_matching
```

Or type this control phrase:

```text
no tag matching
```

This avoids the old problem where bypassing the whole node also removed useful defaults and negative text.

## Smart Formatting

Smart Formatting is a second pass for details that do not map cleanly to Danbooru tags.

Example details that often need help:

- facing another subject
- emotional expression
- lighting mood
- relationship between objects
- action context
- scenic atmosphere

Dynamic Smart Formatting scales the number of repair fragments based on prompt length. Short prompts stay compact; long prompts get more room.

Default dynamic range:

```text
4 - 20 fragments
```

Adjustable range:

```text
1 - 100 fragments
```

## Presets

Included presets:

```text
custom
wai_illustrious
illustrious_base
noobai_xl
animagine_xl_4
kohaku_xl
anima_base
wai_anima
pony_v6
```

For WAI-Illustrious:

```text
masterpiece, best quality, amazing quality
```

For WAI-Anima:

```text
masterpiece, best quality, score_9, score_8, score_7
```

Important: WAI-Anima does not use the same `_up` score format as WAI-Illustrious or Pony.

## Install

Place or link the custom node folder here:

```text
ComfyUI/custom_nodes/danbooru_prompt_tool/
```

Restart ComfyUI.

Add the node:

```text
Danbooru Prompt Builder
```

## Database

The generated SQLite database is not included in the upload.

Create a small starter database:

```bash
python -m danbooru_prompt_tool seed --db data/danbooru_tags.sqlite
```

Or sync/import a larger tag database locally.

## Ollama

Ollama is optional.

Without Ollama, the tool can still do lexical extraction and SQLite tag lookup.

With Ollama, it can propose better first-pass candidates and run Smart Formatting for unmatched details.

## Example Prompt

```text
use scoring, catgirl sitting in a flower garden, black hair, red eyes, soft sunlight, looking at viewer, gentle smile
```

For WAI-Anima, use the Anima preset and avoid `_up` score tags:

```text
1girl, flower garden, long hair, school uniform, soft sunlight, looking at viewer, gentle smile
```

## Recommended Pairing

This pairs well with:

- visible final prompt `ShowText` nodes
- LoRA trigger-word nodes
- image-to-tags workflows
- txt2img and img2img master workflows
- optional ControlNet pose workflows

## Known Limits

This is a prompt helper, not a magic fix for every generation issue.

It will not fully solve:

- low-detail faces in distant shots
- bad hands
- model-specific anatomy problems
- a checkpoint ignoring a concept it does not know well
- every subject/object ownership mistake

Use the debug output to decide whether the problem came from the prompt, the model, a LoRA, ControlNet, or sampling settings.

## License

This project is licensed under:

```text
PolyForm Noncommercial License 1.0.0
```

Forks and contributions are welcome for hobby, research, educational, and other noncommercial use.

Commercial use requires separate permission.

