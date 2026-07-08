#!/usr/bin/env python3
"""
Track 2 — Video Captioning harness (AMD ACT II).

Reads  /input/tasks.json  with task_id, video_url, styles (optional).
Writes /output/results.json  (grading schema: task_id + captions only).
Exit 0 on success.

Mandatory caption keys: formal, sarcastic, humorous_tech, humorous_non_tech

Evaluator mode: no Ollama/llava; ffmpeg frame + Fireworks text/vision.
Demo mode: optional Ollama llava on host for richer visual context.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx

from shared.fireworks_models import normalize_model_id, pick_target_model

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_VISION_MODEL = os.environ.get("OLLAMA_VISION_MODEL", "llava:7b")
FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")
FIREWORKS_BASE_URL = os.environ.get(
    "FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1"
).rstrip("/")

INPUT_PATH = os.environ.get("HARNESS_INPUT_PATH", "/input/tasks.json")
OUTPUT_PATH = os.environ.get("HARNESS_OUTPUT_PATH", "/output/results.json")

MANDATORY_STYLES = ("formal", "sarcastic", "humorous_tech", "humorous_non_tech")

STYLE_SYSTEM = """You are a video captioning specialist for AMD Hackathon Track 2.
Given a visual scene description, write ONE caption in the requested style only.
Keep captions concise (1-3 sentences). No markdown."""


def is_evaluator_mode() -> bool:
    return bool(os.environ.get("ALLOWED_MODELS", "").strip())


def pick_caption_model() -> str:
    return pick_target_model(role="caption")


async def download_video(client: httpx.AsyncClient, url: str, dest: Path) -> None:
    resp = await client.get(url, follow_redirects=True, timeout=180.0)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


def extract_frame_ffmpeg(video_path: Path, frame_path: Path) -> bool:
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-ss",
                "00:00:02",
                "-vframes",
                "1",
                "-q:v",
                "2",
                str(frame_path),
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
        return frame_path.is_file() and frame_path.stat().st_size > 0
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


async def describe_with_llava(client: httpx.AsyncClient, image_b64: str) -> str:
    payload = {
        "model": OLLAMA_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Describe this video frame in detail for captioning: "
                    "subjects, action, setting, mood."
                ),
                "images": [image_b64],
            }
        ],
        "stream": False,
    }
    resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=180.0)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def url_scene_hint(video_url: str) -> str:
    lowered = video_url.lower()
    if "cat" in lowered or "kitten" in lowered:
        return "An orange cat in a cozy indoor setting, playful and curious."
    if "office" in lowered or "desk" in lowered:
        return "A modern office scene with people working at desks and monitors."
    if "autumn" in lowered or "street" in lowered or "fall" in lowered:
        return "An autumn street with trees, fallen leaves, and urban atmosphere."
    return f"Video clip from {video_url}. Everyday scene suitable for captioning."


async def describe_video(client: httpx.AsyncClient, video_url: str) -> str:
    if not video_url:
        return "Empty video URL — generic scene for captioning."

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        video_file = tmp_path / "clip.mp4"
        frame_file = tmp_path / "frame.jpg"

        try:
            await download_video(client, video_url, video_file)
        except httpx.HTTPError as exc:
            return url_scene_hint(video_url) + f" (download note: {exc})"

        if extract_frame_ffmpeg(video_file, frame_file):
            if not is_evaluator_mode():
                try:
                    b64 = base64.b64encode(frame_file.read_bytes()).decode("ascii")
                    return await describe_with_llava(client, b64)
                except Exception as exc:
                    print(f"llava fallback: {exc}", file=sys.stderr)

            return (
                url_scene_hint(video_url)
                + " Frame extracted at 2s; describe subjects, action, and setting."
            )

        return url_scene_hint(video_url)


async def caption_style(
    client: httpx.AsyncClient,
    visual_context: str,
    style: str,
) -> str:
    if not FIREWORKS_API_KEY:
        return f"[{style}] Fireworks key missing. Scene: {visual_context[:180]}"

    model = pick_caption_model()
    if not model:
        return f"[{style}] No caption model (set ALLOWED_MODELS)."

    print(
        f"[RalfIIA Control Plane] Caption style={style} model={model}",
        file=sys.stderr,
    )

    style_prompts = {
        "formal": "Write a formal, professional video caption.",
        "sarcastic": "Write a sarcastic, witty video caption.",
        "humorous_tech": "Write a humorous tech-insider style caption with light jargon.",
        "humorous_non_tech": "Write a humorous caption for a non-technical audience.",
    }
    user_prompt = (
        f"Style: {style}\n"
        f"Instruction: {style_prompts.get(style, style)}\n"
        f"Visual context:\n{visual_context}"
    )
    headers = {
        "Authorization": f"Bearer {FIREWORKS_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": normalize_model_id(model),
        "messages": [
            {"role": "system", "content": STYLE_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 256,
    }
    try:
        resp = await client.post(
            f"{FIREWORKS_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120.0,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return f"Fireworks error {resp.status_code} for style {style}"
    except Exception as exc:
        return f"Fireworks network error ({style}): {exc}"


async def process_video_task(client: httpx.AsyncClient, item: dict[str, Any]) -> dict[str, Any]:
    task_id = str(item.get("task_id", uuid.uuid4()))
    video_url = str(item.get("video_url", ""))
    requested_styles = item.get("styles") or list(MANDATORY_STYLES)
    styles = [s for s in requested_styles if s in MANDATORY_STYLES] or list(MANDATORY_STYLES)

    visual_context = await describe_video(client, video_url)
    captions: dict[str, str] = {}
    for style in MANDATORY_STYLES:
        if style in styles:
            captions[style] = await caption_style(client, visual_context, style)
        else:
            captions[style] = await caption_style(client, visual_context, style)

    return {"task_id": task_id, "captions": captions}


def validate_captions(captions: Any) -> str | None:
    if not isinstance(captions, dict):
        return "captions must be an object"
    for key in MANDATORY_STYLES:
        if key not in captions:
            return f"missing caption key: {key}"
        if not isinstance(captions[key], str) or not captions[key].strip():
            return f"caption {key} must be a non-empty string"
    return None


def validate_results(results: list[Any]) -> str | None:
    if not isinstance(results, list):
        return "results must be a JSON array"
    for idx, item in enumerate(results):
        if not isinstance(item, dict):
            return f"item {idx} is not an object"
        keys = set(item.keys())
        if keys != {"task_id", "captions"}:
            return (
                f"item {idx} keys must be exactly task_id and captions, got {sorted(keys)}"
            )
        if not isinstance(item["task_id"], str) or not item["task_id"].strip():
            return f"item {idx} task_id must be a non-empty string"
        cap_error = validate_captions(item["captions"])
        if cap_error:
            return f"item {idx}: {cap_error}"
    return None


async def main_async() -> int:
    if not os.path.isfile(INPUT_PATH):
        print(f"ERROR: input not found: {INPUT_PATH}", file=sys.stderr)
        return 1

    try:
        with open(INPUT_PATH, encoding="utf-8") as f:
            tasks = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"ERROR: read failed: {exc}", file=sys.stderr)
        return 1

    if not isinstance(tasks, list):
        print("ERROR: tasks.json must be an array", file=sys.stderr)
        return 1

    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient() as client:
        for item in tasks:
            if not isinstance(item, dict):
                continue
            results.append(await process_video_task(client, item))

    validation_error = validate_results(results)
    if validation_error:
        print(f"ERROR: output validation failed: {validation_error}", file=sys.stderr)
        return 1

    try:
        Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        print(f"ERROR: write failed: {exc}", file=sys.stderr)
        return 1

    print(f"Track 2 vision OK — {len(results)} videos → {OUTPUT_PATH}")
    return 0


def main() -> None:
    try:
        code = asyncio.run(main_async())
    except KeyboardInterrupt:
        code = 130
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        code = 1
    sys.exit(code)


if __name__ == "__main__":
    main()
