"""AMD Developer Cloud (DigitalOcean) — cuenta GPU + inferencia vLLM opcional."""

from __future__ import annotations

from typing import Any

import httpx

from app.settings import settings


def _do_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.amd_cloud_api_token}",
        "Content-Type": "application/json",
    }


async def account_health() -> dict[str, Any]:
    if not settings.amd_cloud_api_token:
        return {
            "ok": False,
            "configured": False,
            "platform": "AMD Developer Cloud (DigitalOcean)",
            "hint": "AMD_CLOUD_API_TOKEN en .env (dop_v1_…)",
        }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{settings.amd_cloud_api_base.rstrip('/')}/account",
                headers=_do_headers(),
            )
            if r.status_code == 401:
                return {"ok": False, "configured": True, "error": "Token inválido"}
            r.raise_for_status()
            acc = r.json().get("account", {})
            dr = await client.get(
                f"{settings.amd_cloud_api_base.rstrip('/')}/droplets",
                headers=_do_headers(),
            )
            dr.raise_for_status()
            droplets = dr.json().get("droplets", [])
            gpu = []
            for d in droplets:
                pub = [
                    n.get("ip_address")
                    for n in d.get("networks", {}).get("v4", [])
                    if n.get("type") == "public"
                ]
                gpu.append(
                    {
                        "name": d.get("name"),
                        "status": d.get("status"),
                        "size": d.get("size_slug"),
                        "public_ip": pub[0] if pub else None,
                    }
                )
            return {
                "ok": True,
                "configured": True,
                "platform": "AMD Developer Cloud (DigitalOcean)",
                "email": acc.get("email"),
                "status": acc.get("status"),
                "droplet_count": len(droplets),
                "droplets": gpu,
                "inference_url": settings.amd_inference_base_url or None,
            }
    except Exception as exc:
        return {"ok": False, "configured": True, "error": str(exc)}


async def chat_inference(prompt: str, *, model: str | None = None) -> dict[str, Any]:
    base = (settings.amd_inference_base_url or "").rstrip("/")
    if not base:
        return {
            "ok": False,
            "runtime": "amd_cloud",
            "error": "AMD_INFERENCE_BASE_URL vacío — despliega vLLM en un droplet MI300X",
        }
    use_model = model or settings.amd_inference_model
    headers = {"Content-Type": "application/json"}
    if settings.amd_inference_api_key:
        headers["Authorization"] = f"Bearer {settings.amd_inference_api_key}"
    
    token_query = f"?token={settings.amd_inference_token}" if settings.amd_inference_token else ""
    payload = {
        "model": use_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            r = await client.post(f"{base}/chat/completions{token_query}", json=payload, headers=headers)
            if r.status_code != 200:
                return {
                    "ok": False,
                    "runtime": "amd_cloud",
                    "error": f"HTTP {r.status_code}: {r.text[:300]}",
                }
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            return {
                "ok": True,
                "runtime": "amd_cloud",
                "content": content,
                "model": use_model,
                "provider_id": "amd_cloud",
            }
    except Exception as exc:
        return {"ok": False, "runtime": "amd_cloud", "error": str(exc)}
