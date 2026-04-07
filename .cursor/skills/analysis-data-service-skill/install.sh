#!/bin/bash
# analysis-data-service-skill 安装脚本
set -euo pipefail

SKILL_NAME="analysis-data-service-skill"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.analysis-data-service"

echo "📊 $SKILL_NAME 安装程序"
echo "=================================="

# ── Python ──
echo ""
echo "▶ 检查 Python..."
if ! command -v python3 &>/dev/null; then
    echo "❌ 未找到 python3"
    exit 1
fi
if ! python3 -m pip --version &>/dev/null; then
    echo "❌ 当前 python3 不可用 pip"
    echo "   请先安装 pip，再重新执行 bash install.sh"
    exit 1
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  ✅ Python $PY_VER"

# ── pip 依赖 ──
echo ""
echo "▶ 安装 Python 依赖..."

for pkg in pymysql; do
    if ! python3 -c "import $pkg" 2>/dev/null; then
        echo "  ⏳ 安装 $pkg..."
        python3 -m pip install "$pkg" -q
    fi
    echo "  ✅ $pkg"
done

# ── 运行时目录 ──
echo ""
echo "▶ 初始化运行时目录..."
mkdir -p "$CONFIG_DIR/cache"
echo "  ✅ $CONFIG_DIR"

# ── 鉴权配置（本地校验：内嵌于 scripts/auth_config.json，不从远端拉取、无需复制到 ~/.zhenai-skills）──
echo ""
echo "▶ 检查鉴权配置..."
AUTH_CFG="$SCRIPT_DIR/scripts/auth_config.json"
if [ -f "$AUTH_CFG" ]; then
    echo "  ✅ 已找到内嵌鉴权配置: scripts/auth_config.json"
else
    echo "  ❌ 未找到 scripts/auth_config.json（应为项目内嵌文件）"
    exit 1
fi
mkdir -p "$HOME/.zhenai-skills"
if [ -n "${ZHENAI_API_KEY:-}" ]; then
    echo "  ✅ ZHENAI_API_KEY 已设置（环境变量，可覆盖内嵌配置）"
elif [ -f "$HOME/.zhenai-skills/api_key" ]; then
    echo "  ✅ API Key 已配置于 ~/.zhenai-skills/api_key（可覆盖内嵌配置）"
fi

# ── 安装后自检 ──
echo ""
echo "▶ 执行安装后自检..."
if python3 scripts/handler.py doctor --setup-only; then
    echo "  ✅ 安装环境检查通过"
else
    echo "  ❌ 安装环境检查失败"
    echo "     请根据上面的诊断提示修复后，再重新执行 bash install.sh"
    exit 1
fi

# ── 完成 ──
echo ""
echo "=================================="
echo "✅ $SKILL_NAME 安装完成!"
echo ""
echo "快速开始:"
echo "  cd $SCRIPT_DIR"
echo "  python3 scripts/handler.py data health    # 检查分析引擎连通性"
echo "  python3 scripts/handler.py data sources   # 列出所有业务域"
echo "  python3 scripts/handler.py doctor          # 完整环境诊断"
echo "=================================="
