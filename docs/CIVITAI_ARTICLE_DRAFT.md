# Natural Language to Danbooru Tags in ComfyUI

## A local prompt builder for WAI-Illustrious, WAI-Anima, Pony, Animagine, NoobAI, and other booru-trained anime models

This is a ComfyUI custom node and local prompt tool that turns a normal image
description into a cleaner Danbooru-style prompt.

It is built for people who want to type something natural like:

```text
mermaid underwater, coral reef, blue hair, glowing fish, bubbles,
sunlight rays, peaceful expression
```

and get a prompt closer to what booru-trained anime models understand:

```text
masterpiece, best quality, amazing quality, sensitive, mermaid, underwater,
coral_reef, blue_hair, glowing_fish, bubble, sunlight, sunlight rays,
peaceful expression, gentle bubbles, serene atmosphere
```

The node is called:

```text
Danbooru Prompt Builder
```

It combines:

- a local Danbooru tag SQLite database
- optional local Ollama tag planning
- model-specific prompt presets
- dynamic Smart Formatting for unmatched details
- editable negative prompt base text
- visible debug output for every match and miss

The goal is not to hide prompting behind a black box. The goal is to make the
prompt-building process inspectable, editable, and easier to tune in ComfyUI.

## Screenshot

Attach this screenshot to the Civitai post:

```text
Screenshot_20260605_083422.png
```

Suggested caption:

```text
The Danbooru Prompt Builder inside the grouped ComfyUI master workflow. The node
shows the selected model preset, Ollama settings, dynamic Smart Formatting,
editable negative prompt base, and debug output for tag matches.
```

## Why I Built It

With SD 1.5, I could often stack keywords and weights until something worked.
With newer anime SDXL-style and Anima-style models, that approach became less
reliable.

Long natural-language prompts often miss the exact tag vocabulary. Short booru
prompts can be too sparse and lose relationships, pose direction, lighting, or
scene intent.

Examples that exposed the problem:

```text
boy with sword facing a dragon in ruined castle, fire, smoke,
dramatic lighting, debris, action pose
```

```text
girl on motorcycle, desert road, dust cloud, sunset,
leather jacket, motion blur
```

```text
mermaid underwater, coral reef, blue hair, glowing fish,
bubbles, sunlight rays, peaceful expression
```

Basic tag matching helped, but it still missed details like `facing a dragon`,
`sunlight rays`, or `peaceful expression`. Smart Formatting was added to recover
those details without letting the LLM rewrite the entire prompt blindly.

## How It Works

The node does not simply ask an LLM to write a final prompt.

Instead, it splits the work:

1. Ollama reads the natural-language prompt and proposes candidate tags.
2. A local SQLite database checks those candidates against real Danbooru tags.
3. The resolver expands common concepts, synonyms, and model-specific control
   tags.
4. Smart Formatting sends unresolved pieces back to Ollama and asks for short
   visual fragments.
5. The selected model preset adds quality tags, rating tags, score tags, and
   negative tags.

The debug output shows what happened:

```text
model preset: WAI-Anima / Anima preview
dynamic smart formatting fragments: 4 (words: 0, chunks: 0)
preserved @ style tags: @bluethebone
```

For a longer prompt it may show:

```text
ollama candidates: mermaid, underwater, coral_reef, blue_hair, glowing_fish
mermaid -> mermaid
underwater -> underwater
coral_reef -> coral_reef
blue_hair -> blue_hair
glowing_fish -> glowing_fish
smart formatting: sunlight rays, peaceful expression, gentle bubbles
```

This makes it easier to see whether a weak generation came from:

- the initial user prompt
- a missing Danbooru tag
- an over-broad tag match
- the selected model preset
- the checkpoint itself
- sampler/settings choices
- normal diffusion randomness

## Main Features

- Natural language to Danbooru-style tags.
- Local Danbooru tag database with post-count-aware matching.
- Optional local Ollama support.
- Dynamic Smart Formatting from short prompts to long scene briefs.
- Model presets for WAI-Illustrious, WAI-Anima, Illustrious base, NoobAI,
  Animagine XL 4.0, Kohaku XL, Pony V6, and custom defaults.
- `@style` preservation for Anima models.
- Pony source/rating tag preservation.
- Editable negative prompt base with preset negatives appended afterward.
- Debug output that explains matches, misses, preserved tags, and repair
  fragments.
- CLI support outside ComfyUI.

## Dynamic Smart Formatting

Smart Formatting is the part that improved prompt coherence the most in testing.

Instead of using the same number of repair fragments for every prompt, dynamic
mode estimates prompt complexity from word count and comma/semicolon/newline
chunks. The default range is:

```text
4-20 fragments
```

Short prompts stay compact. Long prompts get more room to preserve atmosphere,
relationships, pose direction, and scene intent.

You can still disable it or force a manual cap.

Prompt phrases:

```text
no smart formatting
no dynamic smart formatting
```

## Editable Negative Prompt Base

The builder has a `negative_prompt_base` field.

This is useful when a model, LoRA, or style tends to produce unwanted artifacts.
For example, some styles may generate good composition but also add jumbled text,
captions, or watermark-like marks.

A practical base to try:

```text
text, subtitles, writing, watermark, logo, signature, caption, speech bubble
```

The output order is:

```text
your editable negative base, preset negative tags
```

If `include_negative` is disabled, only your editable base is sent. This makes
it easy to test handcrafted negatives without losing the field itself.

## WAI-Anima and Anima Style Tags

WAI-Anima / Anima-style models use a different prompt recipe from
WAI-Illustrious and Pony.

The Anima presets use:

```text
masterpiece, best quality, score_9, score_8, score_7
```

Negative defaults:

```text
worst quality, low quality, score_1, score_2, score_3, artist name,
blurry, jpeg artifacts, lowres, censor
```

Anima style tags beginning with `@` are preserved instead of being sent through
normal Danbooru matching.

Supported forms:

```text
@style_token
monster @style_token
(@style_token:1.2)
@artist name, 1girl, forest
```

This prevents the builder from accidentally turning `@style_token` into an
unprefixed Danbooru tag and weakening the intended style behavior.

## Model Presets

Current presets:

| Preset | Intended model family |
| --- | --- |
| `wai_illustrious` | WAI-Illustrious and most Illustrious finetunes |
| `illustrious_base` | Illustrious XL base and conservative Illustrious derivatives |
| `noobai_xl` | NoobAI XL checkpoints |
| `animagine_xl_4` | Animagine XL 4.0 |
| `kohaku_xl` | Kohaku XL style anime SDXL models |
| `anima_base` | Anima Base and Anima-derived models |
| `wai_anima` | WAI-Anima Base 1.0 |
| `pony_v6` | Pony Diffusion V6 and Pony derivatives |
| `custom` | Use your own `.env` defaults |

The default is:

```text
wai_illustrious
```

Use `wai_anima` or `anima_base` for Anima models. Use `pony_v6` for Pony-style
prompting and source/rating tags. Use `custom` if you want only your `.env`
defaults.

## Recommended Workflow Shape

The cleaned public workflow should include:

1. User prompt input.
2. Danbooru Prompt Builder.
3. Debug ShowText node.
4. LoRA trigger/tag section.
5. Positive and negative CLIPTextEncode.
6. Optional ControlNet section.
7. Optional upscale section.
8. Final output/save section.

Recommended wiring:

```text
TextInputBasic
  -> Danbooru Prompt Builder
  -> LoRA Trigger Prompt Builder
  -> CLIPTextEncode positive

Danbooru Prompt Builder negative_prompt
  -> CLIPTextEncode negative

Danbooru Prompt Builder debug_matches
  -> ShowText
```

The final prompt should also be routed into a ShowText node so users can see
exactly what reaches CLIP.

## How To Use It

1. Install the custom node into `ComfyUI/custom_nodes/`.
2. Start Ollama locally if you want LLM tag planning and Smart Formatting.
3. Load the cleaned workflow.
4. Select the correct `model_preset`.
5. Type a normal prompt.
6. Generate once.
7. Read the debug matches.
8. Edit the prompt, negative base, or Smart Formatting settings.
9. Disable Smart Formatting if you want strict tag-only output.

## Prompt Controls

These phrases can be typed directly into the prompt:

```text
use scoring
no default tags
no quality tags
no negative defaults
no rating tags
no smart formatting
no dynamic smart formatting
```

For WAI/Illustrious-style models, `use scoring` adds:

```text
score_9, score_8_up, score_7_up, score_6_up
```

Some presets, such as Pony and Anima, always add their own score tags because
those model families expect a specific score format.

## Example Prompts

```text
use scoring catgirl sitting on a bed in a cozy bedroom, black hair,
red eyes, oversized sweater, soft morning light
```

```text
boy with sword facing a dragon in ruined castle, fire, smoke,
dramatic lighting, debris, action pose
```

```text
girl on motorcycle, desert road, dust cloud, sunset,
leather jacket, motion blur
```

```text
mermaid underwater, coral reef, blue hair, glowing fish,
bubbles, sunlight rays, peaceful expression
```

```text
fox girl eating ramen at a festival stall, yukata, lanterns,
night, steam, happy expression
```

Anima-style example:

```text
@bluethebone, 1girl, forest, soft light, painterly, detailed background
```

Inline Anima-style example:

```text
girl in fear of a monster @bluethebone, dark room, dramatic lighting
```

## What Improved In Testing

Smart Formatting improved:

- scene coherence
- missing atmospheric details
- relationships that are not clean Danbooru tags
- subject details that the LLM found but SQLite could not resolve
- prompt/debug visibility

The editable negative base helped with:

- text artifacts
- captions
- watermark-like marks
- style-specific clutter

It did not fully solve:

- face restoration in distant/full-body images
- subject-object ownership mistakes
- cases where a checkpoint strongly prefers a different composition

For faces, advanced users may still want a detail pass such as an ADetailer-style
workflow.

## Install Notes

The GitHub repo includes:

```text
danbooru_prompt_tool/
comfyui_node/
scripts/
.env.example
README.md
```

The generated SQLite database is not included. Build or sync it locally.

Basic CLI setup:

```bash
cp .env.example .env
python -m danbooru_prompt_tool seed --db data/danbooru_tags.sqlite
```

For a larger local database:

```bash
python -m danbooru_prompt_tool sync-danbooru \
  --db data/danbooru_tags.sqlite \
  --min-count 50
```

Danbooru has rate limits, so the sync command sleeps between requests and can
resume from the last imported tag id.

## Known Limitations

- Presets are best-effort model-family defaults, not official settings from
  every checkpoint author.
- Smart Formatting improves prompt coherence, but it can still add fragments
  that need manual editing.
- The tag database is only as current as your local sync.
- A generated prompt still depends heavily on checkpoint, LoRA, sampler, CFG,
  resolution, seed, and workflow wiring.

## Links

Project repository:

```text
<GitHub URL here>
```

Workflow download:

```text
<Civitai workflow attachment here>
```

Reference pages:

- WAI-Anima: https://civitai.red/models/2544636/wai-anima
- WAI-Illustrious notes: https://test-www.diffus.me/ja/models/wai-nsfw-illustrious-sdxl-v16-0
- Animagine XL 4.0: https://huggingface.co/cagliostrolab/animagine-xl-4.0
- Illustrious XL: https://huggingface.co/OnomaAIResearch/Illustrious-xl-early-release-v0
- Kohaku XL: https://huggingface.co/KBlueLeaf/Kohaku-XL-Zeta

