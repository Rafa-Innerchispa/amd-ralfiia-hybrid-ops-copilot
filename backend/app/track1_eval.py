"""Track 1 — Hybrid Token-Efficient Routing evaluation."""

from __future__ import annotations

from typing import Any

from app.orchestrator import orchestrator, resolve_target_agent


async def evaluate_task(text: str) -> dict[str, Any]:
    target = resolve_target_agent(text)
    out = await orchestrator.delegate_sync(text)
    result = out.get("result") or {}
    meta = result.get("metadata") if isinstance(result, dict) else {}
    if not meta and isinstance(result, dict):
        meta = result

    remote = int(meta.get("tokens_remote", 0) if meta else 0)
    local = int(meta.get("tokens_local", 0) if meta else 0)
    runtime = meta.get("runtime", "unknown") if meta else "unknown"
    model = meta.get("model", "unknown") if meta else "unknown"

    efficiency = "optimal" if remote == 0 else "hybrid_executive"

    return {
        "track": "Track 1 — Hybrid Token-Efficient Routing Agent",
        "target_agent": target,
        "runtime_chosen": runtime,
        "model_used": model,
        "tokens_remote": remote,
        "tokens_local": local,
        "scored_tokens_amd": remote,
        "local_tokens_score_zero": True,
        "efficiency_rating": efficiency,
        "session_id": out.get("session_id"),
        "answer_preview": str(result.get("content", result.get("message", "")))[:400],
        "events_count": len(out.get("events", [])),
        "accuracy_note": "Ejecutar eval local antes de submit (recomendación AMD)",
    }
