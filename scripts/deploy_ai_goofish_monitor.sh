#!/usr/bin/env bash
# 一键部署 / 重启 ai-goofish-monitor（闲鱼智能监控）
# 用法:
#   ./scripts/deploy_ai_goofish_monitor.sh install   # 克隆+依赖+构建
#   ./scripts/deploy_ai_goofish_monitor.sh start     # 启动服务
#   ./scripts/deploy_ai_goofish_monitor.sh stop      # 停止服务
#   ./scripts/deploy_ai_goofish_monitor.sh status    # 健康检查
#   ./scripts/deploy_ai_goofish_monitor.sh restart   # 重启

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${GOOFISH_DIR:-$ROOT_DIR/ai-goofish-monitor}"
REPO_URL="${GOOFISH_REPO:-https://github.com/Usagi-org/ai-goofish-monitor.git}"
SESSION_NAME="ai-goofish-monitor"
PORT="${SERVER_PORT:-8000}"
TMUX_CFG="/exec-daemon/tmux.portal.conf"

export PATH="${HOME}/.nvm/versions/node/v22.22.1/bin:/exec-daemon:${HOME}/.local/bin:${PATH}"

tmux_cmd() {
  if [[ -f "$TMUX_CFG" ]]; then
    tmux -f "$TMUX_CFG" "$@"
  else
    tmux "$@"
  fi
}

ensure_clone() {
  if [[ ! -d "$APP_DIR/.git" ]]; then
    echo "[*] 克隆仓库到 $APP_DIR"
    git clone "$REPO_URL" "$APP_DIR"
  fi
}

ensure_env() {
  mkdir -p "$APP_DIR"/{data,state,jsonl,logs,images,price_history}
  if [[ ! -f "$APP_DIR/.env" ]]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    # 默认密码，部署后请立即修改；API Key 必须替换
    sed -i 's/^OPENAI_API_KEY=.*/OPENAI_API_KEY=sk-please-replace-with-your-key/' "$APP_DIR/.env"
    sed -i 's/^WEB_PASSWORD=.*/WEB_PASSWORD=Goofish@2026/' "$APP_DIR/.env"
    grep -q '^RUN_HEADLESS=true' "$APP_DIR/.env" || echo 'RUN_HEADLESS=true' >> "$APP_DIR/.env"
    echo "[!] 已生成 $APP_DIR/.env —— 请填入真实 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL_NAME"
  fi
}

install_deps() {
  ensure_clone
  ensure_env
  echo "[*] 创建 Python 虚拟环境并安装依赖"
  if [[ ! -d "$APP_DIR/.venv" ]]; then
    python3 -m venv "$APP_DIR/.venv"
  fi
  # shellcheck disable=SC1091
  source "$APP_DIR/.venv/bin/activate"
  pip install -U pip -q
  pip install -r "$APP_DIR/requirements.txt" -q

  echo "[*] 构建前端（使用 registry.npmjs.org）"
  pushd "$APP_DIR/web-ui" >/dev/null
  npm config set registry https://registry.npmjs.org/
  if [[ ! -d node_modules ]]; then
    npm install
  fi
  npx vite build
  popd >/dev/null

  echo "[*] Playwright 将优先使用系统 Chrome (channel=chrome)"
  if command -v google-chrome >/dev/null 2>&1 || command -v google-chrome-stable >/dev/null 2>&1; then
    echo "    已检测到系统 Chrome"
  else
    echo "    警告: 未检测到 Chrome，可尝试: python -m playwright install chromium"
  fi
  echo "[✓] 安装完成"
}

is_running() {
  curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1
}

start_svc() {
  ensure_env
  if is_running; then
    echo "[✓] 服务已在运行: http://127.0.0.1:${PORT}"
    return 0
  fi
  if [[ ! -d "$APP_DIR/.venv" ]]; then
    echo "[!] 尚未安装，先执行: $0 install"
    exit 1
  fi
  tmux_cmd has-session -t "=$SESSION_NAME" 2>/dev/null || \
    tmux_cmd new-session -d -s "$SESSION_NAME" -c "$APP_DIR" -- "${SHELL:-bash}" -l
  tmux_cmd send-keys -t "$SESSION_NAME:0.0" \
    "cd '$APP_DIR' && source .venv/bin/activate && python -m src.app" C-m
  for _ in $(seq 1 20); do
    sleep 1
    if is_running; then
      echo "[✓] 已启动: http://127.0.0.1:${PORT}"
      echo "    默认账号: admin / Goofish@2026（见 .env）"
      return 0
    fi
  done
  echo "[!] 启动超时，请查看 tmux 会话: tmux attach -t $SESSION_NAME"
  exit 1
}

stop_svc() {
  if tmux_cmd has-session -t "=$SESSION_NAME" 2>/dev/null; then
    tmux_cmd kill-session -t "$SESSION_NAME" || true
  fi
  # 兜底杀掉占用端口的进程
  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${PORT}/tcp" 2>/dev/null || true
  fi
  echo "[✓] 已停止"
}

status_svc() {
  if is_running; then
    echo "[✓] healthy — http://127.0.0.1:${PORT}"
    curl -fsS "http://127.0.0.1:${PORT}/health" || true
    echo
    curl -fsS "http://127.0.0.1:${PORT}/api/settings/status" | head -c 1200 || true
    echo
  else
    echo "[!] 未运行"
    exit 1
  fi
}

case "${1:-status}" in
  install) install_deps ;;
  start) start_svc ;;
  stop) stop_svc ;;
  restart) stop_svc; start_svc ;;
  status) status_svc ;;
  *)
    echo "用法: $0 {install|start|stop|restart|status}"
    exit 1
    ;;
esac
