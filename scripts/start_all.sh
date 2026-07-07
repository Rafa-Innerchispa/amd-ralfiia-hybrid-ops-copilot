#!/usr/bin/env bash
# Arranque completo AMD ops — gateway + agents + ngrok (sin Fireworks)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SWARM="/home/rlopez/projects/innerspark-swarm-os-cursor-local"
LOG="/tmp/ralfiia-amd-ops"
mkdir -p "$LOG"
cd "$ROOT"
[[ -f .env ]] || cp .env.example .env

export PYTHONPATH="$ROOT"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
export MONGO_URI="${MONGO_URI:-mongodb://127.0.0.1:27017}"
export SMART_QUOTER_URL="${SMART_QUOTER_URL:-http://127.0.0.1:2026}"
export SMART_QUOTER_AGENT_URL="http://127.0.0.1:8221"
export WATCHDOG_AGENT_URL="http://127.0.0.1:8222"
export SMART_QUOTER_AGENT_AUTH="${SMART_QUOTER_AGENT_AUTH:-quoter_bearer_token_change_me}"
export WATCHDOG_AGENT_AUTH="${WATCHDOG_AGENT_AUTH:-watchdog_bearer_token_change_me}"

kill_port() {
  local p=$1
  local pid
  pid=$(ss -tlnp 2>/dev/null | grep ":${p} " | grep -oP 'pid=\K[0-9]+' | head -1 || true)
  [[ -n "${pid:-}" ]] && kill "$pid" 2>/dev/null || true
}

ensure_venv() {
  local dir=$1 req=$2
  if [[ ! -x "$dir/.venv/bin/uvicorn" ]]; then
    python3 -m venv "$dir/.venv"
    "$dir/.venv/bin/pip" install -q -r "$req" 2>/dev/null || \
      "$dir/.venv/bin/pip" install -q fastapi uvicorn httpx pydantic pydantic-settings pymongo python-dotenv
  fi
}

ensure_venv "$ROOT/backend" "$ROOT/backend/requirements.txt"
ensure_venv "$ROOT/agent_smart_quoter" "$ROOT/agent_smart_quoter/requirements-core.txt"
ensure_venv "$ROOT/agent_watchdog" "$ROOT/agent_watchdog/requirements.txt"

for p in 8220 8221 8222; do kill_port "$p"; done
sleep 1

nohup "$ROOT/backend/.venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8220 \
  --app-dir "$ROOT/backend" > "$LOG/gateway.log" 2>&1 &
nohup "$ROOT/agent_smart_quoter/.venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8221 \
  --app-dir "$ROOT/agent_smart_quoter" > "$LOG/quoter.log" 2>&1 &
nohup "$ROOT/agent_watchdog/.venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8222 \
  --app-dir "$ROOT/agent_watchdog" > "$LOG/watchdog.log" 2>&1 &

kill_port 5188
sleep 1
cd "$SWARM" && nohup python scripts/public_gateway.py > "$LOG/ngrok-gateway.log" 2>&1 &

echo "Esperando servicios…"
for i in $(seq 1 25); do
  curl -sf http://127.0.0.1:8220/health >/dev/null 2>&1 && break
  sleep 1
done
sleep 2

BASE="${PUBLIC_NGROK_BASE:-https://sworn-profusely-alongside.ngrok-free.dev}"
echo ""
echo "=== RalfIIA AMD Ops — LISTO ==="
echo "Console local:  http://192.168.1.4:8220/console/"
echo "Console jurado: ${BASE}/amd-ops/"
echo "API jurado:     ${BASE}/amd-ops-api/health"
echo "Smart Quoter:   http://192.168.1.4:2026/"
echo "Logs:           $LOG/"
echo ""
curl -sf http://127.0.0.1:8220/health | python3 -m json.tool 2>/dev/null | head -8 || cat "$LOG/gateway.log" | tail -5
curl -sf http://127.0.0.1:8221/health && echo " quoter OK" || echo " quoter FAIL — ver $LOG/quoter.log"
curl -sf http://127.0.0.1:8222/health && echo " watchdog OK" || echo " watchdog FAIL — ver $LOG/watchdog.log"
