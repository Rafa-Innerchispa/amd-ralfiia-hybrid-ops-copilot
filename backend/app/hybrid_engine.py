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
from shared.runtime_i18n import (
    format_fireworks_result,
    format_routing_label,
    format_sentiment_result,
    is_sentiment_prompt,
    normalize_lang,
)
from app.fireworks_models import GEMMA_MODEL_IDS, normalize_model_id, pick_target_model

# Modelos desplegados + catálogo Gemma (requieren Deploy on Demand en cuenta personal)
ALLOWED_MODELS = [
    *GEMMA_MODEL_IDS.keys(),
    "deepseek-v4-pro",
    "kimi-k2p6",
    "kimi-k2p5",
    "glm-5p1",
    "glm-5p2",
    "gpt-oss-120b",
    "flux-1-schnell-fp8",
]

DEFAULT_COMPLEX_MODEL = normalize_model_id(
    os.environ.get("FIREWORKS_COMPLEX_MODEL")
    or os.environ.get("FIREWORKS_MODEL")
    or settings.fireworks_model
    or "accounts/fireworks/models/deepseek-v4-pro"
)

COMPLEX_KEYWORDS = ("code", "debug", "math", "puzzle", "matrix", "algorithm")

# Rutas harness (montar volúmenes en Docker: /input, /output)
HARNESS_INPUT = os.environ.get("HARNESS_INPUT_PATH", "/input/tasks.json")
HARNESS_OUTPUT = os.environ.get("HARNESS_OUTPUT_PATH", "/output/results.json")


def is_complex_task(prompt: str) -> bool:
    lowered = prompt.lower()
    return any(k in lowered for k in COMPLEX_KEYWORDS)


def fireworks_model_id(short_name: str) -> str:
    return normalize_model_id(short_name)


def resolve_complex_model(target_model: str | None = None) -> str:
    if target_model:
        return normalize_model_id(target_model)
    env_allowed = os.environ.get("ALLOWED_MODELS", "").strip()
    if env_allowed:
        return pick_target_model(role="complex", allowed_raw=env_allowed)
    configured = os.environ.get("FIREWORKS_COMPLEX_MODEL") or os.environ.get("FIREWORKS_MODEL") or settings.fireworks_model
    if configured:
        return normalize_model_id(configured)
    return DEFAULT_COMPLEX_MODEL


async def run_local_ollama(client: httpx.AsyncClient, prompt: str) -> tuple[str, str, dict[str, Any]]:
    from app.runtime_providers import chat_ollama

    result = await chat_ollama(prompt, prefer_amd=True, task_type="intake")
    if result.get("ok"):
        label = (
            f"RalfIIA {result.get('provider_id', 'local')} "
            f"@ {result.get('ollama_base_url', '?')} "
            f"({result.get('latency_ms', '?')}ms, Token Cost: 0)"
        )
        return result["content"], label, result
    return (
        f"Local processing fallback error: {result.get('error')}",
        f"Error Fallback ({result.get('provider_id', '?')})",
        result,
    )


async def run_fireworks_remote(
    client: httpx.AsyncClient,
    prompt: str,
    target_model: str | None = None,
) -> tuple[str, str]:
    model_id = resolve_complex_model(target_model)

    if not settings.fireworks_api_key:
        return (
            "Fireworks API key not configured — set FIREWORKS_API_KEY in .env",
            "AMD Cloud Error (no key)",
        )

    headers = {
        "Authorization": f"Bearer {settings.fireworks_api_key}",
        "Content-Type": "application/json",
    }
    model_path = fireworks_model_id(model_id)
    payload = {
        "model": model_path,
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
            return answer, f"AMD Cloud Inference ({model_path})"
        return (
            f"AMD Cloud returned status {resp.status_code}: {resp.text[:500]}",
            "AMD Cloud Error",
        )
    except Exception as exc:
        return f"Failed to connect to AMD Cloud proxy: {exc}", "Network Error"


async def process_single_task(task_id: str, prompt: str, lang: str = "es") -> dict[str, Any]:
    lang = normalize_lang(lang)
    async with httpx.AsyncClient() as client:
        if is_complex_task(prompt):
            answer, engine = await run_fireworks_remote(client, prompt)
            model_path = resolve_complex_model()
            answer = format_fireworks_result(answer, model_path, lang)
            meta_extra: dict[str, Any] = {
                "routing": "fireworks",
                "provider_id": "fireworks_cloud",
                "tokens_remote": 1,
                "model": model_path,
                "routing_label": format_routing_label(
                    runtime="fireworks_cloud",
                    provider_id="fireworks_cloud",
                    model=model_path,
                    ollama_url=None,
                    lang=lang,
                ),
            }
        else:
            answer, engine, local_meta = await run_local_ollama(client, prompt)
            if is_sentiment_prompt(prompt):
                answer = format_sentiment_result(
                    prompt,
                    answer,
                    provider_id=str(local_meta.get("provider_id", "amd_local")),
                    ollama_url=str(local_meta.get("ollama_base_url", settings.ollama_amd_url)),
                    model=str(local_meta.get("model", settings.ollama_intake_model)),
                    lang=lang,
                )
            meta_extra = {
                "routing": "local",
                "provider_id": local_meta.get("provider_id"),
                "ollama_base_url": local_meta.get("ollama_base_url"),
                "latency_ms": local_meta.get("latency_ms"),
                "tokens_remote": 0,
                "model": local_meta.get("model", settings.ollama_intake_model),
                "routing_label": format_routing_label(
                    runtime=str(local_meta.get("provider_id", "amd_local")),
                    provider_id=str(local_meta.get("provider_id", "amd_local")),
                    model=str(local_meta.get("model", settings.ollama_intake_model)),
                    ollama_url=str(local_meta.get("ollama_base_url", settings.ollama_amd_url)),
                    lang=lang,
                ),
            }

    return {
        "task_id": task_id,
        "answer": answer,
        "metadata": {
            "processed_by": engine,
            "uuid": str(uuid.uuid4()),
            "model": meta_extra.get("model") or settings.ollama_intake_model,
            **meta_extra,
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
