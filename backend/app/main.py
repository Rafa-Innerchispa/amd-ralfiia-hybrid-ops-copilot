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
    DEFAULT_COMPLEX_MODEL,
    execute_harness_from_file,
    execute_harness_from_tasks,
    process_single_task,
)
from app.integrations import smart_quoter_bridge
from app.orchestrator import orchestrator
from app.runtime_providers import list_providers, select_ollama_url
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
    lang: str = "es"


class ChatResponse(BaseModel):
    session_id: str
    result: dict | None = None
    events: list
    error: dict | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        seed_if_empty()
        mongo_store.append_event({"type": "system_boot", "service": "amd-core-engine"})
    except Exception:
        pass
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
        "amd_cloud_configured": bool(settings.amd_cloud_api_token),
        "amd_inference_configured": bool(settings.amd_inference_base_url),
        "ollama_model": settings.ollama_intake_model,
        "ollama_amd_url": settings.ollama_amd_url,
        "ollama_primary_url": settings.ollama_primary_url,
        "runtime_providers": [
            {
                "id": p.provider_id,
                "url": p.ollama_base_url,
                "available": p.available,
                "label": p.label,
            }
            for p in list_providers()
        ],
        "selected_ollama": select_ollama_url(prefer_amd=True).provider_id,
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
            "runtime_providers": "GET /api/v1/runtime/providers",
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


@app.get("/api/v1/runtime/providers")
async def runtime_providers():
    """Lista proveedores Ollama (AMD .5, primary .4, localhost) y selección activa."""
    providers = list_providers()
    selected = select_ollama_url(prefer_amd=True)
    return {
        "ok": True,
        "selected": {
            "provider_id": selected.provider_id,
            "ollama_base_url": selected.ollama_base_url,
            "available": selected.available,
            "reason": selected.reason,
        },
        "providers": [
            {
                "provider_id": p.provider_id,
                "ollama_base_url": p.ollama_base_url,
                "label": p.label,
                "reason": p.reason,
                "available": p.available,
            }
            for p in providers
        ],
        "settings": {
            "ollama_amd_url": settings.ollama_amd_url,
            "ollama_primary_url": settings.ollama_primary_url,
            "ollama_intake_model": settings.ollama_intake_model,
        },
    }


@app.post("/api/v1/notify-gemma")
async def notify_gemma_activation():
    """Trigger WhatsApp alert via Evolution API when a judge needs Gemma GPU activated."""
    evo_base = "http://192.168.1.4:8082"
    evo_key = "swarm_os_evolution_key_2026"
    evo_inst = "RalphiIA-pcdoctor"
    dest_number = "593999059000"
    
    text = (
        "🚨 *Alerta AMD Hackathon*: Un evaluador está probando la aplicación y requiere activar "
        "el modelo Gemma en la GPU de AMD (Jupyter Server).\n\n"
        "Por favor, enciende la instancia de Jupyter y levanta el servicio vLLM/Gemma.\n"
        "Jupyter URL: https://radeon-global.anruicloud.com/instances/hf-129-3b565f68/lab"
    )
    
    url = f"{evo_base}/message/sendText/{evo_inst}"
    headers = {"apikey": evo_key, "Content-Type": "application/json"}
    payload = {"number": dest_number, "text": text, "delay": 800}
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json=payload, headers=headers, timeout=15.0)
            if r.status_code in (200, 201):
                return {"ok": True, "message": "Notification sent successfully via WhatsApp!"}
            return {"ok": False, "error": f"HTTP {r.status_code}: {r.text}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# --- Track 3: A2A mesh + demo integrado ---


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    sid = req.session_id or str(uuid.uuid4())
    out = await orchestrator.delegate_sync(req.message, sid, lang=req.lang)
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
    from app.amd_cloud_client import account_health
    from app.services.credits_check import fireworks_health, ollama_health

    fw = await fireworks_health()
    ol = await ollama_health()
    amd = await account_health()
    sq = await smart_quoter_bridge.smart_quoter_health()
    services = await orchestrator.list_registered_services()
    return {
        "fireworks": {
            **fw,
            "configured": bool(settings.fireworks_api_key),
            "base_url": settings.fireworks_api_base,
            "allowed_models": ALLOWED_MODELS,
            "default_complex": DEFAULT_COMPLEX_MODEL,
        },
        "amd_cloud": {
            **amd,
            "inference_base_url": settings.amd_inference_base_url or None,
            "inference_model": settings.amd_inference_model,
            "next_step": (
                "Crear droplet MI300X en AMD Developer Cloud y pegar AMD_INFERENCE_BASE_URL"
                if amd.get("ok") and not settings.amd_inference_base_url
                else None
            ),
        },
        "ollama": ol,
        "a2a_agents": services,
        "smart_quoter_live": {
            **sq,
            "label": "PC Doctor product (optional)",
            "url": settings.smart_quoter_url,
        },
        "ngrok": {
            "base": settings.public_ngrok_base,
            "ui": f"{settings.public_ngrok_base}{settings.public_amd_ops_path}/",
        },
        "smart_portal": settings.smart_portal_url,
        "agent_urls": {
            "smart_quoter_a2a": settings.smart_quoter_agent_url,
            "watchdog_a2a": settings.watchdog_agent_url,
        },
    }


@app.get("/api/v1/demo/scenarios")
async def demo_scenarios():
    """Guía bilingüe — qué probar, qué hace cada escenario, qué guarda en Mongo."""
    return {
        "github": "https://github.com/Rafa-Innerchispa/amd-ralfiia-hybrid-ops-copilot",
        "mongo": {
            "db": settings.mongo_db,
            "collections": [
                "amd_hybrid_ops_transactions — cada routing (agente, modelo, tokens local/remoto)",
                "amd_hybrid_ops_events — delegaciones A2A y pasos demo",
                "amd_hybrid_ops_sessions — memoria de conversación",
            ],
            "seed": "10 transacciones demo PC Doctor (cotizaciones, SRE, routing)",
        },
        "amd_stack": {
            "local_ollama": {
                "role": "Track 1 — tareas simples, 0 tokens remotos AMD",
                "model": settings.ollama_intake_model,
                "url": settings.ollama_base_url,
            },
            "fireworks_cloud": {
                "role": "Track 1 complejo — DeepSeek v4 Pro en Fireworks (GPUs AMD MI300X)",
                "models": ALLOWED_MODELS,
                "needs": "FIREWORKS_API_KEY en .env",
            },
        },
        "scenarios": [
            {
                "id": "sentiment",
                "title_es": "Análisis de sentimiento (Ollama local)",
                "title_en": "Sentiment analysis (local Ollama)",
                "example_query_es": (
                    "Analiza el sentimiento del feedback del cliente. Texto: "
                    "«El técnico de PC Doctor llegó puntual, explicó todo con claridad "
                    "y dejó mi laptop funcionando perfecta. Muy recomendado.» "
                    "Responde: POSITIVO, NEGATIVO o NEUTRAL."
                ),
                "example_query_en": (
                    "Analyze customer feedback sentiment. Text: "
                    "«The PC Doctor technician arrived on time, explained everything clearly, "
                    "and left my laptop running perfectly. Highly recommended.» "
                    "Reply: POSITIVE, NEGATIVE, or NEUTRAL."
                ),
                "what_happens_es": (
                    "Evalúa el texto entre comillas (reseña de cliente de ejemplo). "
                    "Gateway → Ollama qwen2.5 en nodo AMD .5. Veredicto POSITIVO/NEGATIVO/NEUTRAL. "
                    "0 tokens Fireworks. API AMD Developer Cloud: no se usa."
                ),
                "what_happens_en": (
                    "Evaluates quoted sample customer review text. "
                    "Gateway → Ollama qwen2.5 on AMD node .5. Verdict POSITIVE/NEGATIVE/NEUTRAL. "
                    "0 Fireworks tokens. AMD Developer Cloud API: not used."
                ),
                "expects_es": ["routing: local", "tokens_remote: 0", "veredicto de sentimiento"],
                "expects_en": ["routing: local", "tokens_remote: 0", "sentiment verdict"],
            },
            {
                "id": "quote",
                "title_es": "Cotización A2A (Smart Quoter :8221)",
                "title_en": "A2A quote (Smart Quoter :8221)",
                "example_query_es": (
                    "Cotizar diagnóstico en sitio e instalación de SSD 1TB para cliente PC Doctor"
                ),
                "example_query_en": (
                    "Quote onsite diagnosis and 1TB SSD installation for PC Doctor customer"
                ),
                "what_happens_es": (
                    "Agente A2A :8221 (CrewAI) genera cotización demo. "
                    "Extracción con Ollama en nodo AMD .5: Diagnóstico en sitio $45 + SSD 1TB $85 ≈ $130. "
                    "Fireworks solo si pides pulido ejecutivo. API AMD Developer Cloud: no se usa."
                ),
                "what_happens_en": (
                    "A2A agent :8221 (CrewAI) builds demo quote. "
                    "Extraction via Ollama on AMD node .5: Onsite diagnosis $45 + 1TB SSD $85 ≈ $130. "
                    "Fireworks only if executive polish requested. AMD Developer Cloud API: not used."
                ),
                "expects_es": ["delegation_completed", "agente: smart_quoter_agent", "líneas y total"],
                "expects_en": ["delegation_completed", "agent: smart_quoter_agent", "line items / total"],
            },
            {
                "id": "sre",
                "title_es": "Health check SRE (Watchdog :8222)",
                "title_en": "SRE health check (Watchdog :8222)",
                "example_query_es": "Health check del stack ralfiia y plan de remediación",
                "example_query_en": "Health check ralfiia stack and remediation plan",
                "what_happens_es": (
                    "Watchdog :8222 (LangGraph) hace sondas HTTP reales en :8220/:8221/:8222. "
                    "Plan de remediación si algún servicio no responde. Ollama local en el agente."
                ),
                "what_happens_en": (
                    "Watchdog :8222 (LangGraph) runs live HTTP probes on :8220/:8221/:8222. "
                    "Remediation plan if a service is down. Local Ollama on the agent."
                ),
                "expects_es": ["agente: watchdog_sre_agent", "sondas /health", "plan de remediación"],
                "expects_en": ["agent: watchdog_sre_agent", "/health probes", "remediation plan"],
            },
            {
                "id": "complex",
                "title_es": "Tarea compleja → Fireworks DeepSeek",
                "title_en": "Complex task → Fireworks DeepSeek",
                "example_query_es": (
                    "Explica paso a paso el algoritmo de autovalores de matrices en Python"
                ),
                "example_query_en": (
                    "Explain matrix eigenvalue algorithm step by step in Python"
                ),
                "what_happens_es": (
                    "Track 1 detecta tarea compleja → API Fireworks (DeepSeek v4 Pro en GPUs AMD MI300X). "
                    "Tokens remotos > 0. Ollama local no se usa. API AMD Developer Cloud: no se usa."
                ),
                "what_happens_en": (
                    "Track 1 routes complex task → Fireworks API (DeepSeek v4 Pro on AMD MI300X GPUs). "
                    "Remote tokens > 0. Local Ollama not used. AMD Developer Cloud API: not used."
                ),
                "expects_es": ["routing: fireworks", "tokens_remote > 0", "respuesta técnica"],
                "expects_en": ["routing: fireworks", "tokens_remote > 0", "technical answer"],
            },
        ],
        "optional_integrations": {
            "smart_quoter_product": {
                "url": settings.smart_quoter_url,
                "note_es": "Producto PC Doctor real en :2026 — opcional, no es el agente A2A del hackathon",
                "note_en": "Real PC Doctor product :2026 — optional, not the hackathon A2A worker",
            },
        },
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
        "github": "https://github.com/Rafa-Innerchispa/amd-ralfiia-hybrid-ops-copilot",
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
