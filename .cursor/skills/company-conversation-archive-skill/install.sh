#!/bin/bash
# company-conversation-archive-skill 安装脚本
set -euo pipefail

SKILL_NAME="company-conversation-archive-skill"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.conversation-archive"

echo "$SKILL_NAME 安装程序"
echo "=================================="

# ── Python ──
echo ""
echo "> 检查 Python..."
if ! command -v python3 &>/dev/null; then
    echo "  [ERR] 未找到 python3"
    exit 1
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  [OK] Python $PY_VER"

# ── pip 依赖 ──
echo ""
echo "> 安装 Python 依赖..."

for pkg in pymysql requests anthropic zhipuai; do
    if ! python3 -c "import $pkg" 2>/dev/null; then
        echo "  安装 $pkg..."
        python3 -m pip install "$pkg" -q
    fi
    echo "  [OK] $pkg"
done

# ── 运行时目录 ──
echo ""
echo "> 初始化运行时目录..."
mkdir -p "$CONFIG_DIR/output" "$CONFIG_DIR/cache"
echo "  [OK] $CONFIG_DIR"

# ── 鉴权配置（本地校验：内嵌于 scripts/auth_config.json，不从远端拉取、无需复制到 ~/.zhenai-skills）──
echo ""
echo "> 检查鉴权配置..."
AUTH_CFG="$SCRIPT_DIR/scripts/auth_config.json"
if [ -f "$AUTH_CFG" ]; then
    echo "  [OK] 已找到内嵌鉴权配置: scripts/auth_config.json"
else
    echo "  [ERR] 未找到 scripts/auth_config.json（应为项目内嵌文件）"
    exit 1
fi
mkdir -p "$HOME/.zhenai-skills"
if [ -n "${ZHENAI_API_KEY:-}" ]; then
    echo "  [OK] ZHENAI_API_KEY 已设置（环境变量，可覆盖内嵌配置）"
elif [ -f "$HOME/.zhenai-skills/api_key" ]; then
    echo "  [OK] API Key 已配置于 ~/.zhenai-skills/api_key（可覆盖内嵌配置）"
fi

# ── 连接检查 ──
echo ""
echo "> 检查数据库连接..."
if python3 "$SCRIPT_DIR/scripts/handler.py" doctor; then
    echo "  [OK] 数据库连接正常"
else
    echo "  [WARN] 数据库连接失败，请检查网络或 VPN"
fi

# ── 完成 ──
echo ""
echo "=================================="
echo "[OK] $SKILL_NAME 安装完成!"
echo ""
echo "快速开始:"
echo "  cd $SCRIPT_DIR"
echo "  python3 scripts/handler.py doctor            # 环境诊断"
echo "  python3 scripts/handler.py list-users         # 列出有存档的员工"
echo "  python3 scripts/handler.py org dept            # 列出部门"
echo ""
echo "AI 可选能力:"
echo "  export ANTHROPIC_API_KEY=xxx                  # 使用 Claude"
echo "  export Z_API_KEY=xxx                          # 使用智谱"
echo "=================================="
