# Estrategia para ganar Track 3 — AMD ACT II

**Hackathon:** https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii

## Qué evalúan los jueces (Track 3 Unicorn)

| Criterio | Cómo lo cubrimos |
|----------|------------------|
| **Creatividad / originalidad** | No es un chatbot: mesh A2A con 3 micro-servicios interoperables (Google protocol) |
| **Uso plataformas AMD** | Fireworks Gemma-2 (MI300X), créditos AMD Developer Cloud, Ollama local 0-token |
| **Completitud** | Docker 4 servicios, UI live, Mongo seed, Agent Cards, remediation SRE |
| **Potencial producto/mercado** | PC Doctor / InnerSpark: cotización + SRE sobre infra real RalfIA |

## Bonus Gemma ($6k pool)

- Gemma-2 vía Fireworks en polish ejecutivo del Smart Quoter
- Mencionar en video demo: "Best AMD-Hosted Gemma Project"

## Diferenciadores vs otros equipos

1. **Ecosistema real** — MCP :8102, Mongo `pcdoctor_swarm`, Smart Quoter :2026 ya operativo
2. **A2A estándar abierto** — no vendor lock-in; Agent Cards descubribles
3. **Hybrid routing demostrable** — dashboard muestra decisión local vs AMD cloud en tiempo real
4. **SRE agent con LangGraph** — ReAct loop auditable (Reason→Act→Observe)

## Entregables pendientes (Rafael)

- [ ] `FIREWORKS_API_KEY` en `.env` (créditos hackathon)
- [ ] Video 2–3 min mostrando UI :5120 + delegación A2A
- [ ] Opcional: AMD Developer Cloud GPU para batch/embeddings
- [ ] Devpost: arquitectura diagram + link repo containerizado

## Preguntas abiertas para afinar

1. ¿Integramos demo en vivo con Smart Quoter :2026 (audio→cotización)?
2. ¿Exponemos vía ngrok `:5188` para jurado remoto?
3. ¿Track 1 dual-submit? El router híbrido también califica por token efficiency
