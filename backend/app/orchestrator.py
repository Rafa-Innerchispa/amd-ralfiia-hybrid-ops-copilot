"""Google ADK-style Root Orchestrator — A2A delegation mesh."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from app import mongo_store
from app.schemas import AgentCard, A2AMessage, A2AMessagePart, A2ATaskRequest, A2ATaskResponse
from app.settings import settings

# --- Google ADK pattern: InMemory Session Service ---


@dataclass
class SessionState:
    session_id: str
    conversation_id: str
    memory: List[Dict[str, str]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class InMemorySessionService:
    """Explicit session/state/memory isolation per Google ADK tutorial."""

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionState] = {}

    def get_or_create(self, session_id: str | None = None) -> SessionState:
        sid = session_id or str(uuid.uuid4())
        if sid not in self._sessions:
            self._sessions[sid] = SessionState(session_id=sid, conversation_id=sid)
            mongo_store.upsert_session(sid, {"conversation_id": sid, "status": "active"})
        return self._sessions[sid]

    def append_turn(self, session_id: str, role: str, content: str) -> None:
        state = self.get_or_create(session_id)
        state.memory.append({"role": role, "content": content})
        mongo_store.upsert_session(session_id, {"memory_len": len(state.memory)})


# --- Google ADK pattern: Remote Agent Connections ---


class RemoteAgentConnections:
    """HTTP authorization headers (Basic/Bearer) mapped from KNOWN_AUTH env vars."""

    def __init__(self) -> None:
        self.known_agents: Dict[str, Dict[str, str]] = {
            "smart_quoter_agent": {
                "url": settings.smart_quoter_agent_url.rstrip("/"),
                "auth": settings.smart_quoter_agent_auth,
                "scheme": "Bearer",
            },
            "watchdog_sre_agent": {
                "url": settings.watchdog_agent_url.rstrip("/"),
                "auth": settings.watchdog_agent_auth,
                "scheme": "Bearer",
            },
            # AMD tutorial aliases
            "pizza_seller_agent": {
                "url": settings.pizza_seller_agent_url.rstrip("/"),
                "auth": settings.pizza_seller_agent_auth,
                "scheme": "Bearer",
            },
            "burger_seller_agent": {
                "url": settings.burger_seller_agent_url.rstrip("/"),
                "auth": settings.burger_seller_agent_auth,
                "scheme": "Bearer",
            },
        }

    def headers_for(self, agent_name: str) -> Dict[str, str]:
        cfg = self.known_agents.get(agent_name, {})
        token = cfg.get("auth", "")
        scheme = cfg.get("scheme", "Bearer")
        if ":" in token and scheme == "Basic":
            import base64

            encoded = base64.b64encode(token.encode()).decode()
            return {"Authorization": f"Basic {encoded}"}
        return {"Authorization": f"Bearer {token}"}

    def url_for(self, agent_name: str) -> str:
        return self.known_agents.get(agent_name, {}).get("url", "")


# --- Routing intelligence ---

QUOTE_KEYWORDS = re.compile(
    r"\b(cotiz|cotizar|quote|precio|paquete|presupuesto|diagnóstico|diagnostico|ssd|onsite)\b",
    re.I,
)
SRE_KEYWORDS = re.compile(
    r"\b(health check|watchdog|incident|caída|caida|container|docker|remediation|sre|alerta|stack ralfiia)\b",
    re.I,
)
TRACK1_LOCAL = re.compile(
    r"\b(sentiment|clasifica|classify|classification|ner|named entity|positive|negative|neutral|extract entity|label|summarize|summary)\b",
    re.I,
)
TRACK1_COMPLEX = re.compile(
    r"\b(code|debug|math|puzzle|matrix|algorithm|eigenvalue|implement|python|recursion|proof|compile)\b",
    re.I,
)


def resolve_target_agent(task: str) -> str:
    if TRACK1_COMPLEX.search(task):
        return "track1_fireworks"
    if TRACK1_LOCAL.search(task):
        return "track1_local"
    if SRE_KEYWORDS.search(task):
        return "watchdog_sre_agent"
    if QUOTE_KEYWORDS.search(task):
        return "smart_quoter_agent"
    return "smart_quoter_agent"


async def fetch_agent_card(agent_name: str, connections: RemoteAgentConnections) -> AgentCard | None:
    url = connections.url_for(agent_name)
    if not url:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{url}/.well-known/agent.json",
                headers=connections.headers_for(agent_name),
            )
            r.raise_for_status()
            return AgentCard.model_validate(r.json())
    except Exception:
        return None


async def send_task(
    agent_name: str,
    task: str,
    target_url: str,
    auth_token: str,
    session_id: str,
    *,
    scheme: str = "Bearer",
    lang: str = "es",
) -> dict[str, Any]:
    """Core A2A task propagation — metadata + acceptedOutputModes."""
    task_id = str(uuid.uuid4())
    payload = A2ATaskRequest(
        id=task_id,
        sessionId=session_id,
        message=A2AMessage(
            role="user",
            parts=[A2AMessagePart(text=task)],
            metadata={"conversation_id": session_id, "delegated_by": "root_gateway", "lang": lang},
        ),
        acceptedOutputModes=["text", "text/plain"],
    )
    headers = {"Authorization": f"{scheme} {auth_token}", "Content-Type": "application/json"}
    if ":" in auth_token and scheme == "Basic":
        import base64

        headers["Authorization"] = f"Basic {base64.b64encode(auth_token.encode()).decode()}"

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(f"{target_url.rstrip('/')}/tasks", json=payload.model_dump(), headers=headers)
        response.raise_for_status()
        return response.json()


@dataclass
class Event:
    """AsyncIterator[Event] pipeline unit (Google ADK purchasing runner pattern)."""

    type: str
    data: Dict[str, Any]
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RootOrchestrator:
    """Root Agent — session, routing, A2A delegation."""

    def __init__(self) -> None:
        self.sessions = InMemorySessionService()
        self.connections = RemoteAgentConnections()
        self._event_buffer: List[Dict[str, Any]] = []

    def _log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        record = {"type": event_type, **data}
        self._event_buffer.insert(0, record)
        self._event_buffer = self._event_buffer[:200]
        mongo_store.append_event(record)

    async def run_async(
        self, user_message: str, session_id: str | None = None, lang: str = "es", force_model: str | None = None, preferred_gemma_backend: str | None = "auto"
    ) -> AsyncIterator[Event]:
        """Process real-time async event stream for UI / ADK consumers."""
        state = self.sessions.get_or_create(session_id)
        sid = state.session_id
        self.sessions.append_turn(sid, "user", user_message)

        yield Event(type="session_started", data={"session_id": sid})
        self._log_event("session_started", {"session_id": sid, "message_preview": user_message[:120]})

        if force_model == "gemma":
            target = "track1_fireworks"
        else:
            target = resolve_target_agent(user_message)
            
        yield Event(type="routing_decision", data={"target_agent": target, "session_id": sid})
        self._log_event("routing_decision", {"target_agent": target, "session_id": sid})

        if target in ("track1_local", "track1_fireworks"):
            from app.hybrid_engine import process_single_task

            task_id = f"chat-{sid[:8]}"
            try:
                row = await process_single_task(
                    task_id, 
                    user_message, 
                    lang=lang, 
                    force_model=force_model, 
                    preferred_gemma_backend=preferred_gemma_backend
                )
                answer = row.get("answer", "")
                meta = row.get("metadata", {})
                client_dict = {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": answer,
                    "status": "completed",
                    "metadata": meta,
                }
                self.sessions.append_turn(sid, "assistant", answer)
                yield Event(type="delegation_completed", data={"agent": target, "result": client_dict})
                self._log_event(
                    "delegation_completed",
                    {
                        "agent": target,
                        "runtime": meta.get("provider_id") or meta.get("routing"),
                        "model": meta.get("model"),
                        "tokens_remote": meta.get("tokens_remote", 0),
                        "tokens_local": meta.get("tokens_local", 0),
                    },
                )
            except Exception as exc:
                err = {"error": str(exc), "agent": target}
                yield Event(type="delegation_failed", data=err)
                self._log_event("delegation_failed", err)
            return

        card = await fetch_agent_card(target, self.connections)
        if card:
            yield Event(type="agent_card_resolved", data={"agent": target, "card": card.model_dump()})
            self._log_event("agent_card_resolved", {"agent": target, "skills": [s.id for s in card.skills]})

        cfg = self.connections.known_agents.get(target, {})
        target_url = cfg.get("url", "")
        auth = cfg.get("auth", "")
        scheme = cfg.get("scheme", "Bearer")

        yield Event(type="delegation_started", data={"agent": target, "url": target_url})
        self._log_event("delegation_started", {"agent": target, "url": target_url})

        try:
            result = await send_task(
                target, user_message, target_url, auth, sid, scheme=scheme, lang=lang
            )
            parsed = A2ATaskResponse.model_validate(result) if "status" in result else None
            client_dict = parsed.to_client_dict() if parsed else result
            self.sessions.append_turn(sid, "assistant", client_dict.get("content", str(result)))
            yield Event(type="delegation_completed", data={"agent": target, "result": client_dict})
            self._log_event(
                "delegation_completed",
                {
                    "agent": target,
                    "runtime": result.get("metadata", {}).get("runtime", "unknown"),
                    "model": result.get("metadata", {}).get("model", "unknown"),
                    "tokens_remote": result.get("metadata", {}).get("tokens_remote", 0),
                    "tokens_local": result.get("metadata", {}).get("tokens_local", 0),
                },
            )
        except Exception as exc:
            err = {"error": str(exc), "agent": target}
            yield Event(type="delegation_failed", data=err)
            self._log_event("delegation_failed", err)

    async def delegate_sync(
        self, user_message: str, session_id: str | None = None, lang: str = "es", force_model: str | None = None, preferred_gemma_backend: str | None = "auto"
    ) -> dict[str, Any]:
        final: dict[str, Any] = {"events": [], "session_id": session_id}
        async for ev in self.run_async(user_message, session_id, lang=lang, force_model=force_model, preferred_gemma_backend=preferred_gemma_backend):
            final["events"].append({"type": ev.type, "data": ev.data, "ts": ev.ts})
            if ev.type == "delegation_completed":
                final["result"] = ev.data.get("result")
            if ev.type == "delegation_failed":
                final["error"] = ev.data
        state = self.sessions.get_or_create(final.get("session_id") or session_id)
        final["session_id"] = state.session_id
        return final

    async def list_registered_services(self) -> list[dict[str, Any]]:
        services = []
        for name in ("smart_quoter_agent", "watchdog_sre_agent"):
            card = await fetch_agent_card(name, self.connections)
            cfg = self.connections.known_agents.get(name, {})
            services.append(
                {
                    "name": name,
                    "url": cfg.get("url"),
                    "status": "online" if card else "unreachable",
                    "agent_card": card.model_dump() if card else None,
                }
            )
        return services

    def get_recent_events(self, limit: int = 40) -> list[dict[str, Any]]:
        mongo_events = mongo_store.list_events(limit)
        if mongo_events:
            return mongo_events
        return self._event_buffer[:limit]


orchestrator = RootOrchestrator()
