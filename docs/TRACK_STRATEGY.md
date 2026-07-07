# Estrategia de tracks — qué priorizar para GANAR

## Mi recomendación honesta

**No necesitas ganar los 3 tracks a la vez.** Lo inteligente es **1 submission fuerte + bonus donde ya tienes código**.

| Prioridad | Track | Por qué | Probabilidad |
|-----------|-------|---------|--------------|
| **🥇 P0** | **Track 3 Unicorn** | Producto real RalfIIA, A2A mesh, Smart Quoter, demo ngrok | **Alta** |
| **🥈 P1** | **Track 1 Hybrid Router** | Ya implementado, script harness listo, Ollama 0-token | **Media-alta** |
| **🥉 P2** | **Track 2 Video** | Requiere clips oficiales AMD + ffmpeg + Fireworks + llava | **Media-baja** |
| **Bonus** | **Premio Gemma ($6k)** | Usar Gemma vía Fireworks en Track 1 o 2 | Transversal |

---

## Por qué NO apostar todo a los 3

1. **Track 2** usa videos fijos del hackathon — hasta que AMD publique los clips, estás adivinando.
2. **Track 1** se puntúa en entorno estandarizado — tu script `run_harness.py` sirve; el producto Track 3 es aparte.
3. **Track 3** premia creatividad + producto — ahí está tu ventaja (PC Doctor, ops copilot, ecosistema vivo).
4. **Fireworks sin API key** — Track 1 complejo y Track 2 quedan en fallback hasta que AMD mande créditos.

---

## Plan ganador (14 días típicos hackathon)

### Semana 1 — Cerrar Track 3 (principal)
- Video Devpost 2-3 min: ngrok `/amd-ops-api/health` + routing en vivo + Smart Quoter :2026
- Narrativa: *startup ops copilot sobre infra AMD + Ollama soberano*
- Mencionar Gemma/Fireworks cuando tengas key

### Paralelo — Track 1 (script)
```bash
cd /home/rlopez/projects/amd-ralfiia-hybrid-ops-copilot
HARNESS_INPUT_PATH=./input/tasks.json HARNESS_OUTPUT_PATH=./output/results.json \
  python3 track1_agent/run_harness.py
```

### Si AMD suelta videos — Track 2
```bash
HARNESS_INPUT_PATH=./input/track2_tasks.json \
  python3 track2_agent/run_vision.py
```

---

## Qué decir en Devpost

- **Track principal:** Track 3 — RalfIIA Hybrid Ops Copilot
- **También compatible:** Track 1 harness (`track1_agent/run_harness.py`)
- **Opcional:** Track 2 si entregan clips
- **AMD stack:** Ollama local + Fireworks Gemma + (futuro) Developer Cloud GPU

---

## Una frase

**Gana Track 3 con el producto; usa Track 1 como prueba técnica del router; Track 2 solo si tienes los videos oficiales y Fireworks activo.**
