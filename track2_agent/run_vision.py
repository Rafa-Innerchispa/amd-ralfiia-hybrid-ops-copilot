#!/usr/bin/env python3
"""
Track 2 — Video Captioning harness (AMD ACT II).

Reads  /input/tasks.json  with video_url + styles (optional).
Uses Ollama llava:7b for visual context, Fireworks for 4 caption styles.
Writes /output/results.json
Exit 0 on success.

Mandatory styles: formal, sarcastic, humorous_tech, humorous_non_tech
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

import httpx

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_VISION_MODEL = os.environ.get("OLLAMA_VISION_MODEL", "llava:7b")
FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")
FIREWORKS_BASE_URL = os.environ.get(
    "FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1"
).rstrip("/")
FIREWORKS_CAPTION_MODEL = os.environ.get(
    "FIREWORKS_CAPTION_MODEL", "accounts/fireworks/models/gemma-2-9b-it"
)

INPUT_PATH = os.environ.get("HARNESS_INPUT_PATH", "/input/tasks.json")
OUTPUT_PATH = os.environ.get("HARNESS_OUTPUT_PATH", "/output/results.json")

MANDATORY_STYLES = ("formal", "sarcastic", "humorous_tech", "humorous_non_tech")

STYLE_SYSTEM = """You are a video captioning specialist for AMD Hackathon Track 2.
Given a visual scene description, write ONE caption in the requested style only.
Keep captions concise (1-3 sentences). No markdown."""


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
                "content": "Describe this video frame in detail for captioning: subjects, action, setting, mood.",
                "images": [image_b64],
            }
        ],
        "stream": False,
    }
    resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=180.0)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


async def describe_video(client: httpx.AsyncClient, video_url: str) -> str:
    """Download video, extract frame, run llava — fallback to URL context."""
    if not video_url:
        return "Empty video URL — no visual context."

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        video_file = tmp_path / "clip.mp4"
        frame_file = tmp_path / "frame.jpg"

        try:
            await download_video(client, video_url, video_file)
        except httpx.HTTPError as exc:
            return f"Video download failed ({video_url}): {exc}"

        if extract_frame_ffmpeg(video_file, frame_file):
            try:
                b64 = base64.b64encode(frame_file.read_bytes()).decode("ascii")
                return await describe_with_llava(client, b64)
            except (httpx.HTTPError, KeyError, json.JSONDecodeError) as exc:
                return f"Llava error after frame extract: {exc}"

        return (
            f"Video at {video_url} downloaded but ffmpeg frame extract unavailable. "
            "Describe a generic tech demo scene for captioning."
        )


async def caption_style(
    client: httpx.AsyncClient,
    visual_context: str,
    style: str,
) -> str:
    if not FIREWORKS_API_KEY:
        return f"[{style}] Local fallback — Fireworks key missing. Scene: {visual_context[:200]}"

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
        "model": FIREWORKS_CAPTION_MODEL,
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
    except httpx.HTTPError as exc:
        return f"Fireworks network error ({style}): {exc}"
    except (KeyError, json.JSONDecodeError) as exc:
        return f"Fireworks parse error ({style}): {exc}"


async def process_video_task(client: httpx.AsyncClient, item: dict[str, Any]) -> dict[str, Any]:
    task_id = str(item.get("task_id", uuid.uuid4()))
    video_url = str(item.get("video_url", ""))
    requested_styles = item.get("styles") or list(MANDATORY_STYLES)
    styles = [s for s in requested_styles if s in MANDATORY_STYLES]
    if not styles:
        styles = list(MANDATORY_STYLES)

    visual_context = await describe_video(client, video_url)
    captions: dict[str, str] = {}
    for style in MANDATORY_STYLES:
        if style in styles:
            captions[style] = await caption_style(client, visual_context, style)
        else:
            captions[style] = await caption_style(client, visual_context, style)

    return {
        "task_id": task_id,
        "video_url": video_url,
        "visual_context": visual_context[:2000],
        "captions": captions,
        "metadata": {
            "vision_model": OLLAMA_VISION_MODEL,
            "caption_model": FIREWORKS_CAPTION_MODEL,
            "uuid": str(uuid.uuid4()),
        },
    }


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
