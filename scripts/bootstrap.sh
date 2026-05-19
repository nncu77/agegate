#!/usr/bin/env bash
# AgeGate bootstrap script
#
# 設定本地開發環境。可重複執行(idempotent)。
# 不安裝 ML heavy dependencies(InsightFace、MiVOLO、torch),
# 那些在 WEEK1-03 / WEEK1-04 才裝。

set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> AgeGate bootstrap"
echo

# ----- check prerequisites -----

command -v python3.11 >/dev/null 2>&1 || {
  echo "ERROR: python3.11 not found. Install Python 3.11."
  exit 1
}

command -v node >/dev/null 2>&1 || {
  echo "ERROR: node not found. Install Node.js 20 LTS."
  exit 1
}

NODE_MAJOR=$(node -p "process.versions.node.split('.')[0]")
if [ "$NODE_MAJOR" -lt 20 ]; then
  echo "ERROR: Node.js >= 20 required, found $(node --version)"
  exit 1
fi

echo "==> Prerequisites OK"
echo "  python: $(python3.11 --version)"
echo "  node:   $(node --version)"
echo

# ----- backend -----

cd backend

if [ ! -d ".venv" ]; then
  echo "==> Creating backend venv"
  python3.11 -m venv .venv
fi

echo "==> Installing backend deps (excluding heavy ML libs)"
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip --quiet
# Install everything except ML-heavy packages (they go in WEEK1-03/04)
grep -vE '^(insightface|onnxruntime|torch)' requirements.txt > /tmp/agegate-light.txt
pip install -r /tmp/agegate-light.txt --quiet
rm /tmp/agegate-light.txt

if [ ! -f ".env" ]; then
  echo "==> Creating .env from .env.example"
  cp .env.example .env
  echo "    !! Edit backend/.env with your Supabase credentials before running tasks that need DB."
fi

echo "==> Running backend tests"
PYTHONPATH=. python -m pytest -q tests/test_decision.py

cd ..

# ----- frontend -----

cd frontend

if [ ! -d "node_modules" ]; then
  echo "==> Installing frontend deps"
  npm install --no-fund --no-audit
fi

if [ ! -f ".env.local" ]; then
  echo "==> Creating frontend .env.local from .env.example"
  cp .env.example .env.local
fi

echo "==> Running typecheck"
npm run typecheck

cd ..

echo
echo "==> Bootstrap complete"
echo
echo "Next steps:"
echo "  1. Read CLAUDE.md"
echo "  2. Open tasks/INDEX.md and start with WEEK1-01"
echo
