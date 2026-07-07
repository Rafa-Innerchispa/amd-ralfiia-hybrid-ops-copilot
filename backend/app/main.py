"""RalfIIA Hybrid Ops Copilot — AMD Core Engine (Track 1 + Track 3)."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import mongo_store
from app.hybrid_engine import (
    ALLOWED_MODELS,
    execute_harness_from_file,
    execute_harness_from_tasks,
    process_single_task,
)
from app.integrations import smart_quoter_bridge
from app.orchestrator import orchestrator
from app.settings import settings
from app.track1_eval import evaluate_task
from scripts.seed_mongo import seed_if_empty


# --- Track 1 Harness schemas (AMD official) ---


class TaskItem(BaseModel):
    task_id: str
    prompt: str


class Track1Input(BaseModel):
    tasks: List[TaskItem]


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    result: dict | None = None
    events: list
    error: dict | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_if_empty()
    mongo_store.append_event({"type": "system_boot", "service": "amd-core-engine"})
    yield


app = FastAPI(
    title="RalfIIA Hybrid Ops Copilot - AMD Core Engine",
    description="Track 1 harness routing + Track 3 A2A orchestrator",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_UI_DIR = Path(__file__).resolve().parents[2] / "ui" / "public"
if _UI_DIR.is_dir():
    app.mount("/console", StaticFiles(directory=str(_UI_DIR), html=True), name="console")


@app.get("/console-page")
async def console_redirect():
    return RedirectResponse(url="/console/")


# --- Health (harness + control plane) ---


@app.get("/health")
async def health_check():
    return {
        "status": "online",
        "infrastructure": "RalfIIA Hybrid Control Plane",
        "ok": True,
        "service": "root-gateway",
        "port": settings.root_gateway_port,
        "tracks": ["Track 1 Hybrid Router", "Track 3 Unicorn A2A"],
        "allowed_models": ALLOWED_MODELS,
        "mongo": mongo_store.ping(),
        "transactions": mongo_store.count_transactions(),
        "fireworks_configured": bool(settings.fireworks_api_key),
        "ollama_model": settings.ollama_intake_model,
    }


@app.get("/")
async def root():
    return RedirectResponse(url="/console/")


@app.get("/api")
async def api_index():
    return {
        "service": "RalfIIA Hybrid Ops Copilot - AMD Core Engine",
        "console": "/console/",
        "endpoints": {
            "health": "/health",
            "execute_harness": "POST /api/v1/execute-harness",
            "execute_harness_body": "POST /api/v1/execute-harness/tasks",
            "route_task": "POST /api/v1/route-task",
            "chat": "POST /api/v1/chat",
            "showcase": "POST /api/v1/demo/showcase",
            "events": "GET /events",
            "services": "GET /services",
        },
    }


# --- Track 1: Harness I/O (file-based, AMD scoring environment) ---


@app.post("/api/v1/execute-harness")
async def execute_harness_flow():
    """
    Track 1 Harness: lee /input/tasks.json → procesa → escribe /output/results.json
    """
    try:
        result = await execute_harness_from_file()
        mongo_store.append_event(
            {"type": "harness_completed", "processed": result["processed_tasks"]}
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/execute-harness/tasks")
async def execute_harness_tasks(body: Track1Input):
    """Harness alternativo vía JSON body (demo / tests sin volumen Docker)."""
    tasks = [t.model_dump() for t in body.tasks]
    result = await execute_harness_from_tasks(tasks)
    mongo_store.append_event(
        {"type": "harness_body", "processed": result["processed_tasks"]}
    )
    return result


@app.post("/api/v1/route-task")
async def route_single_task(item: TaskItem):
    """Enruta una sola tarea con la lógica híbrida Track 1."""
    out = await process_single_task(item.task_id, item.prompt)
    mongo_store.append_event(
        {
            "type": "route_task",
            "task_id": item.task_id,
            "routing": out["metadata"].get("routing"),
        }
    )
    return out


# --- Track 3: A2A mesh + demo integrado ---


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    sid = req.session_id or str(uuid.uuid4())
    out = await orchestrator.delegate_sync(req.message, sid)
    return ChatResponse(
        session_id=out["session_id"],
        result=out.get("result"),
        events=out.get("events", []),
        error=out.get("error"),
    )


@app.get("/events")
async def get_events(limit: int = 40):
    return {"events": orchestrator.get_recent_events(limit)}


@app.get("/services")
async def get_services():
    services = await orchestrator.list_registered_services()
    return {"services": services, "gateway": settings.public_base_url}


@app.get("/api/v1/transactions")
async def get_transactions(limit: int = 20):
    return {"transactions": mongo_store.list_transactions(limit)}


@app.get("/api/v1/routing/stats")
async def routing_stats():
    txns = mongo_store.list_transactions(50)
    local_tokens = sum(t.get("tokens_local", 0) for t in txns)
    remote_tokens = sum(t.get("tokens_remote", 0) for t in txns)
    return {
        "total_transactions": len(txns),
        "tokens_local": local_tokens,
        "tokens_remote": remote_tokens,
        "scored_tokens_amd": remote_tokens,
        "savings_note": "Local Ollama tokens score as 0 in AMD Track 1",
    }


@app.get("/api/v1/credits/status")
async def credits_status():
    from app.services.credits_check import fireworks_health, ollama_health

    fw = await fireworks_health()
    ol = await ollama_health()
    sq = await smart_quoter_bridge.smart_quoter_health()
    return {
        "fireworks": {
            "configured": bool(settings.fireworks_api_key),
            "ok": fw.get("ok", False),
            "base_url": settings.fireworks_api_base,
            "allowed_models": ALLOWED_MODELS,
            "hint": (
                "Sin API key — ver docs/RAFAEL_AMD_PANEL.md"
                if not settings.fireworks_api_key
                else "API key presente"
            ),
        },
        "ollama": ol,
        "smart_quoter_live": sq,
        "ngrok": {
            "base": settings.public_ngrok_base,
            "ui": f"{settings.public_ngrok_base}{settings.public_amd_ops_path}/",
            "api": f"{settings.public_ngrok_base}{settings.public_amd_api_path}/health",
        },
        "smart_portal": settings.smart_portal_url,
    }


@app.get("/api/v1/demo/links")
async def demo_links():
    base = settings.public_ngrok_base.rstrip("/")
    return {
        "jury_urls": {
            "amd_console_ui": f"{base}{settings.public_amd_ops_path}/",
            "amd_api_health": f"{base}{settings.public_amd_api_path}/health",
            "harness_test": f"{base}{settings.public_amd_api_path}/api/v1/execute-harness/tasks",
        },
        "internal": {
            "smart_portal": settings.smart_portal_url,
            "smart_quoter": settings.smart_quoter_url,
        },
        "tracks": ["Track 1 Harness", "Track 3 Unicorn"],
    }


@app.get("/api/v1/demo/smart-quoter-status")
async def smart_quoter_status():
    return await smart_quoter_bridge.smart_quoter_health()


@app.post("/api/v1/demo/showcase")
async def demo_showcase():
    """Demo automática para jurado — 3 pasos sin Fireworks."""
    steps = [
        "Clasifica sentiment: el servicio PC Doctor fue excelente hoy",
        "Cotizar diagnóstico onsite y SSD 1TB para cliente PC Doctor",
        "Health check del stack ralfiia y plan de remediacion",
    ]
    outcomes = []
    last_answer = ""
    for msg in steps:
        out = await orchestrator.delegate_sync(msg)
        result = out.get("result") or {}
        last_answer = str(result.get("content") or result.get("message") or result)[:800]
        outcomes.append({"message": msg[:60], "ok": not out.get("error")})
        mongo_store.append_event({"type": "showcase_step", "message": msg[:80]})

    sq = await smart_quoter_bridge.smart_quoter_health()
    t1 = await process_single_task("showcase-t1", steps[0])

    return {
        "summary": (
            f"Demo OK: {len(outcomes)} delegaciones A2A · "
            f"Smart Quoter {'LIVE' if sq.get('ok') else 'offline'} · "
            f"Track1 local routing: {t1['metadata'].get('routing')}"
        ),
        "steps": outcomes,
        "last_answer": last_answer,
        "smart_quoter": sq,
        "track1_sample": t1,
        "public_console": f"{settings.public_ngrok_base}{settings.public_amd_ops_path}/",
    }


@app.post("/api/v1/demo/integrated")
async def demo_integrated(req: ChatRequest):
    quote_num = await smart_quoter_bridge.next_quote_number()
    sq_health = await smart_quoter_bridge.smart_quoter_health()
    sample = req.message
    if quote_num and "cotiz" in sample.lower():
        sample = f"[{quote_num}] {sample}"
    mesh = await orchestrator.delegate_sync(sample, req.session_id)
    return {
        "session_id": mesh.get("session_id"),
        "smart_quoter": {"health": sq_health, "next_quote_number": quote_num},
        "a2a_mesh": mesh,
        "public_ui": f"{settings.public_ngrok_base}{settings.public_amd_ops_path}/",
    }


@app.post("/api/v1/track1/evaluate")
async def track1_evaluate(req: ChatRequest):
    return await evaluate_task(req.message)
