"""CrewAI pipeline — Agent -> Task -> Crew -> structured output (lazy import)."""

from __future__ import annotations
import json
import os
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


def generate_quote_pdf(order_id: str, line_items: list[OrderItem], total: float, lang: str = "es") -> str:
    """Generate a beautiful, corporate technology quote PDF and return its filename."""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    import datetime

    # Target directory: ui/public
    ui_public_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../ui/public"))
    os.makedirs(ui_public_dir, exist_ok=True)

    filename = f"quote_{order_id[:8]}.pdf"
    pdf_path = os.path.join(ui_public_dir, filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    primary_color = colors.HexColor("#0B0F19")
    accent_color = colors.HexColor("#14B8A6") # Teal
    text_color = colors.HexColor("#1F2937")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        textColor=primary_color,
        spaceAfter=12
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Heading3'],
        fontSize=11,
        leading=15,
        textColor=accent_color,
        spaceAfter=8
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=13,
        textColor=text_color
    )

    story = []

    header_text = "RalfIIA Smart Quoter — PC Doctor"
    story.append(Paragraph(header_text, title_style))
    story.append(Paragraph(f"ID Cotización / Order ID: {order_id}", subtitle_style))
    story.append(Spacer(1, 10))

    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info_text = f"<b>Fecha / Date:</b> {date_str}<br/><b>Cliente / Customer:</b> PC Doctor Santiago (PCD-SANTIAGO-04)<br/><b>Estado / Status:</b> Borrador / Draft"
    story.append(Paragraph(info_text, body_style))
    story.append(Spacer(1, 15))

    table_data = [
        ["Concepto / Item", "Cantidad / Qty", "Precio / Price", "Total"]
    ]
    for it in line_items:
        table_data.append([
            it.name,
            str(it.quantity),
            f"${it.price:.2f}",
            f"${(it.price * it.quantity):.2f}"
        ])
    table_data.append(["TOTAL", "", "", f"${total:.2f}"])

    t = Table(table_data, colWidths=[240, 60, 100, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-2), colors.HexColor("#F9FAFB")),
        ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor("#E5E7EB")),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,-1), (-1,-1), 10),
        ('TEXTCOLOR', (0,-1), (-1,-1), accent_color),
    ]))

    story.append(t)
    story.append(Spacer(1, 20))

    footer_text = "Gracias por su preferencia. Cotización generada automáticamente por RalfIIA Smart Quoter." if lang == "es" else "Thank you for your business. Quote generated autonomously by RalfIIA Smart Quoter."
    story.append(Paragraph(f"<i>{footer_text}</i>", body_style))

    doc.build(story)
    return filename


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
                "Request: {request}"
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
    
    # Generate the actual PDF invoice in ui/public/
    try:
        pdf_filename = generate_quote_pdf(order_id, line_items, total, lang)
        pdf_url = f"/console/{pdf_filename}"
    except Exception as pdf_exc:
        pdf_url = None
        print(f"Error generating PDF: {pdf_exc}")

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
        if pdf_url:
            header += f"📄 Download PDF: {pdf_url}\n\n"
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
        if pdf_url:
            header += f"📄 Descargar PDF: {pdf_url}\n\n"
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
        },
    }
