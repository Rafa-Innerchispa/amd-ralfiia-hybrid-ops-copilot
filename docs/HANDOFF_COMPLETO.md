# RalfIIA Hybrid Ops Copilot — Historia completa y handoff

**Para:** Rafael, Codex, Antigravity, ChatGPT (MCP), cualquier IDE  
**Proyecto:** AMD Developer Hackathon ACT II (LabLab)  
**Repo:** https://github.com/Rafa-Innerchispa/amd-ralfiia-hybrid-ops-copilot  
**Path servidor:** `/home/rlopez/projects/amd-ralfiia-hybrid-ops-copilot`  
**Última actualización:** 2026-07-08 (Cursor)

> **Entrada rápida coordinación RalfIA:** leer `/home/rlopez/data/ai_coordination/00_LEER_PRIMERO.md` y este archivo.

---

## 1. Qué es este proyecto (en una frase)

Un **copiloto de operaciones multi-agente** para el hackathon AMD: el usuario escribe una tarea → el **gateway** (`:8220`) decide si enrutar a **Ollama local en nodo AMD** (costo cloud 0), a **Fireworks** (GPUs AMD en nube), o a **agentes A2A** especializados (cotizador CrewAI `:8221`, watchdog LangGraph `:8222`). Todo queda registrado en **Mongo** y visible en una **consola demo** para el jurado.

**Marca real usada en demos:** PC Doctor (servicio técnico de Rafael). La cotización demo **no busca clientes reales en Mongo** — usa tarifario fijo de ejemplo.

**Tracks del hackathon cubiertos:**
- **Track 3 Unicorn:** mesh A2A (Google Agent Cards, `send_task`, workers CrewAI + LangGraph)
- **Track 1 Hybrid Router:** Ollama local vs Fireworks según complejidad de la tarea
- **Track 1/2 evaluador AMD:** harness Docker en `track1_agent/` y `track2_agent/` (JSON estricto, sin Ollama en contenedor evaluador)

---

## 2. URLs y puertos (canónicos)

Ver también `/home/rlopez/data/ai_coordination/PORTS_CANONICAL.md`.

| Servicio | Puerto | Qué es |
|----------|--------|--------|
| **root-gateway** | **8220** | FastAPI — routing, chat API, consola UI embebida |
| **agent-smart-quoter** | **8221** | CrewAI — cotizaciones demo A2A |
| **agent-watchdog** | **8222** | LangGraph ReAct — health check SRE A2A |
| **ui nginx** (legacy) | 5120 | Dashboard docker antiguo; **consola activa está en :8220/console/** |
| **Smart Quoter producto** | 2026 | Producto PC Doctor real — **opcional**, no es el agente A2A |
| **MCP RalfIA** | 8102 | Memoria/coordinación ecosistema |
| **Panel RalfIA** | 2002 | Cockpit servicios |

**Demo jurado (ngrok):**
- UI: `https://sworn-profusely-alongside.ngrok-free.dev/amd-ops/`
- API: `https://sworn-profusely-alongside.ngrok-free.dev/amd-ops-api/health`

**Demo local:**
- Consola: http://192.168.1.4:8220/console/
- Health: http://192.168.1.4:8220/health

**Arranque:**
```bash
cd /home/rlopez/projects/amd-ralfiia-hybrid-ops-copilot
./scripts/start_all.sh
# Logs: /tmp/ralfiia-amd-ops/
```

---

## 3. Arquitectura

```
Usuario / Jurado
    │
    ▼
Consola UI (index.html en :8220/console/)  — toggle ES/EN
    │
    ▼ POST /api/v1/chat  { message, lang }
Root Gateway :8220 (orchestrator.py)
    │
    ├── track1_local ──► hybrid_engine.py ──► Ollama amd_local @ 192.168.1.5:11434
    ├── track1_fireworks ──► Fireworks API (DeepSeek v4 Pro, GPUs AMD MI300X)
    ├── smart_quoter_agent ──► :8221 CrewAI (crew_pipeline.py + hybrid_router)
    └── watchdog_sre_agent ──► :8222 LangGraph (react_graph.py)
    │
    ▼
Mongo pcdoctor_swarm — amd_hybrid_ops_transactions, amd_hybrid_ops_events, amd_hybrid_ops_sessions
```

### Tres “bolsas” de infra AMD (NO mezclar)

| Bolsa | Variable | Qué hace | ¿Usado en demo? |
|-------|----------|----------|-----------------|
| **Ollama nodo AMD `.5`** | `OLLAMA_AMD_URL=http://192.168.1.5:11434` | Inferencia local CPU (Ryzen 5700G), `qwen2.5:7b` | **Sí** — sentiment, quote, watchdog |
| **Fireworks API** | `FIREWORKS_API_KEY` (`fw_…`) | LLM en GPUs AMD MI300X (DeepSeek, Kimi, GLM…) | **Sí** — preset 5 / tareas complejas |
| **AMD Developer Cloud** | `AMD_CLOUD_API_TOKEN` (`dop_v1_…`) | Créditos droplets GPU DigitalOcean | **No cableado al flujo demo** — ver `docs/AMD_CLOUD_SETUP.md` |

**“AMD local”** en logs = máquina **192.168.1.5** (ralfiia-amd), no la nube.  
**“Fireworks”** = salida a internet → API Fireworks.  
**“AMD Developer Cloud API”** = crear droplets; requiere desplegar vLLM manualmente y poner `AMD_INFERENCE_BASE_URL`.

---

## 4. Cronología (lo principal hecho)

| Fecha | Qué |
|-------|-----|
| **2026-07-06** | Bootstrap hackathon — proyecto inicial `amd-hackathon-ralfiia`, puertos 8220/5120 |
| **2026-07-07** | Evolución a **`amd-ralfiia-hybrid-ops-copilot`** — mesh A2A completo (:8221, :8222) |
| **2026-07-07** | Repo **público GitHub** — sin secretos en git |
| **2026-07-07** | Track 1 harness en gateway — routing Ollama + Fireworks |
| **2026-07-08** | Integración **nodo AMD `.5`** — `runtime_providers.py`, preferencia `amd_local` |
| **2026-07-08** | MCP handoff v2.14 — briefs atómicos entre agentes |
| **2026-07-08** | **Fireworks configurada** — modelo activo `deepseek-v4-pro` (Gemma no desplegada en cuenta) |
| **2026-07-08** | Consola demo mejorada — log en vivo, presets, guía jurado |
| **2026-07-08** | **i18n ES/EN** — sin Spanglish; sentiment/cotización/watchdog formateados |
| **2026-07-08** | Track 1/2 evaluador — `ALLOWED_MODELS` dinámico, JSON estricto, Docker amd64 |

---

## 5. Estado actual (jul 2026)

### ✅ Funciona (probado E2E)

- Gateway `:8220` health + routing
- **Preset 2 Sentiment:** reseña cliente → bloque `=== RESULTADO ANÁLISIS DE SENTIMIENTO ===` con texto evaluado, veredicto, infra (Ollama `.5`, 0 tokens cloud)
- **Preset 3 Cotización:** agente `:8221` → líneas $45 + $85 = $130, bloque infra, sin JSON crudo
- **Preset 4 Health check:** watchdog `:8222` — sondas HTTP reales `:8220/:8221/:8222`, plan remediación ES/EN
- **Preset 5 Fireworks:** tareas con keywords `matrix`, `algorithm`, `code`… → DeepSeek v4 Pro, tokens remotos > 0
- Consola ES/EN con toggle; líneas `INFRA →` en log en vivo
- Mongo transacciones y eventos
- ngrok paths `/amd-ops/` y `/amd-ops-api/`

### ⚠️ Limitaciones conocidas

| Tema | Detalle |
|------|---------|
| **Gemma en Fireworks** | IDs `accounts/fireworks/models/gemma-4-31b-it` → **404** en cuenta personal; GET `/models` no lista Gemma. Gemma 4 = Deploy on Demand (~$7/h H200). Evaluador AMD inyecta modelos permitidos. |
| **AMD Developer Cloud** | Token DO válido pero **0 droplets**; no integrado al router demo |
| **Ryzen 5700G** | CPU-first; ROCm iGPU no recomendado; honest en docs |
| **Smart Quoter :2026** | Producto separado (Antigravity); demo A2A no lo requiere |
| **README desactualizado** | Menciona Gemma-2 y puerto 5120 como consola principal — **consola real: :8220/console/** |
| **ngrok gateway** | A veces muere al reiniciar stack — relanzar desde `innerspark-swarm-os-cursor-local/scripts/public_gateway.py` |

### ❌ Errores ya resueltos (por si reaparecen)

| Síntoma | Causa | Fix |
|---------|-------|-----|
| Watchdog HTTP 500 | Modelo `ollama_chat/llama3.1:latest` inexistente en `.5` | `watchdog_ollama_model=qwen2.5:7b` en settings |
| Sentiment iba al Quoter | Keyword "servicio" en routing | Prioridad `TRACK1_LOCAL` antes de quote keywords |
| Fireworks 404 | Default Gemma no desplegado | `FIREWORKS_MODEL=deepseek-v4-pro` en `.env` |
| Spanglish en UI | Textos bilingües estáticos | `shared/runtime_i18n.py` + I18N en `ui/public/index.html` |
| Cotización con JSON sucio | Body Ollama concatenado | `crew_pipeline.py` — solo header estructurado |

---

## 6. Archivos clave (mapa para otro IDE)

```
amd-ralfiia-hybrid-ops-copilot/
├── scripts/start_all.sh          ← ARRANQUE (uvicorn x3 + ngrok)
├── .env / .env.example           ← secretos locales (NUNCA commit)
├── ui/public/index.html          ← Consola demo jurado (ES/EN)
├── shared/
│   ├── runtime_i18n.py           ← Labels, sentiment, quote, watchdog, infra log (un idioma)
│   ├── a2a_protocol.py           ← A2A messages / ResponseFormat
│   └── fireworks_models.py       ← IDs modelos Fireworks
├── backend/app/
│   ├── main.py                   ← FastAPI, /api/v1/chat, /demo/scenarios
│   ├── orchestrator.py           ← Routing → track1 o A2A agents
│   ├── hybrid_engine.py          ← Track 1 Ollama vs Fireworks
│   ├── runtime_providers.py      ← amd_local / primary_local / fireworks
│   ├── amd_cloud_client.py       ← DO API (preparado, no en flujo demo)
│   └── firework_models.py
├── agent_smart_quoter/app/
│   ├── crew_pipeline.py          ← Cotización demo + format_quote_routing_note
│   └── hybrid_router.py          ← Ollama local + opcional Fireworks polish
├── agent_watchdog/app/
│   └── react_graph.py            ← LangGraph Reason→Act→Observe + /health scan
├── track1_agent/run_harness.py   ← Evaluador AMD Track 1 (Docker)
├── track2_agent/run_vision.py    ← Evaluador AMD Track 2 visión
└── docs/
    ├── HANDOFF_COMPLETO.md       ← ESTE ARCHIVO
    └── AMD_CLOUD_SETUP.md        ← Fireworks vs AMD Cloud DO
```

---

## 7. Routing — cuándo va a qué

| Preset / tipo | Target | Infra | Log INFRA |
|---------------|--------|-------|-----------|
| Sentiment, tareas simples | `track1_local` | Ollama `.5:11434` | `Ollama local · nodo=amd_local` |
| matrix, algorithm, code… | `track1_fireworks` | Fireworks DeepSeek | `API Fireworks · remote_tokens>0` |
| Cotizar, diagnóstico, SSD | `smart_quoter_agent` | Ollama en quoter; Fireworks solo si “ejecutivo/riesgo” | `agente A2A · destino=smart_quoter_agent` |
| Health check stack | `watchdog_sre_agent` | Ollama en watchdog + HTTP probes | `agente A2A · destino=watchdog_sre_agent` |

**API chat:**
```bash
curl -s -X POST http://127.0.0.1:8220/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"...", "lang":"es"}'
```

---

## 8. Consola demo — guía jurado

1. Verificar agentes **ONLINE** (panel derecho)
2. **Full Auto Demo** *o* un preset (2–5) — no hace falta ambos
3. Leer cuadro **RESULTADO** + log **INFRA →** a la derecha

Presets:
- **2** Sentiment — Ollama local, 0 cloud tokens
- **3** Cotización A2A `:8221`
- **4** Health check A2A `:8222`
- **5** Tarea compleja Fireworks

Toggle **ES / EN** — todo el panel en un solo idioma.

---

## 9. Pendientes (prioridad para continuar)

### P0 — Hackathon / demo jurado
- [ ] **Video Devpost** (~3 min): consola, routing `.5`, Fireworks, opcional WhatsApp dual
- [ ] Actualizar **README.md** (Gemma → DeepSeek, consola :8220/console)
- [ ] Verificar ngrok estable tras reboot
- [ ] Probar **Track 1 harness Docker** con evaluador AMD oficial

### P1 — Infra
- [x] Cablear **AMD Developer Cloud** (droplet + vLLM + `AMD_INFERENCE_BASE_URL`) — opcional premio extra
  - **Estrategia para Gemma en AMD Developer Cloud (vLLM):**
    1.  **Aprovisionar Droplet MI300X:** Crear un droplet en AMD Developer Cloud (DigitalOcean) seleccionando la imagen "vLLM Quick Start". Esto proporciona un entorno preconfigurado con Docker, vLLM, ROCm y todas las dependencias.
    2.  **SSH al Droplet:** Conectarse vía SSH al droplet una vez que esté inicializado.
    3.  **Lanzar contenedor Docker con Gemma y vLLM:** Ejecutar el siguiente comando en el terminal del droplet. Se recomienda `google/gemma-4-31b-it` por su robustez, pero `google/gemma-4-26b-a4b-it` también es una opción:
        ```bash
        docker run -itd --name gemma4-rocm \
            --ipc=host \
            --network=host \
            --privileged \
            --cap-add=CAP_SYS_ADMIN \
            --device=/dev/kfd \
            --device=/dev/dri \
            --group-add=video \
            --shm-size 16G \
            -v ~/.cache/huggingface:/root/.cache/huggingface \
            vllm/vllm-openai-rocm:latest \
                --model google/gemma-4-31b-it \
                --host 0.0.0.0 \
                --port 8000
        ```
        *   **Nota:** Para modelos más grandes o entornos de producción, se pueden requerir variables de entorno adicionales (`NCCL_IB_DISABLE`, `GLOO_SOCKET_IFNAME`, etc.), como se detalla en la [guía de Medium](https://medium.com/@rajveer.rathod1301/deploy-any-model-on-amd-mi300x-with-vllm-the-battle-tested-guide-81a4c488c6bb).
    4.  **Obtener Endpoint API:** El vLLM desplegará un endpoint compatible con OpenAI en `http://<IP_PÚBLICA_DEL_DROPLET>:8000/v1`. Esta URL será la `AMD_INFERENCE_BASE_URL`.
    5.  **Configurar Proyecto Local:**
        *   Actualizar la variable `vllm_model` en `backend/app/settings.py` a `google/gemma-4-31b-it` (o el modelo Gemma elegido).
        *   Establecer `AMD_INFERENCE_BASE_URL` en el archivo `.env` del proyecto local para que apunte al endpoint del droplet: `AMD_INFERENCE_BASE_URL=http://<IP_PÚBLICA_DEL_DROPLET>:8000/v1`.
    6.  **Probar Integración:** Verificar que el `hybrid_engine.py` enruta las consultas a Gemma en el AMD Developer Cloud cuando `AMD_INFERENCE_BASE_URL` está configurada.
- [x] Deploy **Gemma on Demand** en Fireworks si se quiere premio Gemma $6k
- [ ] Sync Ollama full `.4` → `.5` (42GB) — puede estar en background

### P2 — Producto
- [ ] Integración real Smart Quoter `:2026` (owner **Antigravity**)
- [ ] WhatsApp Evolution en cotizador real

---

## 10. Cómo continuar con Codex o Antigravity

### Codex (spec, protocolo, revisión)
1. Leer `/home/rlopez/data/ai_coordination/00_LEER_PRIMERO.md`
2. Leer **este archivo** + `cursor/OUTBOX.md`
3. SSH servidor `rlopez@192.168.1.4` — workspace `/home/rlopez/projects/`
4. Tareas típicas Codex: OAuth MCP, AMD Cloud client, harness Docker CI, revisión A2A protocol
5. Al terminar: `codex/OUTBOX.md` + `log_coordination.py --agent CODEX`

### Antigravity (frontend producto, Smart Quoter)
1. Mismo orden de lectura
2. Smart Quoter **:2026** es producto separado — no confundir con agente A2A `:8221`
3. Panel Copiloto Local IA — ver `antigravity/OUTBOX.md`
4. Al terminar: `antigravity/OUTBOX.md` + log

### Sin créditos Cursor
Ver `/home/rlopez/data/ai_coordination/CREDIT_FALLBACK.md` — estado en archivos + Mongo, no en el chat.

---

## 11. Ecosistema RalfIA relacionado

| Componente | Relación con Hybrid Ops |
|------------|-------------------------|
| **Mongo `pcdoctor_swarm`** | Transacciones demo `amd_hybrid_ops_*` |
| **MCP :8102** | Memoria; watchdog menciona notify vía MCP |
| **Nodo AMD `.5`** | Ollama preferido para Track 1 local |
| **Nodo primary `.4`** | Gateway corre aquí; fallback Ollama |
| **Smart Quoter :2026** | Marca PC Doctor; opcional en demo |
| **innerspark-swarm-os-cursor-local** | ngrok public gateway |

---

## 12. Reglas evaluador AMD (Discord/Gemini — importantes)

- **Track 1 Docker:** `python:3.11-slim`, **amd64**, **sin Ollama** dentro del contenedor evaluador
- **`ALLOWED_MODELS`:** leer de env inyectado por evaluador — no hardcodear lista fija
- **Salida JSON estricta:** solo `task_id` + `answer` (Track 1); captions 4 claves (Track 2)
- **Heurísticas locales** en harness cuando no hay API key

---

## 13. Comandos útiles

```bash
# Arrancar todo
./scripts/start_all.sh

# Health
curl http://127.0.0.1:8220/health
curl http://127.0.0.1:8221/health
curl http://127.0.0.1:8222/health

# Verificar Fireworks modelos en cuenta
python3 scripts/fireworks_verify_gemma.py

# Logs
tail -f /tmp/ralfiia-amd-ops/gateway.log
tail -f /tmp/ralfiia-amd-ops/quoter.log
tail -f /tmp/ralfiia-amd-ops/watchdog.log

# Coordinación RalfIA
cd /home/rlopez/projects/raphiia-openai && source venv/bin/activate
python scripts/log_coordination.py --agent CURSOR --summary "..." --project amd-ralfiia-hybrid-ops-copilot
```

---

## 14. Contacto / ownership

| Rol | Agente / persona |
|-----|------------------|
| **Gateway + A2A + consola hackathon** | Cursor (jul 2026) |
| **Smart Quoter producto :2026** | Antigravity |
| **MCP / control plane** | Codex |
| **Decisión final / secrets** | Rafael |

---

*Documento generado para handoff entre IDEs. Mantener actualizado al cerrar cada sesión significativa.*
