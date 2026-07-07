"""Bridge to InnerSpark Smart Quoter (:2026) — live production demo."""

from __future__ import annotations

from typing import Any

import httpx

from app.settings import settings


async def smart_quoter_health() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.smart_quoter_url}/api/quotes/next-number")
            if r.status_code == 200:
                return {"ok": True, "service": "innerspark-smart-quoter", "port": 2026, "next": r.json()}
            return {"ok": False, "status": r.status_code}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def next_quote_number() -> str | None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.smart_quoter_url}/api/quotes/next-number")
            r.raise_for_status()
            return r.json().get("quote_number")
    except Exception:
        return None


async def list_recent_quotes(limit: int = 5) -> list[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(f"{settings.smart_quoter_url}/api/quotes")
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list):
                return data[:limit]
            return data.get("quotes", [])[:limit]
    except Exception:
        return []


async def diagnose_text(description: str) -> dict[str, Any]:
    """Proxy to Smart Quoter Ollama diagnose — local tokens only."""
    payload = {"description": description, "business_type": "PC Doctor"}
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{settings.smart_quoter_url}/api/quote/diagnose", json=payload)
            r.raise_for_status()
            return {"ok": True, "data": r.json(), "runtime": "local", "tokens_remote": 0}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
