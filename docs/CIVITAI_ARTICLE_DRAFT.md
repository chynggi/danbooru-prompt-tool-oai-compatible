# Natural Language to Danbooru Tags in ComfyUI

## A local prompt builder for WAI-Illustrious, WAI-Anima, Pony, Animagine, NoobAI, and other anime SDXL models

I have been building a ComfyUI workflow for anime/furry SDXL generation, and the
hardest part was not the sampler or the checkpoint. It was prompting.

I wanted to type a normal description like:

```text
mermaid underwater, coral reef, blue hair, glowing fish, bubbles,
sunlight rays, peaceful expression
```

and get something closer to what anime SDXL checkpoints actually understand:

```text
masterpiece, best quality, amazing quality, sensitive, mermaid, underwater,
coral_reef, blue_hair, glowing_fish, bubble, sunlight, sunlight rays,
peaceful expression, gentle bubbles, serene atmosphere
```

So I made a local ComfyUI custom node and prompt tool:

```text
Danbooru Prompt Builder
```

It combines:

- a local Danbooru tag SQLite database
- local Ollama prompt planning
- model-specific prompt presets
- a second LLM pass called Smart Formatting
- visible debug output so you can see what matched and what did not

This is meant for users who like ComfyUI, use booru-trained anime models, and
want a workflow that is easier to inspect than a black-box prompt enhancer.

## The Problem

With SD 1.5, I could often stack keywords and weights until something worked.
With SDXL anime models, that approach started breaking down.

Long natural-language prompts often miss the exact tag vocabulary. Short booru
prompts can be too sparse and lose important relationships, direction, lighting,
and scene intent.

Examples I tested:

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
`sunlight rays`, or `peaceful expression`. That is where Smart Formatting made
the biggest difference.

## How It Works

The node does not simply ask an LLM to write a final prompt.

Instead, it splits the work:

1. Ollama reads your natural-language prompt and proposes candidate tags.
2. A local SQLite database checks those candidates against real Danbooru tags.
3. The resolver expands common concepts, synonyms, and model-specific control
   tags.
4. Smart Formatting sends the unresolved parts back to Ollama and asks for short
   visual fragments.
5. The selected model preset adds quality tags, rating tags, score tags, and
   negative tags.

The debug window shows the process:

```text
ollama candidates: mermaid, underwater, coral_reef, blue_hair, glowing_fish
mermaid -> mermaid
underwater -> underwater
coral_reef -> coral_reef
blue_hair -> blue_hair
glowing_fish -> glowing_fish
smart formatting: sunlight rays, peaceful expression, gentle bubbles
```

That makes it much easier to see whether a bad generation came from:

- the initial prompt
- missing Danbooru tags
- the model preset
- the checkpoint
- the sampler/settings
- or just normal diffusion randomness

## Screenshot

Attach the screenshot here:

```text
Screenshot_20260603_233600.png
```

Suggested caption:

```text
The Danbooru Prompt Builder node inside the master ComfyUI workflow. The node
shows the selected model preset, Smart Formatting controls, final prompt output,
and a debug log of tag matches.
```

## Model Presets

Different anime SDXL families want different prompt recipes, so the node has a
`model_preset` dropdown.

Current presets:

| Preset | Intended model family |
| --- | --- |
| `wai_illustrious` | WAI-Illustrious and most Illustrious finetunes |
| `illustrious_base` | Illustrious XL base and conservative Illustrious derivatives |
| `noobai_xl` | NoobAI XL checkpoints |
| `animagine_xl_4` | Animagine XL 4.0 |
| `kohaku_xl` | Kohaku XL style anime SDXL models |
| `wai_anima` | WAI-Anima / Anima preview, experimental |
| `pony_v6` | Pony Diffusion V6 and Pony derivatives |
| `custom` | Use your own `.env` defaults |

The current tested default is:

```text
wai_illustrious
```

because the workflow was tuned around WAI-Illustrious first.

## WAI-Illustrious Preset

The WAI-Illustrious preset uses:

```text
masterpiece, best quality, amazing quality
```

Negative prompt:

```text
bad quality, worst quality, worst detail, sketch, censor
```

Rating tags:

```text
general, sensitive, nsfw, explicit
```

Optional score control:

```text
score_9, score_8_up, score_7_up, score_6_up
```

Type `use scoring` in your prompt if you want those score tags added.

## WAI-Anima Status

WAI-Anima is interesting because it is not just another Illustrious prompt
recipe. The current WAI-Anima page lists Anima-specific requirements and says
the free Base 1.0 version is planned for June 4, 2026.

The experimental preset currently follows the published prompt recipe:

```text
masterpiece, best quality, score_9, score_8, score_7
```

Negative prompt:

```text
worst quality, low quality, score_1, score_2, score_3, artist name,
blurry, jpeg artifacts, lowres, censor
```

This preset should be treated as experimental until the free checkpoint is
downloaded and tested locally.

## Pony Preset

Pony is handled separately because Pony prompting is not the same as ordinary
Danbooru prompting.

The `pony_v6` preset always adds:

```text
score_9, score_8_up, score_7_up, score_6_up, score_5_up, score_4_up
```

It also preserves Pony special tags that are not normal Danbooru tags:

```text
source_anime, source_cartoon, source_furry, source_pony,
rating_safe, rating_questionable, rating_explicit
```

Example:

```text
fox girl eating ramen at a festival stall, source_anime, rating_safe
```

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

Recommended node wiring:

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

## How To Use It

1. Install the custom node into `ComfyUI/custom_nodes/`.
2. Start Ollama locally if you want LLM tag planning and Smart Formatting.
3. Load the cleaned workflow.
4. Select your `model_preset`.
5. Type a normal prompt.
6. Generate once.
7. Read the debug matches.
8. Edit the prompt if a concept matched badly.
9. Disable Smart Formatting if you want strict tag-only output.

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

## What Improved In Testing

Smart Formatting improved:

- scene coherence
- missing atmospheric details
- relationships that are not clean Danbooru tags
- subject details that the LLM found but SQLite could not resolve
- debug visibility

It did not fully solve:

- face restoration in distant/full-body images
- subject-object ownership mistakes
- cases where a model strongly prefers a different composition

For faces, an advanced user may still want a detail pass such as an ADetailer
style workflow.

## Release Plan

This will be released after:

- WAI-Anima Base 1.0 is available and tested.
- The `wai_anima` preset is tuned from real generations.
- A cleaned public workflow is exported.
- The GitHub README and install steps are finalized.

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
