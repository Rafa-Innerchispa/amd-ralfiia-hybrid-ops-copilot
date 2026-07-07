# Rafael — Fireworks vs AMD (paso a paso REAL)

## Respuesta corta: ¿es el Fireworks correcto?

**Sí.** No es un producto de AMD con otro nombre. Es esta empresa:

| Qué | URL correcta | Qué es |
|-----|--------------|--------|
| **Fireworks AI** | https://app.fireworks.ai | API de modelos LLM en GPUs AMD (socio oficial) |
| **AMD Developer** | https://developer.amd.com | Portal AMD — aquí **piden** los créditos |
| **lablab hackathon** | https://lablab.ai | Registro del concurso |

**Los créditos NO aparecen solos en Fireworks.** AMD te manda un **código promocional por email** después de que llenas un formulario en el portal AMD.

---

## Qué hacer tú (orden exacto)

### Paso 1 — AMD AI Developer Program (ya entraste aquí ✅)

1. https://www.amd.com/en/developer/ai-dev-program.html
2. Login con tu cuenta AMD
3. Verifica que estés **aprobado** en el programa

### Paso 2 — Pedir créditos Fireworks (LO QUE FALTA)

1. Ve a **https://developer.amd.com/member-perks/**
2. Busca **"Request Cloud Credits"** o **"Cloud Credit Options"**
3. En el formulario elige **"Fireworks — LLM Endpoint"** (NO el de "AMD Developer Cloud" si solo quieres API)
4. Envía el formulario
5. **Espera 1-2 días hábiles** → AMD revisa manualmente
6. Recibirás **email de AMD** con:
   - un **link** para crear cuenta Fireworks, y/o
   - un **código promocional** ($50)

### Paso 3 — Activar en Fireworks (cuando llegue el email)

1. Abre **https://app.fireworks.ai** (no solo fireworks.ai marketing)
2. Crea cuenta / login
3. **Redeem** el código que mandó AMD (Settings → Billing o Credits)
4. Ve a **Settings → API Keys → Create API Key**
5. Copias la key (empieza con `fw_...`)

### Paso 4 — Pegar en el servidor (Rafael o yo)

```bash
nano /home/rlopez/projects/amd-ralfiia-hybrid-ops-copilot/.env
```

Añade una línea:

```
FIREWORKS_API_KEY=fw_tu_key_aqui
```

Guarda y reinicia:

```bash
cd /home/rlopez/projects/amd-ralfiia-hybrid-ops-copilot
./scripts/check_fireworks.sh
```

---

## ¿Tienes que hacer algo más en el proyecto?

**Para el demo de hoy: NO**, si no tienes la key aún.

| Componente | Estado sin Fireworks |
|------------|----------------------|
| API Track 1 tareas simples | ✅ Ollama local (0 tokens) |
| API Track 1 tareas complejas | ⚠️ mensaje "no API key" |
| Track 3 A2A mesh | ✅ parcial (agents locales) |
| Smart Quoter :2026 | ✅ ya vivo en el servidor |
| Panel :2002 | ✅ solo en red casa `192.168.1.4` |

**Cuando tengas la key:** solo pegarla en `.env` — el código ya está listo.

---

## Por qué "no te abre" cada página

| URL | Por qué no abre |
|-----|-----------------|
| `192.168.1.4:2002` / `:2026` | Solo funcionan **en tu red local** (casa), no desde internet |
| `192.168.1.4:5120` | UI del hackathon — debe estar en el servidor (la estamos levantando) |
| ngrok `.../amd-ops/` | A veces muestra pantalla gris "Visit Site" — haz click y continúa |
| ngrok `.../amd-ops-api/health` | **Esta SÍ funciona** — es la API para el jurado |
| lablab.ai dashboard | Necesitas login + enrollment aprobado |
| fireworks.ai (marketing) | Es la web comercial; la app real es **app.fireworks.ai** |

### URLs que SÍ puedes probar ahora (desde cualquier navegador)

1. **API jurado:** https://sworn-profusely-alongside.ngrok-free.dev/amd-ops-api/health  
   (click "Visit Site" si ngrok lo pide)

2. **Estado créditos:** https://sworn-profusely-alongside.ngrok-free.dev/amd-ops-api/api/v1/credits/status  
   → verás `"configured": false` hasta que pegues la key

---

## Dos bolsas de créditos (no las mezcles)

| Bolsa | Quién la da | Cómo la obtienes |
|-------|-------------|------------------|
| **Programa AMD nuevo** | AMD member perks | Formulario → email en 2-3 días |
| **Hackathon lablab** | Organizadores ACT II | Enrollment aprobado → dashboard lablab (puede tardar si te registraste tarde) |

Puedes usar **cualquiera** que llegue primero — ambas van a Fireworks API.

---

## Si no te llega email en 48h

1. Revisa spam
2. En lablab.ai → tu perfil del hackathon → busca "Credits" / "Resources"
3. Escribe en el chat del hackathon: *"Requested Fireworks credits via member perks on [fecha], still waiting for promo code"*

---

## Resumen en una frase

**AMD te da un cupón por email → tú lo activas en app.fireworks.ai → creas API Key → la pegas en `.env` del servidor.** No es otro Fireworks ni otro servicio AMD oculto.
