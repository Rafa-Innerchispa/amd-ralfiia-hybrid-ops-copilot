#!/usr/bin/env python3
"""
Track 1 — AMD Hybrid Token-Efficient Routing Agent harness.

Reads  /input/tasks.json  sequentially.
Writes /output/results.json
Exit 0 on success.

Routing:
  - NER, sentiment, factual → Ollama qwen2.5:14b-instruct-q4_K_M (token cost 0)
  - code, debug, math, puzzle, logic → Fireworks gemma-4-31b-it
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import httpx

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_INTAKE_MODEL", "qwen2.5:14b-instruct-q4_K_M")
FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")
FIREWORKS_BASE_URL = os.environ.get(
    "FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1"
).rstrip("/")
FIREWORKS_COMPLEX_MODEL = os.environ.get("FIREWORKS_COMPLEX_MODEL", "gemma-4-31b-it")

INPUT_PATH = os.environ.get("HARNESS_INPUT_PATH", "/input/tasks.json")
OUTPUT_PATH = os.environ.get("HARNESS_OUTPUT_PATH", "/output/results.json")

LOCAL_KEYWORDS = (
    "sentiment",
    "ner",
    "named entity",
    "classify",
    "classification",
    "factual",
    "define",
    "definition",
    "extract entity",
    "label",
    "positive",
    "negative",
    "neutral",
    "summarize",
    "summary",
)

COMPLEX_KEYWORDS = (
    "code",
    "debug",
    "math",
    "puzzle",
    "matrix",
    "algorithm",
    "logic",
    "implement",
    "function",
    "compile",
    "recursion",
    "proof",
)


def classify_route(prompt: str) -> str:
    lowered = prompt.lower()
    if any(k in lowered for k in COMPLEX_KEYWORDS):
        return "fireworks"
    if any(k in lowered for k in LOCAL_KEYWORDS):
        return "local"
    # Default local-first (Track 1 token efficiency)
    return "local"


def fireworks_model_id(name: str) -> str:
    if name.startswith("accounts/"):
        return name
    return f"accounts/fireworks/models/{name}"


async def run_local(client: httpx.AsyncClient, prompt: str) -> tuple[str, str]:
    try:
        resp = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        return content, f"RalfIIA Local Ollama ({OLLAMA_MODEL}) — Token Cost: 0"
    except httpx.HTTPError as exc:
        return f"Ollama HTTP error: {exc}", "local_error"
    except (KeyError, json.JSONDecodeError) as exc:
        return f"Ollama parse error: {exc}", "local_error"
    except Exception as exc:
        return f"Ollama error: {exc}", "local_error"


async def run_fireworks(client: httpx.AsyncClient, prompt: str) -> tuple[str, str]:
    if not FIREWORKS_API_KEY:
        return (
            "FIREWORKS_API_KEY not set — complex task cannot run on AMD cloud",
            "fireworks_missing_key",
        )
    headers = {
        "Authorization": f"Bearer {FIREWORKS_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": fireworks_model_id(FIREWORKS_COMPLEX_MODEL),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }
    try:
        resp = await client.post(
            f"{FIREWORKS_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            answer = data["choices"][0]["message"]["content"]
            return answer, f"AMD Cloud Fireworks ({FIREWORKS_COMPLEX_MODEL})"
        return (
            f"Fireworks HTTP {resp.status_code}: {resp.text[:400]}",
            "fireworks_error",
        )
    except httpx.HTTPError as exc:
        return f"Fireworks network error: {exc}", "fireworks_error"
    except (KeyError, json.JSONDecodeError) as exc:
        return f"Fireworks parse error: {exc}", "fireworks_error"
    except Exception as exc:
        return f"Fireworks error: {exc}", "fireworks_error"


async def process_task(client: httpx.AsyncClient, item: dict[str, Any]) -> dict[str, Any]:
    task_id = str(item.get("task_id", uuid.uuid4()))
    prompt = str(item.get("prompt", ""))
    route = classify_route(prompt)

    if route == "fireworks":
        answer, engine = await run_fireworks(client, prompt)
    else:
        answer, engine = await run_local(client, prompt)

    return {
        "task_id": task_id,
        "answer": answer,
        "metadata": {
            "processed_by": engine,
            "routing": route,
            "uuid": str(uuid.uuid4()),
            "model": FIREWORKS_COMPLEX_MODEL if route == "fireworks" else OLLAMA_MODEL,
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
        print(f"ERROR: invalid JSON in {INPUT_PATH}: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"ERROR: cannot read {INPUT_PATH}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(tasks, list):
        print("ERROR: tasks.json must be a JSON array", file=sys.stderr)
        return 1

    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient() as client:
        for item in tasks:
            if not isinstance(item, dict):
                continue
            results.append(await process_task(client, item))

    out_dir = Path(OUTPUT_PATH).parent
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        print(f"ERROR: cannot write {OUTPUT_PATH}: {exc}", file=sys.stderr)
        return 1

    print(f"Track 1 harness OK — {len(results)} tasks → {OUTPUT_PATH}")
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
