#!/usr/bin/env bash
# Levanta stack AMD + reinicia gateway ngrok con rutas /amd-ops
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SWARM="/home/rlopez/projects/innerspark-swarm-os-cursor-local"

cd "$ROOT"
[[ -f .env ]] || cp .env.example .env
chmod +x scripts/check_fireworks.sh 2>/dev/null || true

echo "==> Docker compose AMD ops..."
docker compose up -d --build

echo "==> Reiniciando public gateway :5188 (rutas /amd-ops)..."
GW_PID=$(ss -tlnp 2>/dev/null | grep ':5188' | grep -oP 'pid=\K[0-9]+' | head -1 || true)
if [[ -n "${GW_PID:-}" ]]; then
  kill "$GW_PID" 2>/dev/null || true
  sleep 1
fi
cd "$SWARM"
nohup python scripts/public_gateway.py >> /tmp/public_gateway_amd.log 2>&1 &
sleep 2

BASE="https://sworn-profusely-alongside.ngrok-free.dev"
echo ""
echo "=== URLs JURADO ==="
echo "UI:  ${BASE}/amd-ops/"
echo "API: ${BASE}/amd-ops-api/health"
echo "Credits: ${BASE}/amd-ops-api/api/v1/credits/status"
echo ""
echo "LAN UI:  http://192.168.1.4:5120/"
echo "Smart Portal: http://192.168.1.4:2002/"
echo "Smart Quoter: http://192.168.1.4:2026/"
echo ""
./scripts/check_fireworks.sh 2>/dev/null || echo "(Fireworks pendiente — ver docs/RAFAEL_AMD_PANEL.md)"
