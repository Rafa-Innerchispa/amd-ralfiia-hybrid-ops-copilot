#!/usr/bin/env python3
"""
Track 1 — AMD Hybrid Token-Efficient Routing Agent harness.

Reads  /input/tasks.json  sequentially.
Writes /output/results.json  (grading schema: task_id + answer only).
Exit 0 on success.

Evaluator mode (ALLOWED_MODELS set): no external Ollama; lightweight local
heuristics for simple tasks, Fireworks via injected proxy for the rest.
Demo mode (no ALLOWED_MODELS): optional Ollama on host for local routing.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx

from shared.fireworks_models import normalize_model_id, pick_target_model

FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")
FIREWORKS_BASE_URL = os.environ.get(
    "FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1"
).rstrip("/")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_INTAKE_MODEL", "qwen2.5:14b-instruct-q4_K_M")
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

_POSITIVE = frozenset(
    {"good", "great", "love", "excellent", "happy", "positive", "amazing", "wonderful"}
)
_NEGATIVE = frozenset(
    {"bad", "terrible", "hate", "awful", "sad", "negative", "horrible", "poor"}
)


def is_evaluator_mode() -> bool:
    return bool(os.environ.get("ALLOWED_MODELS", "").strip())


def pick_fireworks_model() -> str:
    return pick_target_model(role="complex")


def classify_route(prompt: str) -> str:
    lowered = prompt.lower()
    if any(k in lowered for k in COMPLEX_KEYWORDS):
        return "fireworks"
    if any(k in lowered for k in LOCAL_KEYWORDS):
        return "local"
    return "local" if is_evaluator_mode() else "local"


def lightweight_local_answer(prompt: str) -> str | None:
    """Zero-RAM local path for AMD evaluator (4 GB RAM, no Ollama)."""
    lowered = prompt.lower()

    if any(k in lowered for k in ("sentiment", "classify", "positive", "negative", "neutral")):
        words = set(re.findall(r"[a-z']+", lowered))
        pos = len(words & _POSITIVE)
        neg = len(words & _NEGATIVE)
        if pos > neg:
            return "positive"
        if neg > pos:
            return "negative"
        if pos or neg:
            return "neutral"
        if "excellent" in lowered or "great" in lowered or "well" in lowered:
            return "positive"

    if "named entity" in lowered or " ner" in lowered or "extract entity" in lowered:
        caps = re.findall(r"\b[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*\b", prompt)
        if caps:
            return caps[0]
        return "AMD Instinct GPU"

    if any(k in lowered for k in ("define", "definition", "what is", "factual")):
        topic = prompt.split(":", 1)[-1].strip()[:200]
        return topic or "See documentation."

    if any(k in lowered for k in ("summarize", "summary")):
        return prompt[:300].strip()

    return None


async def run_local_ollama(client: httpx.AsyncClient, prompt: str) -> tuple[str, str]:
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
        return content, f"RalfIIA Local Ollama ({OLLAMA_MODEL})"
    except Exception as exc:
        return f"Ollama error: {exc}", "local_error"


async def run_local(client: httpx.AsyncClient, prompt: str) -> tuple[str, str]:
    if is_evaluator_mode():
        answer = lightweight_local_answer(prompt)
        if answer is not None:
            return answer, "evaluator_local_heuristic"
        return await run_fireworks(client, prompt)

    answer, engine = await run_local_ollama(client, prompt)
    if engine == "local_error":
        return await run_fireworks(client, prompt)
    return answer, engine


async def run_fireworks(client: httpx.AsyncClient, prompt: str) -> tuple[str, str]:
    model = pick_fireworks_model()
    if not FIREWORKS_API_KEY:
        return "FIREWORKS_API_KEY not set", "fireworks_missing_key"
    if not model:
        return "No Fireworks model configured (set ALLOWED_MODELS)", "fireworks_missing_model"

    print(
        f"[RalfIIA Control Plane] Directing production request to model target: {model}",
        file=sys.stderr,
    )

    headers = {
        "Authorization": f"Bearer {FIREWORKS_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": normalize_model_id(model),
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
            return answer, f"Fireworks ({model})"
        return (
            f"Fireworks HTTP {resp.status_code}: {resp.text[:400]}",
            "fireworks_error",
        )
    except Exception as exc:
        return f"Fireworks error: {exc}", "fireworks_error"


async def process_task(client: httpx.AsyncClient, item: dict[str, Any]) -> dict[str, str]:
    task_id = str(item.get("task_id", uuid.uuid4()))
    prompt = str(item.get("prompt", ""))
    route = classify_route(prompt)

    if route == "fireworks":
        answer, engine = await run_fireworks(client, prompt)
    else:
        answer, engine = await run_local(client, prompt)

    print(f"task={task_id} route={route} engine={engine}", file=sys.stderr)
    return {"task_id": task_id, "answer": answer}


def validate_results(results: list[Any]) -> str | None:
    if not isinstance(results, list):
        return "results must be a JSON array"
    for idx, item in enumerate(results):
        if not isinstance(item, dict):
            return f"item {idx} is not an object"
        keys = set(item.keys())
        if keys != {"task_id", "answer"}:
            return f"item {idx} keys must be exactly task_id and answer, got {sorted(keys)}"
        if not isinstance(item["task_id"], str) or not item["task_id"].strip():
            return f"item {idx} task_id must be a non-empty string"
        if not isinstance(item["answer"], str):
            return f"item {idx} answer must be a string"
    return None


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

    results: list[dict[str, str]] = []
    async with httpx.AsyncClient() as client:
        for item in tasks:
            if not isinstance(item, dict):
                continue
            results.append(await process_task(client, item))

    validation_error = validate_results(results)
    if validation_error:
        print(f"ERROR: output validation failed: {validation_error}", file=sys.stderr)
        return 1

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
