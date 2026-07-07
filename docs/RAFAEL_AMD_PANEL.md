# Guía Rafael — Panel AMD + Fireworks API + créditos hackathon

**Hackathon:** [AMD Developer Hackathon ACT II](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii)

---

## 1. Registro obligatorio (si no lo hiciste)

1. Abre **lablab.ai** → evento **AMD Developer Hackathon ACT II**
2. Click **Join Hackathon** / **Register**
3. Espera email de **aprobación** (Enrollment approved)
4. Si te registraste **después del 2 julio 2026**: los créditos hackathon se asignan **desde el 7 julio** (hoy estamos en esa ventana)

---

## 2. AMD AI Developer Program (créditos separados)

Dos bolsas de créditos **independientes**:

| Tipo | Monto | Cuándo |
|------|-------|--------|
| **Hackathon credits** | $50 Fireworks + GPU cloud AMD | Al aprobar enrollment (post 7-jul si late signup) |
| **New member credits** | $100 AMD Developer Cloud + $50 Fireworks | Signup nuevo programa AMD — **2-3 días manual**

### Pasos en panel AMD

1. **https://www.amd.com/en/developer/aidev-program.html** → Join / Sign in
2. Completa perfil developer (nombre, país, uso de IA)
3. En el **dashboard del hackathon en lablab.ai**:
   - Busca sección **Credits** / **Resources** / **Getting Started**
   - Debe aparecer link a **Fireworks AI** y **AMD Developer Cloud**
4. **Fireworks AI:**
   - https://fireworks.ai/ → Sign up (mismo email si piden)
   - Dashboard → **API Keys** → Create key
   - Billing → verifica créditos hackathon ($50) o promoción AMD
5. **AMD Developer Cloud:**
   - Desde el portal AMD Developer → Cloud / Instinct
   - Activa instancia GPU cuando tengas los $100 créditos

---

## 3. Cómo saber si ya tienes créditos Fireworks

En el servidor (sin pegar la key en chat):

```bash
cd /home/rlopez/projects/amd-ralfiia-hybrid-ops-copilot
cp .env.example .env   # si no existe
nano .env              # pegar FIREWORKS_API_KEY=fw_...
./scripts/check_fireworks.sh
```

O vía API pública (jurado):

```
GET https://sworn-profusely-alongside.ngrok-free.dev/amd-ops-api/api/v1/credits/status
```

Respuesta esperada cuando **sí** hay key:

```json
"fireworks": { "configured": true, "ok": true, ... }
```

Sin key:

```json
"fireworks": { "configured": false, "hint": "Sin API key — ver docs/RAFAEL_AMD_PANEL.md" }
```

---

## 4. Qué pegar en `.env` (solo en servidor, nunca en git)

```bash
FIREWORKS_API_KEY=fw_xxxxxxxx   # desde fireworks.ai dashboard
SMART_QUOTER_AGENT_AUTH=quoter_bearer_token_change_me
WATCHDOG_AGENT_AUTH=watchdog_bearer_token_change_me
```

Luego reiniciar stack:

```bash
cd /home/rlopez/projects/amd-ralfiia-hybrid-ops-copilot
docker compose up -d --build
```

---

## 5. URLs para el jurado (ngrok — ya configurado)

| Qué | URL |
|-----|-----|
| **Console AMD (UI)** | https://sworn-profusely-alongside.ngrok-free.dev/amd-ops/ |
| **API health** | https://sworn-profusely-alongside.ngrok-free.dev/amd-ops-api/health |
| **Estado créditos** | …/amd-ops-api/api/v1/credits/status |
| **Demo integrada** | POST …/amd-ops-api/api/v1/demo/integrated |
| **Track 1 eval** | POST …/amd-ops-api/api/v1/track1/evaluate |
| **Smart Portal** | http://192.168.1.4:2002/ (LAN) |
| **Smart Quoter** | http://192.168.1.4:2026/ (LAN, integrado en demo) |

> ngrok free puede mostrar interstitial — el jurado hace click "Visit Site" una vez.

---

## 6. Si NO tienes créditos aún

El demo **funciona igual** con:
- **Ollama local** (intake + watchdog) — tokens remotos = 0
- **Smart Quoter :2026** — ya operativo
- **A2A mesh** — CrewAI + LangGraph

Solo el polish **Gemma-2 Fireworks** queda en fallback local hasta que pegues la API key.

**Acción:** escribe en el chat del hackathon lablab o email soporte AMD preguntando:
*"Registered [fecha]. When will hackathon Fireworks credits appear in my dashboard?"*

---

## 7. Checklist entrega Devpost

- [ ] Video 2-3 min abriendo URL ngrok `/amd-ops/`
- [ ] Mostrar routing local vs Fireworks en dashboard
- [ ] Mencionar Track 3 + Track 1 dual
- [ ] Repo + docker-compose
- [ ] Gemma-2 vía Fireworks (cuando tengas key)
