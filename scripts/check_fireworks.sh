#!/usr/bin/env bash
# Verifica Fireworks API key sin imprimir el secreto.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
[[ -f .env ]] || { echo "FAIL: crea .env desde .env.example"; exit 1; }
set -a; source .env; set +a
if [[ -z "${FIREWORKS_API_KEY:-}" ]]; then
  echo "FIREWORKS: NO configurada — ver docs/RAFAEL_AMD_PANEL.md"
  exit 2
fi
HTTP=$(curl -s -o /tmp/fw_test.json -w "%{http_code}" \
  -H "Authorization: Bearer ${FIREWORKS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"accounts/fireworks/models/gemma-2-9b-it","messages":[{"role":"user","content":"ping"}],"max_tokens":5}' \
  "https://api.fireworks.ai/inference/v1/chat/completions")
if [[ "$HTTP" == "200" ]]; then
  echo "FIREWORKS: OK (HTTP 200) — Gemma-2 responde"
  exit 0
elif [[ "$HTTP" == "401" ]]; then
  echo "FIREWORKS: API key inválida (401)"
  exit 1
else
  echo "FIREWORKS: HTTP $HTTP — revisar créditos/cuenta"
  cat /tmp/fw_test.json 2>/dev/null | head -c 200
  exit 1
fi
