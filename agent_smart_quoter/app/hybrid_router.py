"""Hybrid Router — Ollama intake + Fireworks Gemma-2 executive polish (AMD MI300X)."""

from __future__ import annotations

import re
from typing import Any

import httpx

from app.settings import settings

EXECUTIVE_KEYWORDS = re.compile(
    r"\b(executive|ejecutivo|riesgo|risk|audit|auditoría|compliance|estrategia|board|c-level)\b",
    re.I,
)


async def ollama_extract(text: str) -> dict[str, Any]:
    payload = {
        "model": settings.ollama_intake_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Extrae ítems de cotización estructurados (nombre, cantidad, precio unitario). "
                    "Responde en JSON compacto con clave line_items."
                ),
            },
            {"role": "user", "content": text},
        ],
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
            r.raise_for_status()
            content = r.json().get("message", {}).get("content", "")
            tokens = r.json().get("eval_count", 0)
            return {"ok": True, "content": content, "tokens_local": int(tokens or 0), "runtime": "local"}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "runtime": "local"}


async def fireworks_polish(draft: str) -> dict[str, Any]:
    if not settings.fireworks_api_key:
        return {"ok": False, "error": "FIREWORKS_API_KEY missing", "runtime": "fireworks"}
    payload = {
        "model": settings.fireworks_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres auditor ejecutivo corporativo. Pulir cotización técnica, "
                    "evaluar riesgos y redactar resumen C-level. Infra: AMD Instinct via Fireworks."
                ),
            },
            {"role": "user", "content": draft},
        ],
        "max_tokens": 1500,
        "temperature": 0.25,
    }
    headers = {"Authorization": f"Bearer {settings.fireworks_api_key}"}
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{settings.fireworks_api_base}/chat/completions",
                json=payload,
                headers=headers,
            )
            r.raise_for_status()
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return {
                "ok": True,
                "content": content,
                "tokens_remote": int(usage.get("total_tokens", 0)),
                "runtime": "fireworks",
                "model": settings.fireworks_model,
            }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "runtime": "fireworks"}


async def hybrid_route(user_text: str) -> dict[str, Any]:
    local = await ollama_extract(user_text)
    needs_executive = bool(EXECUTIVE_KEYWORDS.search(user_text))
    tokens_local = local.get("tokens_local", 0)
    tokens_remote = 0
    model = settings.ollama_intake_model
    runtime = "local"
    final_message = local.get("content", "")

    if needs_executive or "riesgo" in user_text.lower():
        polish = await fireworks_polish(local.get("content", user_text))
        if polish.get("ok"):
            final_message = polish["content"]
            tokens_remote = polish.get("tokens_remote", 0)
            model = settings.fireworks_model
            runtime = "fireworks"
        else:
            final_message += f"\n\n[Fireworks unavailable: {polish.get('error')}]"

    return {
        "message": final_message,
        "runtime": runtime,
        "model": model,
        "tokens_local": tokens_local,
        "tokens_remote": tokens_remote,
        "routing_label": (
            f"Routed to AMD Cloud via Fireworks — Model: Gemma-2"
            if runtime == "fireworks"
            else f"Routed to Local Ollama — Model: {settings.ollama_intake_model}"
        ),
    }
