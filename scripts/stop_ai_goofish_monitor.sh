#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${GOOFISH_DIR:-$ROOT_DIR/ai-goofish-monitor}"

if [ ! -d "$APP_DIR" ]; then
  echo "未找到 $APP_DIR"
  exit 1
fi

cd "$APP_DIR"
if [ -f logs/server.pid ]; then
  PID="$(cat logs/server.pid)"
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID" || true
    echo "已停止 PID=$PID"
  else
    echo "PID 文件存在但进程已退出"
  fi
  rm -f logs/server.pid
else
  # 兜底：按端口杀
  PIDS="$(pgrep -f 'python3 -m src.app' || true)"
  if [ -n "$PIDS" ]; then
    kill $PIDS || true
    echo "已停止: $PIDS"
  else
    echo "未发现运行中的服务"
  fi
fi
