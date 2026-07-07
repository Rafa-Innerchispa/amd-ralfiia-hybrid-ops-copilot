#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -f .env ]] || cp .env.example .env
docker compose up --build -d
echo "UI http://192.168.1.4:5120 | API http://192.168.1.4:8220"
