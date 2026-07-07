"""LangGraph ReAct loop — Reason -> Act -> Observe (SRE Watchdog)."""

from __future__ import annotations

import random
from typing import Annotated, Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from pydantic import BaseModel

from app.settings import settings
from shared.a2a_protocol import ResponseFormat


class WatchdogState(TypedDict):
    messages: Annotated[list, "conversation"]
    observations: Annotated[list, "observe_log"]
    structured_response: dict[str, Any]


class RemediationBlueprint(BaseModel):
    incident_id: str
    severity: str
    affected_services: list[str]
    root_cause_hypothesis: str
    remediation_steps: list[str]
    status: str


MOCK_CONTAINERS = [
    "ralfiia_root_gateway",
    "ralfiia_agent_smart_quoter",
    "ralfiia_agent_watchdog",
    "ralfia-mcp",
    "ralfia-app",
]


def _simulate_health_scan() -> dict[str, Any]:
    failing = random.choice([None, None, MOCK_CONTAINERS[2]])
    results = []
    for name in MOCK_CONTAINERS:
        healthy = name != failing
        results.append(
            {
                "container": name,
                "healthy": healthy,
                "latency_ms": random.randint(12, 180),
                "restart_count": 0 if healthy else random.randint(1, 3),
            }
        )
    return {"scan_ts": "live", "containers": results, "incident": failing}


def build_react_graph():
    memory = MemorySaver()
    llm = ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        temperature=0.1,
    )

    def reason_node(state: WatchdogState) -> WatchdogState:
        scan = _simulate_health_scan()
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
        }
        return state

    def act_node(state: WatchdogState) -> WatchdogState:
        sr = state.get("structured_response", {})
        incident = sr.get("incident_service")
        steps = [
            "Collect container logs: docker logs --tail 200 <service>",
            "Verify health endpoint /health",
            "Restart service if unhealthy: docker compose restart <service>",
            "Notify AG-31 recovery watchdog via MCP",
        ]
        if incident:
            steps.insert(0, f"Isolate failing container: {incident}")
        blueprint = RemediationBlueprint(
            incident_id=f"INC-{random.randint(1000, 9999)}",
            severity="high" if incident else "low",
            affected_services=[incident] if incident else [],
            root_cause_hypothesis=(
                f"Simulated failure in {incident}" if incident else "All services nominal"
            ),
            remediation_steps=steps,
            status="action_required" if incident else "healthy",
        )
        state["observations"].append({"phase": "act", "blueprint": blueprint.model_dump()})
        state["structured_response"] = blueprint.model_dump()
        return state

    def observe_node(state: WatchdogState) -> WatchdogState:
        sr = state["structured_response"]
        post_scan = _simulate_health_scan()
        resolved = not post_scan.get("incident") and sr.get("status") != "action_required"
        state["observations"].append({"phase": "observe", "post_scan": post_scan, "resolved": resolved})
        sr["observe_resolved"] = resolved
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


def run_watchdog(user_text: str, thread_id: str) -> dict[str, Any]:
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    initial: WatchdogState = {
        "messages": [HumanMessage(content=user_text)],
        "observations": [],
        "structured_response": {},
    }
    final = graph.invoke(initial, config=config)
    sr = final.get("structured_response", {})
    status = "completed" if sr.get("status") in ("healthy", "action_required") else "error"
    msg = (
        f"SRE Watchdog Report\n"
        f"Severity: {sr.get('severity', 'unknown')}\n"
        f"Hypothesis: {sr.get('root_cause_hypothesis', 'n/a')}\n"
        f"Steps:\n" + "\n".join(f"- {s}" for s in sr.get("remediation_steps", []))
    )
    rf = ResponseFormat(status="completed" if status == "completed" else "error", message=msg)
    return {
        "structured_response": sr,
        "observations": final.get("observations", []),
        "response_format": rf.model_dump(),
        "metadata": {
            "runtime": "local",
            "model": settings.ollama_model,
            "tokens_local": 0,
            "tokens_remote": 0,
            "routing_label": f"Routed to Local Ollama — Model: {settings.ollama_model}",
        },
    }
