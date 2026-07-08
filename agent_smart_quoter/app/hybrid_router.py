"""Hybrid Router — AMD local + primary + Fireworks cloud."""

from __future__ import annotations

import re
from typing import Any

import httpx

from app.settings import settings
from shared.runtime_i18n import format_fireworks_unavailable, format_routing_label

EXECUTIVE_KEYWORDS = re.compile(
    r"\b(executive|ejecutivo|riesgo|risk|audit|auditoría|compliance|estrategia|board|c-level)\b",
    re.I,
)


def _ollama_ok(base: str) -> bool:
    try:
        r = httpx.get(f"{base.rstrip('/')}/api/tags", timeout=3.0)
        return r.status_code == 200
    except Exception:
        return False


def _pick_ollama_url() -> tuple[str, str]:
    """Returns (url, provider_id). Prefiere AMD local si responde."""
    for pid, url in (
        ("amd_local", settings.ollama_amd_url),
        ("primary_local", settings.ollama_primary_url),
        ("local_default", settings.ollama_base_url),
    ):
        if _ollama_ok(url):
            return url, pid
    return settings.ollama_base_url, "local_default"


async def ollama_extract(text: str, lang: str = "es") -> dict[str, Any]:
    lang = "en" if lang.lower().startswith("en") else "es"
    system = (
        "Extract quote line items (name, quantity, unit price). Reply in compact JSON with line_items key."
        if lang == "en"
        else "Extrae ítems de cotización (nombre, cantidad, precio unitario). Responde JSON compacto con clave line_items."
    )
    base, provider_id = _pick_ollama_url()
    model = settings.ollama_intake_model
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ],
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{base.rstrip('/')}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
            content = data.get("message", {}).get("content", "")
            tokens = data.get("eval_count", 0)
            return {
                "ok": True,
                "content": content,
                "tokens_local": int(tokens or 0),
                "runtime": provider_id,
                "model": model,
                "ollama_base_url": base,
                "provider_id": provider_id,
            }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "runtime": provider_id, "provider_id": provider_id}


async def fireworks_polish(draft: str, lang: str = "es") -> dict[str, Any]:
    lang = "en" if lang.lower().startswith("en") else "es"
    if not settings.fireworks_api_key:
        return {"ok": False, "error": "FIREWORKS_API_KEY missing", "runtime": "fireworks_cloud"}
    system = (
        "You are a corporate executive auditor. Polish the technical quote, assess risks, write C-level summary."
        if lang == "en"
        else "Eres auditor ejecutivo corporativo. Pulir cotización técnica, evaluar riesgos, resumen C-level."
    )
    payload = {
        "model": settings.fireworks_model,
        "messages": [
            {"role": "system", "content": system},
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
                "runtime": "fireworks_cloud",
                "model": settings.fireworks_model,
            }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "runtime": "fireworks_cloud"}


async def hybrid_route(user_text: str, lang: str = "es") -> dict[str, Any]:
    lang = "en" if lang.lower().startswith("en") else "es"
    local = await ollama_extract(user_text, lang=lang)
    needs_executive = bool(EXECUTIVE_KEYWORDS.search(user_text))
    tokens_local = local.get("tokens_local", 0)
    tokens_remote = 0
    model = local.get("model", settings.ollama_intake_model)
    runtime = local.get("runtime", "amd_local")
    provider_id = local.get("provider_id", runtime)
    final_message = local.get("content", "")

    if needs_executive or "riesgo" in user_text.lower():
        polish = await fireworks_polish(local.get("content", user_text), lang=lang)
        if polish.get("ok"):
            final_message = polish["content"]
            tokens_remote = polish.get("tokens_remote", 0)
            model = polish.get("model", settings.fireworks_model)
            runtime = "fireworks_cloud"
            provider_id = "fireworks_cloud"
        else:
            final_message += format_fireworks_unavailable(str(polish.get("error", "?")), lang)

    routing_label = format_routing_label(
        runtime=runtime,
        provider_id=provider_id,
        model=model,
        ollama_url=local.get("ollama_base_url"),
        lang=lang,
    )

    return {
        "message": final_message,
        "runtime": runtime,
        "provider_id": provider_id,
        "model": model,
        "tokens_local": tokens_local,
        "tokens_remote": tokens_remote,
        "ollama_base_url": local.get("ollama_base_url"),
        "routing_label": routing_label,
    }
