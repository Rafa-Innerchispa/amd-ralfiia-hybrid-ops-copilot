"""Runtime labels — single language (es | en), no Spanglish."""

from __future__ import annotations

import re

Lang = str  # "es" | "en"


def normalize_lang(lang: str | None) -> Lang:
    return "en" if (lang or "").lower().startswith("en") else "es"


def extract_evaluated_text(prompt: str) -> str:
    m = re.search(r"[«\"']([^»\"']{8,})[»\"']", prompt)
    if m:
        return m.group(1).strip()
    for sep in (":", "—", "-"):
        if sep in prompt:
            tail = prompt.split(sep, 1)[-1].strip()
            if len(tail) > 8:
                return tail.strip('"').strip("«").strip("»").strip()
    return prompt.strip()


def parse_sentiment_verdict(raw: str) -> str:
    lowered = raw.lower()
    if any(w in lowered for w in ("positive", "positivo", "positiva")):
        return "positive"
    if any(w in lowered for w in ("negative", "negativo", "negativa")):
        return "negative"
    if any(w in lowered for w in ("neutral", "neutro", "neutra", "mixed", "mixto")):
        return "neutral"
    return raw.split("\n")[0][:120]


def format_sentiment_result(
    prompt: str,
    model_answer: str,
    *,
    provider_id: str,
    ollama_url: str,
    model: str,
    lang: Lang,
) -> str:
    evaluated = extract_evaluated_text(prompt)
    verdict = parse_sentiment_verdict(model_answer)
    if lang == "en":
        labels = {"positive": "POSITIVE", "negative": "NEGATIVE", "neutral": "NEUTRAL"}
        verdict_disp = labels.get(verdict, verdict.upper())
        return (
            "=== SENTIMENT ANALYSIS RESULT ===\n\n"
            f"Evaluated text:\n  \"{evaluated}\"\n\n"
            f"Verdict: {verdict_disp}\n"
            f"Task: classify customer feedback tone (NLP Track 1)\n\n"
            "Infrastructure:\n"
            f"  • Engine: local Ollama ({model})\n"
            f"  • Node: {provider_id} @ {ollama_url}\n"
            "  • Fireworks / AMD cloud tokens: 0\n"
            "  • AMD Developer Cloud API: not used for this task"
        )
    labels = {"positive": "POSITIVO", "negative": "NEGATIVO", "neutral": "NEUTRAL"}
    verdict_disp = labels.get(verdict, verdict.upper())
    return (
        "=== RESULTADO ANÁLISIS DE SENTIMIENTO ===\n\n"
        f"Texto evaluado:\n  «{evaluated}»\n\n"
        f"Veredicto: {verdict_disp}\n"
        f"Tarea: clasificar el tono del feedback del cliente (NLP Track 1)\n\n"
        "Infraestructura:\n"
        f"  • Motor: Ollama local ({model})\n"
        f"  • Nodo: {provider_id} @ {ollama_url}\n"
        "  • Tokens Fireworks / nube AMD: 0\n"
        "  • API AMD Developer Cloud: no se usa en esta tarea"
    )


def format_fireworks_result(answer: str, model_path: str, lang: Lang) -> str:
    if lang == "en":
        return (
            "=== COMPLEX TASK RESULT (FIREWORKS) ===\n\n"
            f"{answer}\n\n"
            "Infrastructure:\n"
            f"  • Engine: Fireworks AI (AMD MI300X GPUs)\n"
            f"  • Model: {model_path}\n"
            "  • Local Ollama: not used\n"
            "  • AMD Developer Cloud API: not used (optional for GPU droplets)"
        )
    return (
        "=== RESULTADO TAREA COMPLEJA (FIREWORKS) ===\n\n"
        f"{answer}\n\n"
        "Infraestructura:\n"
        f"  • Motor: Fireworks AI (GPUs AMD MI300X)\n"
        f"  • Modelo: {model_path}\n"
        "  • Ollama local: no se usa\n"
        "  • API AMD Developer Cloud: no se usa (opcional para droplets GPU)"
    )


def format_amd_cloud_result(answer: str, model_path: str, lang: Lang) -> str:
    if lang == "en":
        return (
            "=== COMPLEX TASK RESULT (AMD DEVELOPER CLOUD) ===\n\n"
            f"{answer}\n\n"
            "Infrastructure:\n"
            f"  • Engine: AMD Developer Cloud (vLLM / GPU droplet)\n"
            f"  • Model: {model_path}\n"
            "  • Local Ollama: not used\n"
            "  • Fireworks Cloud: not used"
        )
    return (
        "=== RESULTADO TAREA COMPLEJA (AMD DEVELOPER CLOUD) ===\n\n"
        f"{answer}\n\n"
        "Infraestructura:\n"
        f"  • Motor: AMD Developer Cloud (vLLM / droplet GPU)\n"
        f"  • Modelo: {model_path}\n"
        "  • Ollama local: no se usa\n"
        "  • Inferencia Fireworks: no se usa"
    )


def format_routing_label(
    *,
    runtime: str,
    provider_id: str,
    model: str,
    ollama_url: str | None,
    lang: Lang,
) -> str:
    if runtime == "amd_cloud" or provider_id == "amd_cloud":
        if lang == "en":
            return f"AMD Cloud vLLM (AMD GPU) — {model}"
        return f"AMD Cloud vLLM (GPUs AMD) — {model}"
    if runtime == "fireworks_cloud" or provider_id == "fireworks_cloud":
        if lang == "en":
            return f"Fireworks cloud (AMD GPU) — {model}"
        return f"Fireworks en nube (GPUs AMD) — {model}"
    url = ollama_url or "?"
    if lang == "en":
        return f"Local Ollama — {provider_id} @ {url}"
    return f"Ollama local — {provider_id} @ {url}"


def format_fireworks_unavailable(error: str, lang: Lang) -> str:
    if lang == "en":
        return f"\n\n[Fireworks unavailable: {error}]"
    return f"\n\n[Fireworks no disponible: {error}]"


def infra_log_line(
    *,
    target: str,
    provider_id: str | None,
    ollama_url: str | None,
    model: str | None,
    tokens_remote: int,
    lang: Lang,
) -> str:
    if target == "track1_fireworks" or provider_id == "fireworks_cloud" or tokens_remote > 0:
        if lang == "en":
            return f"INFRA → Fireworks API (AMD GPU cloud) · model={model or '?'} · remote_tokens={tokens_remote}"
        return f"INFRA → API Fireworks (GPUs AMD en nube) · modelo={model or '?'} · tokens_remotos={tokens_remote}"
    if target in ("track1_local", "smart_quoter_agent", "watchdog_sre_agent") or provider_id in (
        "amd_local",
        "primary_local",
        "local_default",
    ):
        node = provider_id or "local"
        url = ollama_url or "127.0.0.1:11434"
        if lang == "en":
            return f"INFRA → local Ollama · node={node} · {url} · model={model or '?'} · cloud_tokens=0"
        return f"INFRA → Ollama local · nodo={node} · {url} · modelo={model or '?'} · tokens_nube=0"
    if lang == "en":
        return f"INFRA → A2A agent · target={target}"
    return f"INFRA → agente A2A · destino={target}"


def format_quote_routing_note(
    *,
    provider_id: str,
    ollama_url: str,
    model: str,
    tokens_remote: int,
    fireworks_model: str | None,
    lang: Lang,
) -> str:
    if tokens_remote > 0 and lang == "en":
        return (
            "Infrastructure:\n"
            f"  • Extraction: local Ollama ({model}) @ {ollama_url}\n"
            f"  • Executive polish: Fireworks ({fireworks_model or '?'}) — AMD GPU cloud\n"
            "  • AMD Developer Cloud API: not used"
        )
    if tokens_remote > 0:
        return (
            "Infraestructura:\n"
            f"  • Extracción: Ollama local ({model}) @ {ollama_url}\n"
            f"  • Pulido ejecutivo: Fireworks ({fireworks_model or '?'}) — GPUs AMD en nube\n"
            "  • API AMD Developer Cloud: no se usa"
        )
    if lang == "en":
        return (
            "Infrastructure:\n"
            f"  • Quote engine: local Ollama ({model}) @ {ollama_url}\n"
            f"  • Node role: {provider_id} (AMD Ryzen .5 when available)\n"
            "  • Fireworks: not used for this demo quote\n"
            "  • AMD Developer Cloud API: not used"
        )
    return (
        "Infraestructura:\n"
        f"  • Motor cotización: Ollama local ({model}) @ {ollama_url}\n"
        f"  • Rol del nodo: {provider_id} (AMD Ryzen .5 cuando está disponible)\n"
        "  • Fireworks: no se usa en esta cotización demo\n"
        "  • API AMD Developer Cloud: no se usa"
    )


def format_watchdog_report(sr: dict, lang: Lang) -> str:
    status = sr.get("status", "unknown")
    if lang == "en":
        lines = ["=== SRE HEALTH CHECK RESULT ===", ""]
        if status == "healthy":
            lines.append("Status: ALL SERVICES HEALTHY (live /health probes)")
        else:
            lines.append("Status: ACTION REQUIRED")
        lines.append(f"Incident ID: {sr.get('incident_id', 'n/a')}")
        lines.append(f"Severity: {sr.get('severity', 'unknown')}")
        lines.append(f"Cause: {sr.get('root_cause_hypothesis', 'n/a')}")
        if sr.get("post_scan_summary"):
            lines.append("")
            lines.append("Services checked (HTTP GET /health):")
            for row in sr["post_scan_summary"]:
                lines.append(f"  • {row}")
        lines.append("")
        lines.append("Next steps:")
        for step in sr.get("remediation_steps", []):
            lines.append(f"  → {step}")
        lines.append("")
        lines.append(
            "Infrastructure: local Ollama on watchdog agent · Fireworks not used · "
            "AMD Developer Cloud API not used"
        )
        return "\n".join(lines)

    lines = ["=== RESULTADO HEALTH CHECK SRE ===", ""]
    if status == "healthy":
        lines.append("Estado: TODOS LOS SERVICIOS OK (sondas /health en vivo)")
    else:
        lines.append("Estado: ACCIÓN REQUERIDA")
    lines.append(f"ID incidente: {sr.get('incident_id', 'n/a')}")
    lines.append(f"Severidad: {sr.get('severity', 'unknown')}")
    lines.append(f"Causa: {sr.get('root_cause_hypothesis', 'n/a')}")
    if sr.get("post_scan_summary"):
        lines.append("")
        lines.append("Servicios comprobados (HTTP GET /health):")
        for row in sr["post_scan_summary"]:
            lines.append(f"  • {row}")
    lines.append("")
    lines.append("Pasos siguientes:")
    for step in sr.get("remediation_steps", []):
        lines.append(f"  → {step}")
    lines.append("")
    lines.append(
        "Infraestructura: Ollama local en agente watchdog · Fireworks no se usa · "
        "API AMD Developer Cloud no se usa"
    )
    return "\n".join(lines)


def is_sentiment_prompt(prompt: str) -> bool:
    return bool(
        re.search(r"\b(sentiment|sentimiento|analiza el sentimiento|classify)\b", prompt, re.I)
    )
