#!/usr/bin/env python3

import json
import mimetypes
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
import typer


app = typer.Typer(help="CLI for Ideogram v4 API.")

API_BASE = "https://api.ideogram.ai/v1"

GENERATE_URL = f"{API_BASE}/ideogram-v4/generate"
REMIX_URL = f"{API_BASE}/ideogram-v4/remix"
MAGIC_URL = f"{API_BASE}/ideogram-v4/magic-prompt"
DESCRIBE_URL = f"{API_BASE}/ideogram-v4/describe"


def get_api_key() -> str:
    api_key = os.getenv("IDEOGRAM_API_KEY")
    if not api_key:
        typer.echo(
            "Error: IDEOGRAM_API_KEY environment variable is not set.",
            err=True,
        )
        raise typer.Exit(1)
    return api_key


def auth_headers() -> dict:
    return {"Api-Key": get_api_key()}


def fail_response(response: requests.Response) -> None:
    typer.echo(f"Error: HTTP {response.status_code}", err=True)
    try:
        typer.echo(json.dumps(response.json(), indent=2), err=True)
    except Exception:
        typer.echo(response.text, err=True)
    raise typer.Exit(1)


def guess_extension(response: requests.Response, url: str) -> str:
    content_type = response.headers.get("Content-Type", "").split(";")[0].strip()

    if content_type:
        ext = mimetypes.guess_extension(content_type)
        if ext:
            if ext == ".jpe":
                return ".jpg"
            return ext

    path = urlparse(url).path
    suffix = Path(path).suffix
    if suffix:
        return suffix

    return ".jpg"


def download_image(url: str, seed: object, index: int = 0) -> Path:
    response = requests.get(url, timeout=120)

    if not response.ok:
        typer.echo(f"Error downloading image: HTTP {response.status_code}", err=True)
        typer.echo(response.text, err=True)
        raise typer.Exit(1)

    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    ext = guess_extension(response, url)

    suffix = f"_{index}" if index else ""
    filename = f"ideogram_{now}_{seed}{suffix}{ext}"
    path = Path.cwd() / filename

    path.write_bytes(response.content)
    return path


def handle_image_response(response: requests.Response) -> None:
    if not response.ok:
        fail_response(response)

    payload = response.json()
    data = payload.get("data", [])

    if not data:
        typer.echo("Error: response contained no image data.", err=True)
        raise typer.Exit(1)

    for index, image_obj in enumerate(data):
        is_safe = image_obj.get("is_image_safe")
        seed = image_obj.get("seed", "unknown_seed")
        url = image_obj.get("url")

        if is_safe is False:
            typer.echo(
                f"Error: generated image with seed {seed} was marked unsafe. "
                "Not downloading.",
                err=True,
            )
            continue

        if not url:
            typer.echo(
                f"Error: image object with seed {seed} did not contain a URL.",
                err=True,
            )
            continue

        output_path = download_image(url, seed=seed, index=index)
        typer.echo(f"Downloaded: {output_path}")


def normalize_speed(speed: str) -> str:
    value = speed.upper()
    allowed = {"FLASH", "TURBO", "DEFAULT", "QUALITY"}
    if value not in allowed:
        typer.echo(
            f"Error: invalid speed '{speed}'. Use one of: "
            "flash, turbo, default, quality.",
            err=True,
        )
        raise typer.Exit(1)
    return value


@app.command("gen")
def generate(
    text_prompt: Optional[str] = typer.Option(
        None,
        "-t",
        "--text-prompt",
        help="Natural-language prompt. Mutually exclusive with --json-prompt.",
    ),
    json_prompt_file: Optional[Path] = typer.Option(
        None,
        "-j",
        "--json-prompt",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to Ideogram v4 JSON prompt file. Mutually exclusive with --text-prompt.",
    ),
    resolution: str = typer.Option(
        "2048x2048",
        "-r",
        "--resolution",
        help="Ideogram v4 2K resolution, e.g. 2048x2048.",
    ),
    speed: str = typer.Option(
        "default",
        "-s",
        "--speed",
        help="Rendering speed: flash, turbo, default, quality.",
    ),
):
    """
    Generate an image using Ideogram v4.
    """

    if bool(text_prompt) == bool(json_prompt_file):
        typer.echo(
            "Error: provide exactly one of --text-prompt or --json-prompt.",
            err=True,
        )
        raise typer.Exit(1)

    rendering_speed = normalize_speed(speed)

    if rendering_speed == "FLASH":
        typer.echo(
            "Error: Ideogram v4 Generate currently returns HTTP 400 for "
            "rendering_speed=FLASH. Use turbo, default, or quality.",
            err=True,
        )
        raise typer.Exit(1)

    multipart_fields = {
        "resolution": (None, resolution),
        "rendering_speed": (None, rendering_speed),
    }

    if text_prompt:
        multipart_fields["text_prompt"] = (None, text_prompt)
    else:
        with json_prompt_file.open("r", encoding="utf-8") as f:
            json_prompt = json.load(f)
        multipart_fields["json_prompt"] = (
            None,
            json.dumps(json_prompt),
            "application/json",
        )

    response = requests.post(
        GENERATE_URL,
        headers=auth_headers(),
        files=multipart_fields,
        timeout=300,
    )

    handle_image_response(response)


@app.command("remix")
def remix(
    image: Path = typer.Option(
        ...,
        "-i",
        "--image",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Input image. JPEG, PNG, and WebP are supported by the API.",
    ),
    prompt: str = typer.Option(
        ...,
        "-p",
        "--prompt",
        help="Text prompt that guides the remix. Maps to text_prompt.",
    ),
    weight: int = typer.Option(
        50,
        "-w",
        "--weight",
        min=1,
        max=100,
        help="How strongly output should resemble input image. Range: 1-100.",
    ),
    resolution: str = typer.Option(
        "2048x2048",
        "-r",
        "--resolution",
        help="Ideogram v4 2K resolution, e.g. 2048x2048.",
    ),
    speed: str = typer.Option(
        "default",
        "-s",
        "--speed",
        help="Rendering speed: flash, turbo, default, quality.",
    ),
):
    """
    Remix an image using Ideogram v4.
    """

    rendering_speed = normalize_speed(speed)

    mime_type = mimetypes.guess_type(str(image))[0] or "application/octet-stream"

    with image.open("rb") as image_file:
        multipart_fields = {
            "image": (image.name, image_file, mime_type),
            "text_prompt": (None, prompt),
            "image_weight": (None, str(weight)),
            "resolution": (None, resolution),
            "rendering_speed": (None, rendering_speed),
        }

        response = requests.post(
            REMIX_URL,
            headers=auth_headers(),
            files=multipart_fields,
            timeout=300,
        )

    handle_image_response(response)


@app.command("magic")
def magic(
    prompt: str = typer.Option(
        ...,
        "-p",
        "--prompt",
        help="Natural-language prompt to enhance.",
    ),
    aspect_ratio: str = typer.Option(
        "AUTO",
        "-ar",
        "--aspect-ratio",
        help="Target aspect ratio. Defaults to AUTO.",
    ),
):
    """
    Generate an Ideogram v4 magic prompt.

    Writes json_prompt to stdout so it can be redirected to a file.
    Writes the resolved aspect ratio to stderr.
    """

    body = {
        "text_prompt": prompt,
        "aspect_ratio": aspect_ratio,
    }

    response = requests.post(
        MAGIC_URL,
        headers={**auth_headers(), "Content-Type": "application/json"},
        json=body,
        timeout=120,
    )

    if not response.ok:
        fail_response(response)

    payload = response.json()

    resolved_aspect_ratio = payload.get("aspect_ratio")
    json_prompt = payload.get("json_prompt")

    if resolved_aspect_ratio:
        typer.echo(f"Resolved aspect ratio: {resolved_aspect_ratio}", err=True)

    if json_prompt is None:
        typer.echo("Error: response did not contain json_prompt.", err=True)
        raise typer.Exit(1)

    typer.echo(json.dumps(json_prompt, indent=2, ensure_ascii=False))


@app.command("describe")
def describe(
    image: Path = typer.Option(
        ...,
        "-i",
        "--image",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Input image. JPEG, PNG, and WebP are supported by the API.",
    ),
    boxes: bool = typer.Option(
        True,
        "-b",
        "--boxes/--no-boxes",
        help="Whether to include bounding boxes in the returned JSON prompt.",
    ),
):
    """
    Describe an image using Ideogram v4.

    Writes the full JSON response to stdout.
    """

    mime_type = mimetypes.guess_type(str(image))[0] or "application/octet-stream"

    with image.open("rb") as image_file:
        multipart_fields = {
            "image_file": (image.name, image_file, mime_type),
            "include_bbox": (None, str(boxes).lower()),
        }

        response = requests.post(
            DESCRIBE_URL,
            headers=auth_headers(),
            files=multipart_fields,
            timeout=300,
        )

    if not response.ok:
        fail_response(response)

    typer.echo(json.dumps(response.json(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    app()
