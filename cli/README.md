# intuition.py

A command-line tool for generating and working with images via the [Ideogram v4 API](https://ideogram.ai).

---

## Requirements

- Python 3.8+
- The following packages: `requests`, `typer`

```bash
pip install requests typer
```

---

## Authentication

The tool reads your Ideogram API key from the environment. Export it before running any command:

```bash
export IDEOGRAM_API_KEY="your_api_key_here"
```

If the variable is not set, all commands exit immediately with an error.

---

## Overview

```
usage: intuition.py [COMMAND] [OPTIONS]
```

| Command | What it does |
|---|---|
| `gen` | Generate a new image from a text or JSON prompt |
| `remix` | Re-imagine an existing image guided by a text prompt |
| `magic` | Enhance a plain prompt into a structured Ideogram JSON prompt |
| `describe` | Analyse an image and return its structured JSON description |

---

## Commands

### `gen` — Generate an image

Generate a new image from either a plain text prompt or a structured JSON prompt file (typically produced by `magic`).

**Exactly one** of `--text-prompt` or `--json-prompt` must be provided; they are mutually exclusive.

```
intuition.py gen [OPTIONS]
```

| Option | Short | Type | Default | Description |
|---|---|---|---|---|
| `--text-prompt` | `-t` | string | — | Plain natural-language prompt |
| `--json-prompt` | `-j` | path | — | Path to an Ideogram v4 JSON prompt file |
| `--resolution` | `-r` | string | `2048x2048` | Output resolution (Ideogram v4 2 K presets, e.g. `2048x2048`, `1536x2048`) |
| `--speed` | `-s` | string | `default` | Rendering speed: `turbo`, `default`, or `quality` |

> **Note:** The `flash` speed value is currently rejected by the Ideogram v4 API (HTTP 400) and is blocked by the tool. Use `turbo` for the fastest available generation.

**Generated files** are saved in the current working directory with the naming pattern:

```
ideogram_<UTC timestamp>_<seed>[_<index>].<ext>
```

**Examples**

```bash
# Simple text prompt
intuition.py gen -t "A photorealistic red fox in a snowy forest at dusk"

# Specify a landscape resolution and faster speed
intuition.py gen -t "Cyberpunk city skyline" -r 2048x1536 -s turbo

# Use a JSON prompt produced by `magic`
intuition.py gen -j fox_prompt.json

# High-quality square output from a JSON prompt
intuition.py gen -j fox_prompt.json -r 2048x2048 -s quality
```

---

### `remix` — Remix an existing image

Takes an input image and a guiding text prompt, and produces a new image that blends the two. The `--weight` option controls how faithfully the output follows the original image versus the prompt.

```
intuition.py remix [OPTIONS]
```

| Option | Short | Type | Default | Description |
|---|---|---|---|---|
| `--image` | `-i` | path | *(required)* | Input image file. JPEG, PNG, and WebP are supported |
| `--prompt` | `-p` | string | *(required)* | Text prompt that guides the transformation |
| `--weight` | `-w` | integer 1–100 | `50` | Image fidelity weight. Higher values stay closer to the original; lower values follow the prompt more freely |
| `--resolution` | `-r` | string | `2048x2048` | Output resolution |
| `--speed` | `-s` | string | `default` | Rendering speed: `flash`, `turbo`, `default`, or `quality` |

Output files follow the same naming convention as `gen`.

**Examples**

```bash
# Basic remix
intuition.py remix -i photo.jpg -p "Impressionist oil painting style"

# Stay very close to the original image
intuition.py remix -i photo.jpg -p "Impressionist oil painting style" -w 80

# Follow the prompt more freely, use turbo speed
intuition.py remix -i photo.png -p "Neon-lit sci-fi version" -w 20 -s turbo
```

---

### `magic` — Enhance a prompt

Sends a plain-language prompt to the Ideogram Magic Prompt API, which returns a rich structured `json_prompt` optimised for generation. The resolved aspect ratio is printed to **stderr**; the JSON prompt is printed to **stdout** — making it easy to redirect to a file for use with `gen --json-prompt`.

```
intuition.py magic [OPTIONS]
```

| Option | Short | Type | Default | Description |
|---|---|---|---|---|
| `--prompt` | `-p` | string | *(required)* | Plain natural-language prompt to enhance |
| `--aspect-ratio` | `-ar` | string | `AUTO` | Desired aspect ratio hint (e.g. `1:1`, `16:9`, `9:16`, `AUTO`) |

**Examples**

```bash
# Print the enhanced prompt to the terminal
intuition.py magic -p "A red fox in a snowy forest"

# Save the JSON prompt to a file for later use with gen
intuition.py magic -p "A red fox in a snowy forest" > fox_prompt.json

# Hint at a widescreen aspect ratio
intuition.py magic -p "Panoramic mountain landscape" -ar 16:9 > landscape_prompt.json
```

**Two-step workflow — magic → gen**

The intended use of `magic` is to feed its output directly into `gen`:

```bash
# Step 1: enhance the prompt and save it
intuition.py magic -p "A red fox in a snowy forest at dusk" > fox_prompt.json

# Step 2: generate with the enriched JSON prompt
intuition.py gen -j fox_prompt.json -s quality
```

---

### `describe` — Describe an image

Analyses an image file using the Ideogram v4 Describe API and returns its full structured JSON response — including a `json_prompt` that can be used directly with `gen --json-prompt`. Bounding boxes can optionally be included.

The full JSON response is written to **stdout**.

```
intuition.py describe [OPTIONS]
```

| Option | Short | Type | Default | Description |
|---|---|---|---|---|
| `--image` | `-i` | path | *(required)* | Input image file. JPEG, PNG, and WebP are supported |
| `--boxes` / `--no-boxes` | `-b` | flag | `--boxes` | Whether to include bounding boxes in the returned JSON prompt |

**Examples**

```bash
# Describe an image, print JSON to the terminal
intuition.py describe -i photo.jpg

# Save the full description JSON to a file
intuition.py describe -i photo.jpg > photo_description.json

# Describe without bounding boxes
intuition.py describe -i photo.jpg --no-boxes

# Extract just the json_prompt field and use it to regenerate the image
intuition.py describe -i photo.jpg | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(json.dumps(data.get('json_prompt', data), indent=2))
" > regen_prompt.json

intuition.py gen -j regen_prompt.json
```

---

## Common options

### Resolutions

Ideogram v4 supports 2 K preset resolutions. Common values:

| Preset | Aspect ratio |
|---|---|
| `2048x2048` | 1:1 (square) |
| `2048x1536` | 4:3 landscape |
| `1536x2048` | 3:4 portrait |
| `2048x1152` | 16:9 widescreen |
| `1152x2048` | 9:16 portrait / mobile |

### Speed tiers

| Value | Notes |
|---|---|
| `turbo` | Fastest available in v4 |
| `default` | Balanced speed and quality |
| `quality` | Highest quality, slowest |
| `flash` | **Not supported** in v4 Generate (blocked by the tool) |

---

## Error handling

All error messages are written to **stderr** so they don't pollute redirected output. The tool exits with code `1` on any error, including:

- Missing or invalid API key
- HTTP errors from the Ideogram API
- Images flagged as unsafe by the API
- Invalid option values (e.g. unsupported speed)

---

## Quick-reference cheat sheet

```bash
# Generate from text
intuition.py gen -t "prompt text" [-r RESOLUTION] [-s SPEED]

# Generate from JSON prompt file
intuition.py gen -j prompt.json [-r RESOLUTION] [-s SPEED]

# Remix an image
intuition.py remix -i image.jpg -p "prompt text" [-w 1-100] [-r RESOLUTION] [-s SPEED]

# Enhance a prompt → save JSON → generate
intuition.py magic -p "prompt text" [-ar RATIO] > prompt.json
intuition.py gen -j prompt.json

# Describe an image → save JSON
intuition.py describe -i image.jpg [--no-boxes] > description.json
```
