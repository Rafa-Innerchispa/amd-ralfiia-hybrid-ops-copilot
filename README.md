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
| `ui` | 5120 | Nginx dashboard grayscale |

## Arranque (sin Fireworks)

```bash
cd /home/rlopez/projects/amd-ralfiia-hybrid-ops-copilot
./scripts/start_all.sh
```

- **Console local:** http://192.168.1.4:8220/console/
- **Console jurado:** https://sworn-profusely-alongside.ngrok-free.dev/amd-ops/
- **API jurado:** https://sworn-profusely-alongside.ngrok-free.dev/amd-ops-api/health

La consola incluye demo interactiva, botones Track 1, chat A2A y métricas en vivo.

## Criterios Track 3 (Unicorn)

- Creatividad: ops copilot real sobre ecosistema RalfIA (PC Doctor, MCP, Mongo)
- AMD platforms: Fireworks Gemma-2 on AMD + Ollama local + Developer Cloud ready
- Completitud: 4 containers, A2A agent cards, live UI, Mongo seed
- Product/market: Smart Quoter + SRE Watchdog como workers interoperables

## Premio Gemma ($6k)

Usar Gemma-2 vía Fireworks en polish ejecutivo del Smart Quoter.
