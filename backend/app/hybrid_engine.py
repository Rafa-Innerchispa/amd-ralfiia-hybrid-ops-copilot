"""
RalfIIA Hybrid Core Engine — Track 1 harness + routing unificado.

- Tareas ligeras → Ollama qwen2.5:14b (costo token remoto = 0)
- Tareas complejas → Fireworks AMD (modelos oficiales Track 1)
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

import httpx

from app.settings import settings

# Track 1 — modelos oficiales permitidos (AMD harness)
ALLOWED_MODELS = [
    "minimax-m3",
    "kimi-k2p7-code",
    "gemma-4-31b-it",
    "gemma-4-26b-a4b-it",
    "gemma-4-31b-it-nvfp4",
]

DEFAULT_COMPLEX_MODEL = "gemma-4-31b-it"

COMPLEX_KEYWORDS = ("code", "debug", "math", "puzzle", "matrix", "algorithm")

# Rutas harness (montar volúmenes en Docker: /input, /output)
HARNESS_INPUT = os.environ.get("HARNESS_INPUT_PATH", "/input/tasks.json")
HARNESS_OUTPUT = os.environ.get("HARNESS_OUTPUT_PATH", "/output/results.json")


def is_complex_task(prompt: str) -> bool:
    lowered = prompt.lower()
    return any(k in lowered for k in COMPLEX_KEYWORDS)


def fireworks_model_id(short_name: str) -> str:
    if short_name.startswith("accounts/"):
        return short_name
    return f"accounts/fireworks/models/{short_name}"


async def run_local_ollama(client: httpx.AsyncClient, prompt: str) -> tuple[str, str]:
    try:
        resp = await client.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": settings.ollama_intake_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        answer = resp.json()["message"]["content"]
        return answer, "RalfIIA Local Ollama (Token Cost: 0)"
    except Exception as exc:
        return f"Local processing fallback error: {exc}", "Error Fallback"


async def run_fireworks_remote(
    client: httpx.AsyncClient,
    prompt: str,
    target_model: str = DEFAULT_COMPLEX_MODEL,
) -> tuple[str, str]:
    if target_model not in ALLOWED_MODELS and not target_model.startswith("accounts/"):
        target_model = DEFAULT_COMPLEX_MODEL

    if not settings.fireworks_api_key:
        return (
            "Fireworks API key not configured — set FIREWORKS_API_KEY in .env",
            "AMD Cloud Error (no key)",
        )

    headers = {
        "Authorization": f"Bearer {settings.fireworks_api_key}",
        "Content-Type": "application/json",
    }
    model_id = fireworks_model_id(target_model)
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }
    base = settings.fireworks_api_base.rstrip("/")

    try:
        resp = await client.post(
            f"{base}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120.0,
        )
        if resp.status_code == 200:
            answer = resp.json()["choices"][0]["message"]["content"]
            return answer, f"AMD Cloud Inference ({target_model})"
        return (
            f"AMD Cloud returned status {resp.status_code}: {resp.text[:500]}",
            "AMD Cloud Error",
        )
    except Exception as exc:
        return f"Failed to connect to AMD Cloud proxy: {exc}", "Network Error"


async def process_single_task(task_id: str, prompt: str) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        if is_complex_task(prompt):
            answer, engine = await run_fireworks_remote(client, prompt)
        else:
            answer, engine = await run_local_ollama(client, prompt)

    return {
        "task_id": task_id,
        "answer": answer,
        "metadata": {
            "processed_by": engine,
            "uuid": str(uuid.uuid4()),
            "routing": "fireworks" if is_complex_task(prompt) else "local",
            "model": DEFAULT_COMPLEX_MODEL if is_complex_task(prompt) else settings.ollama_intake_model,
        },
    }


async def execute_harness_from_file(
    input_path: str | None = None,
    output_path: str | None = None,
) -> dict[str, Any]:
    inp = input_path or HARNESS_INPUT
    out = output_path or HARNESS_OUTPUT

    if not os.path.exists(inp):
        raise FileNotFoundError(f"Input file not found at {inp}")

    with open(inp, encoding="utf-8") as f:
        tasks_data = json.load(f)

    results: list[dict[str, Any]] = []
    for item in tasks_data:
        task_id = item.get("task_id", str(uuid.uuid4()))
        prompt = item.get("prompt", "")
        results.append(await process_single_task(task_id, prompt))

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return {"status": "completed", "processed_tasks": len(results), "output_path": out}


async def execute_harness_from_tasks(tasks: list[dict[str, str]]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for item in tasks:
        results.append(
            await process_single_task(
                item.get("task_id", str(uuid.uuid4())),
                item.get("prompt", ""),
            )
        )
    return {"status": "completed", "processed_tasks": len(results), "results": results}
