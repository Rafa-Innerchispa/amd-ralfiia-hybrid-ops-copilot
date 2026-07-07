#!/usr/bin/env bash
# Arranque local sin Docker — exposición ngrok inmediata
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SWARM="/home/rlopez/projects/innerspark-swarm-os-cursor-local"
cd "$ROOT"
[[ -f .env ]] || cp .env.example .env
set -a; source .env; set +a

export PYTHONPATH="$ROOT"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
export MONGO_URI="${MONGO_URI:-mongodb://127.0.0.1:27017}"
export SMART_QUOTER_URL="${SMART_QUOTER_URL:-http://127.0.0.1:2026}"
export SMART_QUOTER_AGENT_URL="${SMART_QUOTER_AGENT_URL:-http://127.0.0.1:8221}"
export WATCHDOG_AGENT_URL="${WATCHDOG_AGENT_URL:-http://127.0.0.1:8222}"

mkdir -p /tmp/ralfiia-amd-ops

if [[ ! -d backend/.venv ]]; then
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install -q -r backend/requirements.txt
fi
if [[ ! -d agent_smart_quoter/.venv ]]; then
  python3 -m venv agent_smart_quoter/.venv
  agent_smart_quoter/.venv/bin/pip install -q -r agent_smart_quoter/requirements.txt 2>/dev/null || \
    agent_smart_quoter/.venv/bin/pip install -q fastapi uvicorn httpx pydantic pydantic-settings pymongo python-dotenv
fi
if [[ ! -d agent_watchdog/.venv ]]; then
  python3 -m venv agent_watchdog/.venv
  agent_watchdog/.venv/bin/pip install -q -r agent_watchdog/requirements.txt
fi

for port in 8220 8221 8222 5120; do
  pid=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -oP 'pid=\K[0-9]+' | head -1 || true)
  [[ -n "${pid:-}" ]] && kill "$pid" 2>/dev/null || true
done
sleep 1

nohup backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8220 --app-dir backend > /tmp/ralfiia-amd-ops/gateway.log 2>&1 &
nohup agent_smart_quoter/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8221 --app-dir agent_smart_quoter > /tmp/ralfiia-amd-ops/quoter.log 2>&1 &
nohup agent_watchdog/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8222 --app-dir agent_watchdog > /tmp/ralfiia-amd-ops/watchdog.log 2>&1 &

# UI via python http.server + simple proxy not ideal — use nginx docker solo UI or caddy
# Minimal: serve UI static and proxy API via gateway only
if command -v docker &>/dev/null; then
  docker compose up -d ui 2>/dev/null || true
fi

# Reiniciar gateway ngrok
GW_PID=$(ss -tlnp 2>/dev/null | grep ':5188' | grep -oP 'pid=\K[0-9]+' | head -1 || true)
[[ -n "${GW_PID:-}" ]] && kill "$GW_PID" 2>/dev/null || true
sleep 1
cd "$SWARM" && nohup python scripts/public_gateway.py > /tmp/public_gateway_amd.log 2>&1 &

sleep 3
curl -sf http://127.0.0.1:8220/health && echo " gateway OK"
curl -sf http://127.0.0.1:8221/health && echo " quoter OK"
curl -sf http://127.0.0.1:8222/health && echo " watchdog OK"

BASE="${PUBLIC_NGROK_BASE:-https://sworn-profusely-alongside.ngrok-free.dev}"
echo ""
echo "JURADO UI:  ${BASE}/amd-ops/"
echo "JURADO API: ${BASE}/amd-ops-api/health"
echo "Credits:    ${BASE}/amd-ops-api/api/v1/credits/status"
