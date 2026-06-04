# Danbooru Prompt Tool

Turn a plain-language image idea into a cleaner anime/booru prompt for ComfyUI.

This tool uses a local Danbooru tag database plus an optional local Ollama model.
The LLM proposes candidate tags, SQLite verifies them against real tag counts,
and Smart Formatting repairs the pieces that do not map cleanly to tags.

![ComfyUI Danbooru Prompt Builder](Screenshot_20260603_233600.png)

## What It Does

- Converts natural language into Danbooru-style tags.
- Ranks tag matches by local Danbooru post counts.
- Shows a debug log explaining every match and miss.
- Adds model-specific positive, negative, score, and rating tags through presets.
- Preserves special tags for Pony-style models, such as `source_anime` and
  `rating_explicit`.
- Adds `score_9, score_8_up, score_7_up, score_6_up` only when the prompt says
  `use scoring`, except for presets where score tags are required.
- Runs inside ComfyUI as `Danbooru Prompt Builder`.
- Also works from the command line.

## Why This Exists

SDXL anime models are less forgiving than older SD 1.5 workflows. A long natural
sentence often contains concepts that do not exist as clean Danbooru tags, while
short booru prompts can miss relationships, pose direction, lighting, or scene
intent.

This tool splits the job:

1. Ollama reads your natural-language idea and proposes likely tags.
2. SQLite checks those tags against a local Danbooru tag database.
3. The resolver adds synonyms, common concept expansions, and conflict checks.
4. Smart Formatting asks Ollama to recover the still-unmatched details as short
   natural-language prompt fragments.
5. The selected model preset adds the correct quality, rating, and negative tags.

The LLM does not get final authority over the prompt. The database remains the
source of truth for tag matching.

## Current Status

This is a working local tool, but it is still tuned from practical testing rather
than a broad public benchmark.

Known strengths:

- WAI-Illustrious and Illustrious-style anime/furry prompting.
- Prompt coherence improvements from Smart Formatting.
- Debuggability: you can see which words matched and which did not.
- ComfyUI workflows where you want to copy, edit, and iterate on prompts.

Known limitations:

- It is not a replacement for face/detail fixers such as ADetailer-style passes.
- It does not guarantee perfect subject ownership, for example who holds a sword.
- Model presets are best-effort defaults. Always prefer a checkpoint author's
  latest model card when it conflicts with this README.
- WAI-Anima Base 1.0 is supported through the `wai_anima` preset, but it uses a
  different score format from WAI-Illustrious and Pony.

## Requirements

- Python 3.10 or newer.
- A local Danbooru tag SQLite database created by this tool.
- Optional: Ollama running locally for LLM candidate extraction and Smart
  Formatting.
- Optional: ComfyUI for the custom node workflow.

Tested locally with:

- ComfyUI `0.22.0`
- Ollama model `gemma4:e4b`
- WAI-Illustrious SDXL workflow

## Quick Start

Clone the repo and enter it:

```bash
git clone <your-repo-url>
cd danbooru-prompt-tool
```

Create or edit `.env`:

```bash
cp .env.example .env
```

Seed a small starter database:

```bash
python -m danbooru_prompt_tool seed --db data/danbooru_tags.sqlite
```

Build a prompt:

```bash
python -m danbooru_prompt_tool prompt \
  --db data/danbooru_tags.sqlite \
  "use scoring catgirl sitting on a bed, black hair, red eyes, soft morning light"
```

Search tags directly:

```bash
python -m danbooru_prompt_tool search \
  --db data/danbooru_tags.sqlite \
  "long hair"
```

For production use, import a full tag CSV or sync from Danbooru:

```bash
python -m danbooru_prompt_tool sync-danbooru \
  --db data/danbooru_tags.sqlite \
  --min-count 50
```

Danbooru has rate limits. The sync command sleeps between requests and resumes
from the last imported tag id.

## Configuration

`.env.example` contains the main settings:

```env
DANBOORU_PROMPT_MODEL_PRESET=wai_illustrious
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

Use `DANBOORU_PROMPT_MODEL_PRESET=custom` if you want only the explicit `.env`
positive and negative defaults.

## ComfyUI Setup

Install or link this folder into ComfyUI:

```text
ComfyUI/custom_nodes/danbooru_prompt_tool/
```

Restart ComfyUI. Add this node:

```text
Danbooru Prompt Builder
```

Typical wiring:

```text
TextInputBasic -> Danbooru Prompt Builder -> LoRA Trigger Prompt Builder -> CLIPTextEncode
Danbooru Prompt Builder negative_prompt -> negative CLIPTextEncode
Danbooru Prompt Builder debug_matches -> ShowText
```

The node outputs:

```text
prompt
debug_matches
negative_prompt
```

Useful controls:

- `model_preset`: model family preset.
- `use_ollama`: first-pass LLM tag candidate extraction.
- `smart_formatting`: second-pass repair for unmatched details.
- `smart_format_max_fragments`: number of natural-language repair fragments.
- `default_rating`: rating tag to inject through the preset.
- `include_quality`: include preset quality tags.
- `include_negative`: output preset negative prompt.

## Smart Formatting

Smart Formatting is the part that improved prompt coherence the most in local
testing.

Example input:

```text
mermaid underwater, coral reef, blue hair, glowing fish, bubbles,
sunlight rays, peaceful expression
```

Example final prompt shape:

```text
masterpiece, best quality, amazing quality, sensitive, mermaid, underwater,
coral_reef, blue_hair, glowing_fish, bubble, sunlight, sunlight rays,
peaceful expression, gentle bubbles, serene atmosphere
```

Turn it off in the node, with the CLI flag, or inside the prompt:

```bash
python -m danbooru_prompt_tool prompt --no-smart-formatting "..."
```

```text
no smart formatting
```

## Prompt Controls

These phrases can be typed directly into the user prompt:

```text
use scoring
no default tags
no quality tags
no negative defaults
no rating tags
no smart formatting
```

`use scoring` adds the WAI/Illustrious-style score prefix:

```text
score_9, score_8_up, score_7_up, score_6_up
```

Some presets always add their own score tags because the model family expects
them.

## Model Presets

Available presets:

```text
custom
wai_illustrious
illustrious_base
noobai_xl
animagine_xl_4
kohaku_xl
wai_anima
pony_v6
```

Use a preset from the CLI:

```bash
python -m danbooru_prompt_tool prompt \
  --db data/danbooru_tags.sqlite \
  --model-preset animagine_xl_4 \
  "1girl with long black hair red eyes standing at sunset"
```

Preset guide:

| Preset | Best For | Positive Defaults | Negative Defaults | Rating Tags |
| --- | --- | --- | --- | --- |
| `wai_illustrious` | WAI-Illustrious and most Illustrious finetunes | `masterpiece, best quality, amazing quality` | `bad quality, worst quality, worst detail, sketch, censor` | `general`, `sensitive`, `nsfw`, `explicit` |
| `illustrious_base` | Illustrious XL base and conservative derivatives | `masterpiece, best quality` | `worst quality, comic, multiple views, bad quality, low quality, lowres, displeasing, very displeasing, bad anatomy, bad hands, scan artifacts, monochrome, greyscale, signature, twitter username, jpeg artifacts, 2koma, 4koma, guro, extra digits, fewer digits` | `general`, `sensitive`, `nsfw`, `explicit` |
| `noobai_xl` | NoobAI XL checkpoints | `masterpiece, best quality, newest, absurdres, highres` | `nsfw, worst quality, old, early, low quality, lowres, signature, username, logo, bad hands, mutated hands, mammal, anthro, furry, ambiguous form, feral, semi-anthro` | `safe`, `sensitive`, `nsfw`, `explicit` |
| `animagine_xl_4` | Animagine XL 4.0 | `masterpiece, high score, great score, absurdres` | `lowres, bad anatomy, bad hands, text, error, missing finger, extra digits, fewer digits, cropped, worst quality, low quality, low score, bad score, average score, signature, watermark, username, blurry` | `safe`, `sensitive`, `nsfw`, `explicit` |
| `kohaku_xl` | Kohaku XL and related booru anime SDXL models | `masterpiece, best quality, great quality` | `low quality, worst quality, lowres, bad anatomy, bad hands, signature, watermark` | `safe`, `sensitive`, `nsfw`, `explicit` |
| `wai_anima` | WAI-Anima Base 1.0 | `masterpiece, best quality, score_9, score_8, score_7` | `worst quality, low quality, score_1, score_2, score_3, artist name, blurry, jpeg artifacts, lowres, censor` | `general`, `sensitive`, `nsfw`, `explicit` |
| `pony_v6` | Pony Diffusion V6 and Pony derivatives | `score_9, score_8_up, score_7_up, score_6_up, score_5_up, score_4_up` | None by default; try `score_5, score_4, score_3, score_2, score_1, bad quality, low quality, bad anatomy, bad hands` if needed | `rating_safe`, `rating_questionable`, `rating_explicit` |
| `custom` | Any model with a special recipe | Uses `.env` defaults | Uses `.env` defaults | Uses `.env` defaults |

Notes:

- `wai_illustrious` is the default because it matches the tested local workflow.
- `wai_anima` is not SDXL and should not use WAI/Pony `_up` score tags. Keep
  `score_9, score_8, score_7` in that exact Anima form.
- `pony_v6` preserves Pony source and rating tags, including `source_anime`,
  `source_cartoon`, `source_furry`, `source_pony`, `rating_safe`,
  `rating_questionable`, and `rating_explicit`.
- `noobai_xl` removes conflicting negative rating tags when `nsfw` or `explicit`
  is selected.

## Model Reference Links

- [WAI-NSFW-illustrious-SDXL v16 notes](https://test-www.diffus.me/ja/models/wai-nsfw-illustrious-sdxl-v16-0)
- [WAI-Anima on Civitai](https://civitai.red/models/2544636/wai-anima)
- [Illustrious XL Early Release on Hugging Face](https://huggingface.co/OnomaAIResearch/Illustrious-xl-early-release-v0)
- [NoobAI XL on Hugging Face](https://huggingface.co/Laxhar/noobai-XL-1.1)
- [NoobAI XL SeaArt guide](https://docs.seaart.ai/guide-1/6-permanent-events/high-quality-models-recommendation/noobai-xl)
- [Animagine XL 4.0 on Hugging Face](https://huggingface.co/cagliostrolab/animagine-xl-4.0)
- [Pony Diffusion V6 XL prompt guide](https://stable-diffusion-art.com/pony-diffusion-v6-xl/)
- [Kohaku XL on Hugging Face](https://huggingface.co/KBlueLeaf/Kohaku-XL-Zeta)

## Example Prompts

```text
use scoring catgirl sitting on a bed in a cozy bedroom, black hair, red eyes,
oversized sweater, soft morning light
```

```text
boy with sword facing a dragon in ruined castle, fire, smoke, dramatic lighting,
debris, action pose
```

```text
mermaid underwater, coral reef, blue hair, glowing fish, bubbles, sunlight rays,
peaceful expression
```

```text
fox girl eating ramen at a festival stall, yukata, lanterns, night, steam,
happy expression
```

## Development Notes

The local test database currently contains over one million Danbooru tags. The
database file is not intended to be committed to GitHub. Publish scripts and
instructions, not the generated SQLite database.

Useful checks:

```bash
python -m compileall danbooru_prompt_tool comfyui_node
python -m danbooru_prompt_tool prompt --db data/danbooru_tags.sqlite --no-ollama "catgirl black hair red eyes"
```

## Roadmap Before Public Release

- Test the released WAI-Anima Base 1.0 checkpoint and tune `wai_anima`.
- Attach a cleaned public workflow JSON for Civitai users.
- Add a short install video or image guide if needed.
- Add packaging metadata if this should be installed through pip later.

## License

Add a license before publishing publicly. If you plan to accept outside
contributions, choose the license before opening pull requests.
