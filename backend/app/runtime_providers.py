"""Runtime providers — AMD local, primary local, cloud (Fireworks)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

from app.settings import settings


@dataclass
class RuntimeChoice:
    provider_id: str
    ollama_base_url: str
    label: str
    reason: str
    available: bool


def _ollama_ok(base: str, timeout: float = 3.0) -> bool:
    try:
        r = httpx.get(f"{base.rstrip('/')}/api/tags", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def list_providers() -> list[RuntimeChoice]:
    amd_url = os.getenv("OLLAMA_AMD_URL", settings.ollama_amd_url)
    primary_url = os.getenv("OLLAMA_PRIMARY_URL", settings.ollama_primary_url)
    local_url = settings.ollama_base_url

    providers = [
        RuntimeChoice(
            "amd_local",
            amd_url,
            "AMD Ryzen node (.5)",
            "prefer_cpu / offload from primary",
            _ollama_ok(amd_url),
        ),
        RuntimeChoice(
            "primary_local",
            primary_url,
            "Primary Intel+GPU (.4)",
            "GPU models / heavy inference",
            _ollama_ok(primary_url),
        ),
        RuntimeChoice(
            "local_default",
            local_url,
            "Local gateway host",
            "fallback localhost",
            _ollama_ok(local_url),
        ),
    ]
    return providers


def select_ollama_url(
    *,
    prefer_amd: bool = False,
    prefer_primary: bool = False,
    task_type: str = "general",
) -> RuntimeChoice:
    providers = list_providers()
    order = ["amd_local", "primary_local", "local_default"]
    if prefer_primary:
        order = ["primary_local", "amd_local", "local_default"]
    elif prefer_amd or task_type in ("intake", "classify", "quote_intake", "routing"):
        order = ["amd_local", "primary_local", "local_default"]

    for pid in order:
        for p in providers:
            if p.provider_id == pid and p.available:
                return p

    for p in providers:
        if p.available:
            return p

    return providers[-1]


async def chat_ollama(
    prompt: str,
    *,
    system: str = "",
    model: str | None = None,
    prefer_amd: bool = False,
    prefer_primary: bool = False,
    task_type: str = "general",
) -> dict[str, Any]:
    import time

    choice = select_ollama_url(
        prefer_amd=prefer_amd,
        prefer_primary=prefer_primary,
        task_type=task_type,
    )
    use_model = model or settings.ollama_intake_model
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            r = await client.post(
                f"{choice.ollama_base_url.rstrip('/')}/api/chat",
                json={"model": use_model, "messages": messages, "stream": False},
            )
            r.raise_for_status()
            data = r.json()
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            return {
                "ok": True,
                "content": data.get("message", {}).get("content", ""),
                "provider_id": choice.provider_id,
                "ollama_base_url": choice.ollama_base_url,
                "model": use_model,
                "runtime": choice.provider_id,
                "selection_reason": choice.reason,
                "latency_ms": elapsed_ms,
                "tokens_local": int(data.get("eval_count") or 0),
            }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "provider_id": choice.provider_id,
            "ollama_base_url": choice.ollama_base_url,
            "runtime": choice.provider_id,
        }
