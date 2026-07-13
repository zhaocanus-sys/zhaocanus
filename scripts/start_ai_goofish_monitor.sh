#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${GOOFISH_DIR:-$ROOT_DIR/ai-goofish-monitor}"
PORT="${SERVER_PORT:-8000}"

if [ ! -d "$APP_DIR" ]; then
  echo "未找到 $APP_DIR，请先执行: bash scripts/deploy_ai_goofish_monitor.sh"
  exit 1
fi

cd "$APP_DIR"
mkdir -p logs
export PATH="${HOME}/.local/bin:${PATH}"

if [ -f logs/server.pid ] && kill -0 "$(cat logs/server.pid)" 2>/dev/null; then
  echo "已在运行 PID=$(cat logs/server.pid)"
  exit 0
fi

nohup python3 -m src.app > logs/server.log 2>&1 &
echo $! > logs/server.pid
sleep 2
if curl -sf "http://127.0.0.1:${PORT}/" >/dev/null; then
  echo "已启动 http://127.0.0.1:${PORT}  PID=$(cat logs/server.pid)"
else
  echo "启动失败，见 logs/server.log"
  exit 1
fi
