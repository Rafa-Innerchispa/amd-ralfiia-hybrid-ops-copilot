"""Smart Quoter A2A Server — CrewAI worker on :8221."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException
from pymongo import MongoClient

from app.crew_pipeline import run_quote_pipeline
from app.settings import settings
from shared.a2a_protocol import (
    AgentAuthentication,
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    A2ATaskRequest,
    A2ATaskResponse,
)


def _auth_ok(authorization: str | None) -> bool:
    if not authorization:
        return False
    token = authorization.replace("Bearer ", "").strip()
    return token == settings.agent_auth


def agent_card() -> AgentCard:
    base = settings.public_base_url.rstrip("/")
    return AgentCard(
        name="smart_quoter_agent",
        description="Extracts data and creates corporate technology quotes (CrewAI + Hybrid Router)",
        url=f"{base}/",
        version="1.0.0",
        authentication=AgentAuthentication(schemes=["Bearer"]),
        capabilities=AgentCapabilities(pushNotifications=True),
        skills=[
            AgentSkill(
                id="create_quote",
                name="Quote Engine",
                description="Parse audio/text and build structured quote line items",
                tags=["quoting", "crewai", "ollama", "fireworks"],
                examples=["Cotizar 2 SSD y diagnóstico para cliente PC Doctor"],
            )
        ],
    )


app = FastAPI(title="Smart Quoter A2A Agent", version="1.0.0")


@app.get("/health")
async def health():
    return {"ok": True, "agent": "smart_quoter_agent", "port": settings.agent_port}


@app.get("/.well-known/agent.json")
async def well_known_agent():
    return agent_card().model_dump()


@app.post("/tasks")
async def handle_task(payload: A2ATaskRequest, authorization: str | None = Header(default=None)):
    if not _auth_ok(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")

    text = " ".join(p.text for p in payload.message.parts)
    req_lang = (payload.message.metadata or {}).get("lang", "es")
    result = await run_quote_pipeline(text, lang=req_lang)
    result["sessionId"] = payload.sessionId
    result["id"] = payload.id

    try:
        client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
        client[settings.mongo_db]["amd_hybrid_ops_transactions"].insert_one(
            {
                "transaction_id": str(uuid.uuid4()),
                "agent": "smart_quoter_agent",
                "runtime": result.get("metadata", {}).get("runtime"),
                "model": result.get("metadata", {}).get("model"),
                "tokens_local": result.get("metadata", {}).get("tokens_local", 0),
                "tokens_remote": result.get("metadata", {}).get("tokens_remote", 0),
                "action": "create_quote",
                "status": result.get("status"),
                "ts": datetime.now(timezone.utc).isoformat(),
                "session_id": payload.sessionId,
            }
        )
    except Exception:
        pass

    parsed = A2ATaskResponse.model_validate(result)
    return {**parsed.model_dump(), **parsed.to_client_dict()}
