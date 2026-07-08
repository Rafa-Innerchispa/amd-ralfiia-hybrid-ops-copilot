"""LangGraph ReAct loop — Reason -> Act -> Observe (SRE Watchdog)."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from pydantic import BaseModel

from app.settings import settings
from shared.a2a_protocol import ResponseFormat
from shared.runtime_i18n import format_watchdog_report, normalize_lang


class WatchdogState(TypedDict):
    messages: Annotated[list, "conversation"]
    observations: Annotated[list, "observe_log"]
    structured_response: dict[str, Any]
    lang: str


class RemediationBlueprint(BaseModel):
    incident_id: str
    severity: str
    affected_services: list[str]
    root_cause_hypothesis: str
    remediation_steps: list[str]
    status: str


STACK_CHECKS = (
    ("ralfiia_root_gateway", "http://127.0.0.1:8220/health"),
    ("ralfiia_agent_smart_quoter", "http://127.0.0.1:8221/health"),
    ("ralfiia_agent_watchdog", "http://127.0.0.1:8222/health"),
)


def _live_health_scan() -> dict[str, Any]:
    """Health scan real — GET /health en servicios del stack AMD ops."""
    results: list[dict[str, Any]] = []
    failing: str | None = None
    for name, url in STACK_CHECKS:
        healthy = False
        latency_ms = 0
        detail = ""
        try:
            t0 = __import__("time").perf_counter()
            r = httpx.get(url, timeout=4.0)
            latency_ms = int((__import__("time").perf_counter() - t0) * 1000)
            healthy = r.status_code == 200
            if healthy:
                detail = "OK"
            else:
                detail = f"HTTP {r.status_code}"
        except Exception as exc:
            detail = str(exc)[:120]
        if not healthy and failing is None:
            failing = name
        results.append(
            {
                "container": name,
                "healthy": healthy,
                "latency_ms": latency_ms,
                "endpoint": url,
                "detail": detail,
            }
        )
    return {"scan_ts": "live", "containers": results, "incident": failing}


def build_react_graph():
    memory = MemorySaver()
    llm = ChatOllama(
        base_url=settings.ollama_base_url.replace("host.docker.internal", "127.0.0.1"),
        model=settings.watchdog_ollama_model,
        temperature=0.1,
    )

    def reason_node(state: WatchdogState) -> WatchdogState:
        scan = _live_health_scan()
        incident = scan.get("incident")
        prompt = (
            f"Health scan results: {scan}\n"
            f"User context: {state['messages'][-1] if state['messages'] else 'routine check'}\n"
            "Reason about SRE incident severity and next action."
        )
        response = llm.invoke(
            [
                SystemMessage(content="You are an SRE watchdog agent. Be concise and operational."),
                HumanMessage(content=prompt),
            ]
        )
        state["observations"].append({"phase": "reason", "scan": scan, "llm": response.content})
        state["messages"].append(response)
        state["structured_response"] = {
            "phase": "reason",
            "incident_detected": bool(incident),
            "incident_service": incident,
            "containers": scan.get("containers", []),
        }
        return state

    def act_node(state: WatchdogState) -> WatchdogState:
        sr = state.get("structured_response", {})
        incident = sr.get("incident_service")
        req_lang = normalize_lang(state.get("lang", "es"))
        if req_lang == "en":
            steps = [
                "Collect logs: docker logs --tail 200 <service>",
                "Verify /health endpoint",
                "Restart: ./scripts/start_all.sh",
                "Notify recovery watchdog via MCP if still down",
            ]
            if incident:
                steps.insert(0, f"Priority: restore {incident} — check /tmp/ralfiia-amd-ops/*.log")
            hypothesis = (
                f"Service {incident} not responding on /health"
                if incident
                else "All stack health endpoints returned HTTP 200"
            )
            no_action = ["No action required — stack healthy"]
        else:
            steps = [
                "Recoger logs: docker logs --tail 200 <servicio>",
                "Verificar endpoint /health",
                "Reiniciar: ./scripts/start_all.sh",
                "Notificar watchdog de recuperación vía MCP si sigue caído",
            ]
            if incident:
                steps.insert(0, f"Prioridad: restaurar {incident} — revisar /tmp/ralfiia-amd-ops/*.log")
            hypothesis = (
                f"El servicio {incident} no responde en /health"
                if incident
                else "Todos los endpoints /health del stack respondieron HTTP 200"
            )
            no_action = ["Sin acción requerida — stack saludable"]
        unhealthy = [c["container"] for c in sr.get("containers", []) if not c.get("healthy")]
        blueprint = RemediationBlueprint(
            incident_id=f"INC-{incident or 'CLEAR'}",
            severity="high" if incident else "low",
            affected_services=unhealthy,
            root_cause_hypothesis=hypothesis,
            remediation_steps=steps if incident else no_action,
            status="action_required" if incident else "healthy",
        )
        state["observations"].append({"phase": "act", "blueprint": blueprint.model_dump()})
        state["structured_response"] = blueprint.model_dump()
        return state

    def observe_node(state: WatchdogState) -> WatchdogState:
        sr = state["structured_response"]
        post_scan = _live_health_scan()
        still_failing = post_scan.get("incident")
        resolved = not still_failing and sr.get("status") != "action_required"
        state["observations"].append({"phase": "observe", "post_scan": post_scan, "resolved": resolved})
        sr["observe_resolved"] = resolved
        req_lang = normalize_lang(state.get("lang", "es"))
        ok_lbl, down_lbl = ("OK", "CAÍDO") if req_lang == "es" else ("OK", "DOWN")
        sr["post_scan_summary"] = [
            f"{c['container']}: {ok_lbl if c['healthy'] else down_lbl}"
            for c in post_scan.get("containers", [])
        ]
        state["structured_response"] = sr
        return state

    graph = StateGraph(WatchdogState)
    graph.add_node("reason", reason_node)
    graph.add_node("act", act_node)
    graph.add_node("observe", observe_node)
    graph.set_entry_point("reason")
    graph.add_edge("reason", "act")
    graph.add_edge("act", "observe")
    graph.add_edge("observe", END)

    return graph.compile(checkpointer=memory)


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_react_graph()
    return _graph


def run_watchdog(user_text: str, thread_id: str, lang: str = "es") -> dict[str, Any]:
    lang = normalize_lang(lang)
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    initial: WatchdogState = {
        "messages": [HumanMessage(content=user_text)],
        "observations": [],
        "structured_response": {},
        "lang": lang,
    }
    final = graph.invoke(initial, config=config)
    sr = final.get("structured_response", {})
    status = "completed" if sr.get("status") in ("healthy", "action_required") else "error"
    msg = format_watchdog_report(sr, lang)
    rf = ResponseFormat(status="completed" if status == "completed" else "error", message=msg)
    return {
        "structured_response": sr,
        "observations": final.get("observations", []),
        "response_format": rf.model_dump(),
        "metadata": {
            "runtime": "local",
            "provider_id": "local",
            "ollama_base_url": settings.ollama_base_url,
            "model": settings.watchdog_ollama_model,
            "tokens_local": 0,
            "tokens_remote": 0,
            "routing_label": (
                "Watchdog SRE — live /health scan"
                if lang == "en"
                else "Watchdog SRE — escaneo /health en vivo"
            ),
        },
    }
