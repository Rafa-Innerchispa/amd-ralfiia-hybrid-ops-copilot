"""Health checks for credits status endpoint."""

from __future__ import annotations

from typing import Any

import httpx

from app.fireworks_models import DEFAULT_GEMMA_COMPLEX, GEMMA_MODEL_IDS, normalize_model_id
from app.settings import settings


async def ollama_health() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
            r.raise_for_status()
            models = [m.get("name") for m in r.json().get("models", [])]
            intake_ok = any(settings.ollama_intake_model.split(":")[0] in (m or "") for m in models)
            return {
                "ok": True,
                "base_url": settings.ollama_base_url,
                "intake_model": settings.ollama_intake_model,
                "intake_ready": intake_ok,
                "model_count": len(models),
            }
    except Exception as exc:
        return {"ok": False, "base_url": settings.ollama_base_url, "error": str(exc)}


async def fireworks_health() -> dict[str, Any]:
    target = normalize_model_id(settings.fireworks_model or DEFAULT_GEMMA_COMPLEX)
    if not settings.fireworks_api_key:
        return {
            "ok": False,
            "configured": False,
            "model": target,
            "platform": "Fireworks AI (AMD MI300X)",
            "hint": "Pega FIREWORKS_API_KEY en .env — créditos AMD hackathon",
        }
    headers = {"Authorization": f"Bearer {settings.fireworks_api_key}"}
    base = settings.fireworks_api_base.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get(f"{base}/models", headers=headers)
            if r.status_code == 401:
                return {"ok": False, "configured": True, "error": "API key inválida"}
            r.raise_for_status()
            deployed = [m.get("id", "") for m in r.json().get("data", [])]
            gemma_deployed = [m for m in deployed if "gemma" in m.lower()]
            gemma_catalog = list(GEMMA_MODEL_IDS.values())
            return {
                "ok": True,
                "configured": True,
                "model": target,
                "platform": "Fireworks AI · Gemma on AMD",
                "deployed_models": deployed,
                "gemma_deployed": gemma_deployed,
                "gemma_catalog": gemma_catalog,
                "gemma_ready": target in deployed,
                "deploy_hint": (
                    None
                    if target in deployed
                    else "Deploy on Demand en app.fireworks.ai → Gemma → gemma-4-31b-it"
                ),
            }
    except Exception as exc:
        return {"ok": False, "configured": True, "error": str(exc)}


async def jupyter_health() -> dict[str, Any]:
    if not settings.amd_inference_base_url:
        return {"ok": False, "error": "URL no configurada"}
    token_query = f"?token={settings.amd_inference_token}" if settings.amd_inference_token else ""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{settings.amd_inference_base_url.rstrip('/')}/models{token_query}")
            if r.status_code == 200:
                models = [m.get("id") for m in r.json().get("data", [])]
                return {"ok": True, "models": models}
            return {"ok": False, "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
