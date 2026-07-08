"""Watchdog SRE A2A Server — LangGraph on :8222."""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Header, HTTPException

from app.react_graph import run_watchdog
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
    return authorization.replace("Bearer ", "").strip() == settings.agent_auth


def agent_card() -> AgentCard:
    return AgentCard(
        name="watchdog_sre_agent",
        description="LangGraph ReAct SRE agent — health scans and remediation blueprints",
        url=settings.public_base_url.rstrip("/") + "/",
        version="1.0.0",
        authentication=AgentAuthentication(schemes=["Bearer"]),
        capabilities=AgentCapabilities(pushNotifications=True),
        skills=[
            AgentSkill(
                id="health_scan",
                name="Container Health Scan",
                description="Cyclical Reason-Act-Observe over local services",
                tags=["sre", "langgraph", "react"],
                examples=["Check docker health for ralfiia stack"],
            ),
            AgentSkill(
                id="remediation",
                name="Remediation Blueprint",
                description="Structured incident response plan",
                tags=["ops", "incident"],
                examples=["Service failure on agent-watchdog"],
            ),
        ],
    )


app = FastAPI(title="Watchdog SRE A2A Agent", version="1.0.0")


@app.get("/health")
async def health():
    return {"ok": True, "agent": "watchdog_sre_agent", "port": settings.agent_port}


@app.get("/.well-known/agent.json")
async def well_known_agent():
    return agent_card().model_dump()


@app.post("/tasks")
async def handle_task(payload: A2ATaskRequest, authorization: str | None = Header(default=None)):
    if not _auth_ok(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")

    text = " ".join(p.text for p in payload.message.parts)
    req_lang = (payload.message.metadata or {}).get("lang", "es")
    try:
        out = run_watchdog(text, thread_id=payload.sessionId, lang=req_lang)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Watchdog graph error: {exc}") from exc
    rf = out["response_format"]

    result = {
        "id": payload.id,
        "sessionId": payload.sessionId,
        "status": "completed" if rf["status"] == "completed" else "error",
        "message": rf["message"],
        "artifacts": [out["structured_response"]],
        "metadata": out["metadata"],
    }
    parsed = A2ATaskResponse.model_validate(result)
    return {**parsed.model_dump(), **parsed.to_client_dict()}
