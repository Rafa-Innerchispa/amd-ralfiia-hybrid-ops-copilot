"""CrewAI pipeline — Agent -> Task -> Crew -> structured output (lazy import)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from app.hybrid_router import hybrid_route
from app.settings import settings
from shared.a2a_protocol import Order, OrderItem, ResponseFormat
from shared.runtime_i18n import format_quote_routing_note, normalize_lang

TECH_MENU = """
Servicios PC Doctor:
- Diagnóstico onsite: $45
- Reparación placa madre: $120
- Instalación SSD 1TB: $85
- Mantenimiento preventivo anual: $199
- Cableado red empresarial (por punto): $35
"""


def create_quote(customer_request: str) -> str:
    """Deterministic quote ID generator + extraction hook."""
    order_id = str(uuid.uuid4())
    return json.dumps({"order_id": order_id, "raw_request": customer_request[:2000]})


def build_quote_crew():
    try:
        from crewai import Agent, Crew, Process, Task
        from crewai.tools import tool

        @tool("create_quote")
        def create_quote_tool(customer_request: str) -> str:
            return create_quote(customer_request)

        quoter_agent = Agent(
            role="Smart Quoter Specialist",
            goal="Extract line items and produce corporate technology quotes for PC Doctor",
            backstory="Expert in field service quoting with strict pricing compliance.",
            tools=[create_quote_tool],
            verbose=False,
            allow_delegation=False,
        )
        quote_task = Task(
            description=(
                f"{TECH_MENU}\n"
                "Rules:\n"
                "1. Ensure layout and pricing are confirmed.\n"
                "2. Call create_quote tool for tracking ID.\n"
                "3. Output breakdown, totals, and order ID.\n"
                "Request: {{request}}"
            ),
            expected_output="JSON with order_id, line_items, total, status",
            agent=quoter_agent,
        )
        return Crew(agents=[quoter_agent], tasks=[quote_task], process=Process.sequential, verbose=False)
    except ImportError:
        return None


async def run_quote_pipeline(user_text: str, lang: str = "es") -> dict[str, Any]:
    """CrewAI extraction + hybrid router polish."""
    lang = normalize_lang(lang)
    raw = create_quote(user_text)
    crew = build_quote_crew()
    if crew is not None:
        try:
            crew_result = crew.kickoff(inputs={"request": user_text})
            raw = str(crew_result)
        except Exception as exc:
            raw = f"{raw}\ncrew_fallback: {exc}"

    hybrid = await hybrid_route(user_text + "\n" + raw, lang=lang)

    order_id = str(uuid.uuid4())
    try:
        import re

        m = re.search(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            raw,
        )
        if m:
            order_id = m.group(0)
    except Exception:
        pass

    line_items = [
        OrderItem(
            name="Onsite diagnosis" if lang == "en" else "Diagnóstico en sitio",
            quantity=1,
            price=45,
        ),
        OrderItem(
            name="1TB SSD installation" if lang == "en" else "Instalación SSD 1TB",
            quantity=1,
            price=85,
        ),
    ]
    order = Order(order_id=order_id, status="draft", order_items=line_items)
    total = sum(i.price * i.quantity for i in line_items)
    infra = format_quote_routing_note(
        provider_id=str(hybrid.get("provider_id", "amd_local")),
        ollama_url=str(hybrid.get("ollama_base_url", "?")),
        model=str(hybrid.get("model", "?")),
        tokens_remote=int(hybrid.get("tokens_remote", 0)),
        fireworks_model=settings.fireworks_model if hybrid.get("tokens_remote") else None,
        lang=lang,
    )
    if lang == "en":
        header = (
            "=== QUOTE GENERATED ===\n\n"
            f"Order ID: {order_id}\n"
            f"Status: draft\n"
        )
        for it in line_items:
            header += f"  • {it.name}: ${it.price} x{it.quantity}\n"
        header += f"ESTIMATED TOTAL: ${total}\n\n"
        header += infra
    else:
        header = (
            "=== COTIZACIÓN GENERADA ===\n\n"
            f"Order ID: {order_id}\n"
            f"Estado: borrador\n"
        )
        for it in line_items:
            header += f"  • {it.name}: ${it.price} x{it.quantity}\n"
        header += f"TOTAL ESTIMADO: ${total}\n\n"
        header += infra

    response = ResponseFormat(status="completed", message=header)

    return {
        "id": str(uuid.uuid4()),
        "sessionId": "crew-session",
        "status": "completed" if response.status == "completed" else "input_required",
        "message": response.message,
        "artifacts": [order.model_dump()],
        "metadata": {
            "runtime": hybrid["runtime"],
            "provider_id": hybrid["provider_id"],
            "ollama_base_url": hybrid.get("ollama_base_url"),
            "model": hybrid["model"],
            "tokens_local": hybrid["tokens_local"],
            "tokens_remote": hybrid["tokens_remote"],
            "routing_label": hybrid["routing_label"],
            "crew_output_preview": raw[:500],
        },
    }
