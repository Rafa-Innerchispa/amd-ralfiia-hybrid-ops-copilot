#!/usr/bin/env python3
"""Verifica modelos Fireworks desplegados y acceso a Gemma (sin imprimir secretos)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.fireworks_models import DEFAULT_GEMMA_COMPLEX, GEMMA_MODEL_IDS, normalize_model_id


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    load_dotenv()
    key = os.environ.get("FIREWORKS_API_KEY", "")
    base = os.environ.get("FIREWORKS_API_BASE", "https://api.fireworks.ai/inference/v1").rstrip("/")

    if not key:
        print("ERROR: FIREWORKS_API_KEY no configurada en .env")
        return 1

    headers = {"Authorization": f"Bearer {key}"}

    print("=== Modelos desplegados (GET /models) ===")
    r = httpx.get(f"{base}/models", headers=headers, timeout=30)
    if r.status_code != 200:
        print(f"FAIL list models: {r.status_code} {r.text[:200]}")
        return 1

    deployed = [m.get("id", "") for m in r.json().get("data", [])]
    for mid in deployed:
        print(f"  ✓ {mid}")

    gemma_deployed = [m for m in deployed if "gemma" in m.lower()]
    print(f"\nGemma desplegados: {len(gemma_deployed)}")

    print("\n=== Catálogo Gemma (IDs oficiales) ===")
    for short, full in GEMMA_MODEL_IDS.items():
        status = "DEPLOYED" if full in deployed else "NOT DEPLOYED"
        print(f"  {short}: {full} [{status}]")

    print("\n=== Smoke test chat/completions ===")
    targets = list(GEMMA_MODEL_IDS.values()) + deployed[:2]
    seen: set[str] = set()
    for model_id in targets:
        if model_id in seen:
            continue
        seen.add(model_id)
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
            "max_tokens": 8,
            "temperature": 0,
        }
        try:
            resp = httpx.post(
                f"{base}/chat/completions",
                json=payload,
                headers=headers,
                timeout=90,
            )
            if resp.status_code == 200:
                text = resp.json()["choices"][0]["message"]["content"][:60]
                print(f"  OK  {model_id} → {text!r}")
            else:
                err = resp.json().get("error", {}).get("message", resp.text[:100])
                print(f"  FAIL {model_id} → {resp.status_code} {err}")
        except Exception as exc:
            print(f"  ERR {model_id} → {exc}")

    if not gemma_deployed:
        print(
            "\n⚠ Gemma NO está desplegado en tu cuenta."
            "\n  En app.fireworks.ai → Model Library → Gemma → 'Deploy on Demand'."
            f"\n  ID objetivo recomendado: {DEFAULT_GEMMA_COMPLEX}"
            "\n  En el evaluador AMD, ALLOWED_MODELS ya vendrá inyectado — no depende de tu deploy local."
        )
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
