#!/usr/bin/env bash
# 一键部署 Usagi-org/ai-goofish-monitor（本机 / VPS）
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${GOOFISH_DIR:-$ROOT_DIR/ai-goofish-monitor}"
REPO_URL="${GOOFISH_REPO:-https://github.com/Usagi-org/ai-goofish-monitor.git}"
PORT="${SERVER_PORT:-8000}"

GREEN='\033[0;32m';YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== ai-goofish-monitor 一键部署 ===${NC}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo -e "${RED}缺少命令: $1${NC}"
    exit 1
  fi
}

need_cmd git
need_cmd python3
need_cmd npm

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo -e "${RED}需要 Python 3.10+${NC}"
  exit 1
fi

if [ ! -d "$APP_DIR/.git" ]; then
  echo -e "${YELLOW}克隆仓库...${NC}"
  git clone "$REPO_URL" "$APP_DIR"
else
  echo -e "${YELLOW}更新仓库...${NC}"
  git -C "$APP_DIR" pull --ff-only || true
fi

cd "$APP_DIR"
mkdir -p data state prompts logs images jsonl price_history

if [ ! -f .env ]; then
  cp .env.example .env
  # 随机 Web 密码
  if command -v openssl >/dev/null 2>&1; then
    WEB_PASS="$(openssl rand -base64 18 | tr -dc 'A-Za-z0-9' | head -c 16)"
  else
    WEB_PASS="admin$(date +%s | tail -c 8)"
  fi
  if grep -q '^WEB_PASSWORD=' .env; then
    sed -i.bak "s/^WEB_PASSWORD=.*/WEB_PASSWORD=${WEB_PASS}/" .env && rm -f .env.bak
  else
    echo "WEB_PASSWORD=${WEB_PASS}" >> .env
  fi
  echo "$WEB_PASS" > .web_password
  chmod 600 .env .web_password
  echo -e "${YELLOW}已生成 .env，Web 密码写入 .web_password${NC}"
  echo -e "${YELLOW}请编辑 .env 填入 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL_NAME${NC}"
fi

export PATH="${HOME}/.local/bin:${PATH}"
echo -e "${YELLOW}安装 Python 依赖...${NC}"
python3 -m pip install -r requirements.txt --quiet

echo -e "${YELLOW}安装 Playwright（系统 Chrome 通道优先）...${NC}"
python3 -m pip install playwright --quiet
python3 -m playwright install chromium || true
if command -v sudo >/dev/null 2>&1; then
  sudo python3 -m playwright install-deps chromium 2>/dev/null || true
  if ! command -v google-chrome >/dev/null 2>&1 && ! command -v chromium >/dev/null 2>&1 && ! command -v chromium-browser >/dev/null 2>&1; then
    sudo apt-get update -qq
    sudo apt-get install -y -qq chromium-browser 2>/dev/null || sudo apt-get install -y -qq chromium 2>/dev/null || true
  fi
fi

echo -e "${YELLOW}构建前端...${NC}"
cd web-ui
npm config set registry https://registry.npmjs.org/
npm install --silent
# 跳过 vue-tsc（上游偶发 TS2589），直接 vite 构建
npx vite build
cd "$APP_DIR"

if [ ! -f dist/index.html ]; then
  echo -e "${RED}前端构建失败：缺少 dist/index.html${NC}"
  exit 1
fi

# 若已有进程则先停
if [ -f logs/server.pid ] && kill -0 "$(cat logs/server.pid)" 2>/dev/null; then
  echo -e "${YELLOW}停止旧进程 $(cat logs/server.pid)...${NC}"
  kill "$(cat logs/server.pid)" 2>/dev/null || true
  sleep 1
fi

echo -e "${YELLOW}启动服务 (port ${PORT})...${NC}"
nohup python3 -m src.app > logs/server.log 2>&1 &
echo $! > logs/server.pid
sleep 2

if curl -sf "http://127.0.0.1:${PORT}/" >/dev/null; then
  echo -e "${GREEN}✓ 部署成功${NC}"
  echo -e "  Web UI : http://127.0.0.1:${PORT}"
  echo -e "  API 文档: http://127.0.0.1:${PORT}/docs"
  echo -e "  账号   : $(grep '^WEB_USERNAME=' .env | cut -d= -f2-)"
  if [ -f .web_password ]; then
    echo -e "  密码   : $(cat .web_password)"
  else
    echo -e "  密码   : 见 .env 中 WEB_PASSWORD"
  fi
  echo -e "  日志   : $APP_DIR/logs/server.log"
  echo -e "${YELLOW}下一步：填 API Key → 导入闲鱼登录态 → 创建任务${NC}"
else
  echo -e "${RED}服务未响应，请查看 logs/server.log${NC}"
  tail -n 40 logs/server.log || true
  exit 1
fi
