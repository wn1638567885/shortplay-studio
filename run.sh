#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "$ROOT/frontend/dist/index.html" ]; then
  echo "[剧作工坊] 首次启动，正在构建前端..."
  cd "$ROOT/frontend"
  npm install --no-audit --no-fund
  npm run build
fi

cd "$ROOT/backend"

if [ ! -x ".venv/bin/python" ] || ! .venv/bin/python -c "import uvicorn" >/dev/null 2>&1; then
  echo "[剧作工坊] 准备 Python 虚拟环境..."
  python3 -m venv .venv
  .venv/bin/python -m pip install -q --upgrade pip
  .venv/bin/python -m pip install -q -r requirements.txt
fi

echo "[剧作工坊] 服务启动： http://localhost:8787"
exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8787
