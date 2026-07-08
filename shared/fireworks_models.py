"""
Fireworks model IDs — nomenclatura oficial AMD/LabLab.

En Fireworks los IDs deben llevar prefijo accounts/... La API GET /models solo
lista modelos *desplegados* en la cuenta; Gemma aparece en el catálogo web pero
hay que hacer Deploy on Demand antes de poder invocarlo.
"""

from __future__ import annotations

import os

# Catálogo Gemma (hackathon AMD) — rutas completas obligatorias
GEMMA_MODEL_IDS: dict[str, str] = {
    "gemma-4-31b-it": "accounts/fireworks/models/gemma-4-31b-it",
    "gemma-4-26b-a4b-it": "accounts/fireworks/models/gemma-4-26b-a4b-it",
    "gemma-3-27b-instruct": "accounts/fireworks/models/gemma-3-27b-instruct",
    "gemma-2-9b-it": "accounts/fireworks/models/gemma-2-9b-it",
}

DEFAULT_GEMMA_COMPLEX = GEMMA_MODEL_IDS["gemma-4-31b-it"]
DEFAULT_GEMMA_CAPTION = GEMMA_MODEL_IDS["gemma-2-9b-it"]


def normalize_model_id(name: str) -> str:
    """Convierte nombre corto → ruta accounts/fireworks/models/..."""
    cleaned = (name or "").strip()
    if not cleaned:
        return ""
    if cleaned.startswith("accounts/"):
        return cleaned
    if cleaned in GEMMA_MODEL_IDS:
        return GEMMA_MODEL_IDS[cleaned]
    return f"accounts/fireworks/models/{cleaned}"


def parse_allowed_models(raw: str | None = None) -> list[str]:
    source = raw if raw is not None else os.environ.get("ALLOWED_MODELS", "")
    return [normalize_model_id(m) for m in source.split(",") if m.strip()]


def pick_target_model(
    *,
    role: str = "complex",
    allowed_raw: str | None = None,
) -> str:
    """
    Selección dinámica de modelo:
    1. ALLOWED_MODELS (evaluador AMD) → primer modelo
    2. FIREWORKS_COMPLEX_MODEL / FIREWORKS_MODEL / FIREWORKS_CAPTION_MODEL
    3. Default Gemma según rol
    """
    allowed = parse_allowed_models(allowed_raw)
    if allowed:
        return allowed[0]

    env_keys = (
        ("FIREWORKS_COMPLEX_MODEL", "FIREWORKS_MODEL")
        if role == "complex"
        else ("FIREWORKS_CAPTION_MODEL", "FIREWORKS_MODEL", "FIREWORKS_COMPLEX_MODEL")
    )
    for key in env_keys:
        value = os.environ.get(key, "").strip()
        if value:
            return normalize_model_id(value)

    if role == "caption":
        return DEFAULT_GEMMA_CAPTION
    return DEFAULT_GEMMA_COMPLEX
