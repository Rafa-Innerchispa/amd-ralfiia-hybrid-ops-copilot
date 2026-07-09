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
    format_amd_cloud_result,
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

COMPLEX_KEYWORDS = ("code", "debug", "math", "puzzle", "matrix", "algorithm", "algoritmo", "matrices", "autovalor", "complejo", "matemáticas", "programar")

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


async def process_single_task(task_id: str, prompt: str, lang: str = "es", force_model: str | None = None) -> dict[str, Any]:
    lang = normalize_lang(lang)
    async with httpx.AsyncClient() as client:
        is_gemma_preset = (force_model == "gemma")
        
        if is_complex_task(prompt) or is_gemma_preset:
            is_cloud_vllm = False
            fallback_reason = None
            
            if is_gemma_preset:
                target_fireworks_model = "accounts/fireworks/models/gemma-4-31b-it"
                if not settings.fireworks_api_key and not settings.amd_inference_base_url:
                    err_msg = (
                        "No hay backend de Gemma activo. Por favor configura Fireworks o enciende el Jupyter."
                        if lang == "es" else
                        "No active Gemma backend. Please configure Fireworks or start the Jupyter server."
                    )
                    return {
                        "task_id": task_id,
                        "answer": f"ERROR: {err_msg}",
                        "result": {
                            "message": f"ERROR: {err_msg}",
                            "content": f"ERROR: {err_msg}"
                        },
                        "metadata": {
                            "routing": "error",
                            "error": err_msg,
                            "routing_label": "Gemma Offline"
                        }
                    }
            else:
                target_fireworks_model = resolve_complex_model()
                if "gemma" in target_fireworks_model.lower() and not settings.fireworks_api_key:
                    fallback_reason = (
                        "Gemma requiere 'Deploy on Demand' en app.fireworks.ai y FIREWORKS_API_KEY no configurada. "
                        "Usando deepseek-v4-pro como fallback."
                        if lang == "es"
                        else "Gemma requires 'Deploy on Demand' in app.fireworks.ai and FIREWORKS_API_KEY not configured. "
                        "Using deepseek-v4-pro as fallback."
                    )
                    target_fireworks_model = "deepseek-v4-pro"

            if settings.amd_inference_base_url:
                try:
                    from app.amd_cloud_client import chat_inference

                    res = await chat_inference(prompt)
                    if res.get("ok"):
                        answer = res["content"]
                        model_path = res.get("model") or settings.amd_inference_model
                        
                        if is_gemma_preset:
                            audit_prompt = (
                                f"Actúa como el Agente Auditor Gemma de AMD. Analiza el siguiente código "
                                f"generado para optimización en entornos AMD ROCm GPU, eficiencia de memoria y complejidad. "
                                f"Responde de forma muy concisa con 3 viñetas. Código:\n{answer}"
                                if lang == "es" else
                                f"Act as the Gemma AMD Auditor Agent. Analyze the following generated code "
                                f"for optimization in AMD ROCm GPU environments, memory efficiency, and complexity. "
                                f"Reply very concisely with 3 bullet points. Code:\n{answer}"
                            )
                            try:
                                audit_res = await chat_inference(audit_prompt)
                                if audit_res.get("ok"):
                                    answer = (
                                        f"{answer}\n\n"
                                        f"=== 🛡️ ROCm GPU AUDIT (Gemma Supervisor) ===\n"
                                        f"{audit_res['content']}"
                                    )
                            except Exception:
                                pass

                        answer = format_amd_cloud_result(answer, model_path, lang)
                        engine = f"AMD Cloud vLLM ({model_path})"
                        is_cloud_vllm = True
                        meta_extra = {
                            "routing": "amd_cloud",
                            "provider_id": "amd_cloud",
                            "tokens_remote": 1,
                            "model": model_path,
                            "routing_label": format_routing_label(
                                runtime="amd_cloud",
                                provider_id="amd_cloud",
                                model=model_path,
                                ollama_url=None,
                                lang=lang,
                            ),
                        }
                except Exception:
                    pass
            if not is_cloud_vllm:
                try:
                    answer, engine = await run_fireworks_remote(client, prompt, target_model=target_fireworks_model)
                    model_path = target_fireworks_model  # Aseguramos que el model_path refleje el modelo usado
                    
                    if is_gemma_preset:
                        audit_prompt = (
                            f"Actúa como el Agente Auditor Gemma de AMD. Analiza el siguiente código "
                            f"generado para optimización en entornos AMD ROCm GPU, eficiencia de memoria y complejidad. "
                            f"Responde de forma muy concisa con 3 viñetas. Código:\n{answer}"
                            if lang == "es" else
                            f"Act as the Gemma AMD Auditor Agent. Analyze the following generated code "
                            f"for optimization in AMD ROCm GPU environments, memory efficiency, and complexity. "
                            f"Reply very concisely with 3 bullet points. Code:\n{answer}"
                        )
                        try:
                            audit_res, _ = await run_fireworks_remote(client, audit_prompt, target_model=target_fireworks_model)
                            answer = (
                                f"{answer}\n\n"
                                f"=== 🛡️ ROCm GPU AUDIT (Gemma Supervisor) ===\n"
                                f"{audit_res}"
                            )
                        except Exception:
                            pass

                    answer = format_fireworks_result(answer, model_path, lang, fallback_reason)
                    meta_extra = {
                        "routing": "fireworks",
                        "provider_id": "fireworks_cloud",
                        "tokens_remote": 1,
                        "model": model_path,
                        "fallback_reason": fallback_reason,
                        "routing_label": format_routing_label(
                            runtime="fireworks_cloud",
                            provider_id="fireworks_cloud",
                            model=model_path,
                            ollama_url=None,
                            lang=lang,
                        ),
                    }
                except Exception as exc:
                    if is_gemma_preset:
                        err_msg = str(exc)
                        return {
                            "task_id": task_id,
                            "answer": f"Gemma API Error: {err_msg}",
                            "result": {
                                "message": f"Gemma API Error: {err_msg}",
                                "content": f"Gemma API Error: {err_msg}"
                            },
                            "metadata": {
                                "routing": "error",
                                "error": err_msg,
                                "routing_label": "Gemma API Error"
                            }
                        }
                    raise exc
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
