"""Health checks for credits status endpoint."""

from __future__ import annotations

from typing import Any

import httpx

from app.settings import settings


async def ollama_health() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            r.raise_for_status()
            return {"ok": True, "models": len(r.json().get("models", []))}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def fireworks_health() -> dict[str, Any]:
    if not settings.fireworks_api_key:
        return {"ok": False, "configured": False}
    return {"ok": True, "configured": True, "model": settings.fireworks_model}
