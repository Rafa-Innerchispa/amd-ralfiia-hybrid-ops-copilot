# RalfIIA Hybrid Ops Copilot — AMD ACT II Track 3

Multi-agent ops copilot (A2A) for AMD Developer Hackathon ACT II — Track 3 Unicorn + hybrid Track 1 router.

## Quick start

```bash
git clone https://github.com/Rafa-Innerchispa/amd-ralfiia-hybrid-ops-copilot.git
cd amd-ralfiia-hybrid-ops-copilot
cp .env.example .env   # edit locally — never commit secrets
./scripts/start_all.sh
```

**Console:** http://localhost:8220/console/

| Servicio | Puerto | Stack |
|----------|--------|-------|
| `root-gateway` | 8220 | FastAPI + Google ADK patterns (Session, RemoteAgentConnections, send_task) |
| `agent-smart-quoter` | 8221 | CrewAI + Hybrid Ollama/Fireworks |
| `agent-watchdog` | 8222 | LangGraph ReAct (Reason→Act→Observe) |
| `ui` (legacy) | 5120 | Nginx dashboard grayscale (la consola principal está en :8220/console/) |

---

## 🚀 Integración con Native.Builder (Promo Hackatón)

El proyecto está preparado para integrarse con **Native.Builder** utilizando los créditos de Fireworks AI:
1. Regístrate en [Native.Builder](https://native.ai/).
2. Ve a **Manage Plan** -> **Change Plan** e ingresa el código de promoción **`AMDXBUILDER`** para activar el plan gratuito de 1 mes (desbloquea *Bring Your Own Key*).
3. En la sección **Integrations** de Builder, agrega tu clave de API de **Fireworks AI** (`FIREWORKS_API_KEY`) para conectar tus créditos de inferencia del hackatón.
4. Diseña y prueba los agentes y flujos directamente en la consola interactiva.

---

## ♊ Integración de Modelos Gemma (Premios Especiales)

El router híbrido del proyecto tiene soporte completo para la familia de modelos **Gemma** de Google DeepMind:
* **Gemma 4 (Complejo/Razonamiento):** `accounts/fireworks/models/gemma-4-31b-it` para inferencia compleja.
* **Gemma 2 (Video/Subtítulos/Ligero):** `accounts/fireworks/models/gemma-2-9b-it` para generación y análisis rápido.

### Opciones de Despliegue de Gemma:
1. **Vía Fireworks API (Remoto):** Configura tu variable `FIREWORKS_API_KEY` en el archivo `.env` para enviar solicitudes al catálogo de Fireworks en GPUs AMD.
2. **Vía AMD Developer Cloud (Local-first / Standby):** Puedes desplegar un contenedor de **vLLM** con Gemma en un droplet de GPU en la nube de AMD y configurar la variable `AMD_INFERENCE_BASE_URL` en tu `.env` para derivar el tráfico localmente.

---

## Arranque y Pruebas

```bash
cd /home/rlopez/projects/amd-ralfiia-hybrid-ops-copilot
./scripts/start_all.sh
```

* **Consola local:** http://192.168.1.4:8220/console/
* **Consola pública (ngrok):** `https://sworn-profusely-alongside.ngrok-free.dev/amd-ops/`

## Handoff / continuar en otro IDE

**Historia completa y bitácora del hackathon AMD:** [`docs/HANDOFF_COMPLETO.md`](docs/HANDOFF_COMPLETO.md)
