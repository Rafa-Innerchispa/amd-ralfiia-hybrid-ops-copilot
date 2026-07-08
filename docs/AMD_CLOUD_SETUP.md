# AMD Developer Cloud — qué es y qué falta

## Dos bolsas distintas (no las mezcles)

| Bolsa | Token | Para qué |
|-------|-------|----------|
| **Fireworks** | `fw_…` | API LLM lista (DeepSeek, Kimi, GLM, Flux imagen) — **ya configurada** |
| **AMD Developer Cloud** | `dop_v1_…` | Créditos **horas GPU MI300X** en DigitalOcean — crear droplets |

## Tu token `dop_v1_…`

- **Sí es válido** — cuenta DigitalOcean activa (`rafagye@gmail.com`)
- **Hoy:** 0 droplets GPU creados
- **No sirve** para chat directo como Fireworks — gestiona infraestructura

## Siguiente paso para usar AMD Cloud en el demo

1. Portal AMD → crear **GPU Droplet** (MI300X, imagen ROCm)
2. SSH al droplet → desplegar vLLM (tutorial lablab: Qwen2.5-1.5B)
3. Anotar IP pública → en `.env`:

```env
AMD_INFERENCE_BASE_URL=http://TU_IP:8000/v1
AMD_INFERENCE_MODEL=Qwen/Qwen2.5-1.5B-Instruct
```

4. Reiniciar gateway: `./scripts/start_all.sh`

El hybrid router usará entonces **AMD Cloud vLLM** además de Ollama local y Fireworks.

## Video hackathon

Opcional pero recomendado. Guión corto (~3 min):

1. Consola `:8220` — routing Ollama AMD `.5` (0 tokens)
2. Tarea compleja → Fireworks DeepSeek v4 Pro
3. WhatsApp dual (primary + AMD backup)
4. Smart Quoter / panel `:2002`

## Gemma vs lo que tienes en Fireworks

Gemma es modelo **Google**, no NVIDIA. Fireworks lo corre en **GPUs AMD** en su nube.

En **tu cuenta hackathon** los modelos desplegados son: `deepseek-v4-pro`, `kimi-k2p6/p5`, `glm-5p1/p2`, `gpt-oss-120b`, `flux-1-schnell-fp8` — no Gemma-2 del doc viejo.
