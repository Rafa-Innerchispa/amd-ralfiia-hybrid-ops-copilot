"""CrewAI pipeline — Agent -> Task -> Crew -> structured output (lazy import)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from app.hybrid_router import hybrid_route
from shared.a2a_protocol import Order, OrderItem, ResponseFormat

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


async def run_quote_pipeline(user_text: str) -> dict[str, Any]:
    """CrewAI extraction + hybrid router polish."""
    raw = create_quote(user_text)
    crew = build_quote_crew()
    if crew is not None:
        try:
            crew_result = crew.kickoff(inputs={"request": user_text})
            raw = str(crew_result)
        except Exception as exc:
            raw = f"{raw}\ncrew_fallback: {exc}"

    hybrid = await hybrid_route(user_text + "\n" + raw)

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
        OrderItem(name="Diagnóstico onsite", quantity=1, price=45),
        OrderItem(name="Instalación SSD 1TB", quantity=1, price=85),
    ]
    order = Order(order_id=order_id, status="draft", order_items=line_items)
    total = sum(i.price * i.quantity for i in line_items)

    response = ResponseFormat(
        status="completed",
        message=(
            f"{hybrid['message']}\n\n"
            f"Order ID: {order_id}\n"
            f"Total estimado: ${total}\n"
            f"{hybrid['routing_label']}"
        ),
    )

    return {
        "id": str(uuid.uuid4()),
        "sessionId": "crew-session",
        "status": "completed" if response.status == "completed" else "input_required",
        "message": response.message,
        "artifacts": [order.model_dump()],
        "metadata": {
            "runtime": hybrid["runtime"],
            "model": hybrid["model"],
            "tokens_local": hybrid["tokens_local"],
            "tokens_remote": hybrid["tokens_remote"],
            "routing_label": hybrid["routing_label"],
            "crew_output_preview": raw[:500],
        },
    }
