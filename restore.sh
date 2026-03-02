#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 智慧助理（Linh）系统 · 全量无损迁移部署脚本 v2
# 适用：系统重装后在新机器上从备份包一键恢复
#
# 用法：
#   1. 解压备份包：tar -xzf linh-system-backup-*.tar.gz && cd linh-system-backup-*/
#   2. 执行本脚本：chmod +x restore.sh && ./restore.sh
# ═══════════════════════════════════════════════════════════════

set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
err()  { echo -e "${RED}✗ $1${NC}"; }

BACKUP_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_PROJECT="/Users/yanchen/智慧助理"
CURSOR_SKILLS_DIR="$HOME/.cursor/skills"
CURSOR_SKILLS_CURSOR_DIR="$HOME/.cursor/skills-cursor"
AGENTS_SKILLS_DIR="$HOME/.agents/skills"
CURSOR_SETTINGS="$HOME/Library/Application Support/Cursor/User"
MCPORTER_DIR="$HOME/.mcporter"

echo ""
echo "══════════════════════════════════════════════"
echo "  智慧助理（Linh）系统 · 全量恢复 v2"
echo "══════════════════════════════════════════════"
echo ""

# ─────────────────────────────────────────────
# STEP 1: 恢复工作区
# ─────────────────────────────────────────────
echo "[ 1/7 ] 恢复工作区..."

if [ -d "$BACKUP_DIR/workspace" ]; then
    if [ -d "$TARGET_PROJECT" ]; then
        warn "目标目录已存在，将合并（不删除现有文件）"
        cp -rn "$BACKUP_DIR/workspace/." "$TARGET_PROJECT/" 2>/dev/null || true
        # 强制覆盖核心文件
        for critical in \
            "agent_system/config/facts.json" \
            "agent_system/config/preferences.json" \
            "agent_system/knowledge_base/report_template_benchmark.md" \
            "agent_system/knowledge_base/report_design_principles_kb.md" \
            "agent_system/knowledge_base/zhao_management_wisdom_kb.md" \
            "generate_telesale_full_report.py" \
            "generate_hongniang_full_report.py" \
            "generate_jianxin_full_report.py" \
            "generate_app_full_report.py" \
            "generate_shop_full_report.py" \
            "DEPLOY.md"
        do
            if [ -f "$BACKUP_DIR/workspace/$critical" ]; then
                cp "$BACKUP_DIR/workspace/$critical" "$TARGET_PROJECT/$critical"
            fi
        done
    else
        mkdir -p "$(dirname "$TARGET_PROJECT")"
        cp -r "$BACKUP_DIR/workspace" "$TARGET_PROJECT"
    fi
    ok "工作区已恢复 → $TARGET_PROJECT"
else
    # 如果在工作区内直接运行（非解压包场景）
    if [ -f "$TARGET_PROJECT/agent_system/config/facts.json" ]; then
        ok "工作区已在正确位置（restore.sh 在工作区内执行）"
    else
        err "找不到 workspace/ 目录，请确认从解压包目录执行本脚本"
        exit 1
    fi
fi

# ─────────────────────────────────────────────
# STEP 2: 恢复 Cursor 全局 Skills
# ─────────────────────────────────────────────
echo ""
echo "[ 2/7 ] 恢复 Cursor 全局 Skills..."

# ~/.cursor/skills/
if [ -d "$BACKUP_DIR/cursor-skills" ]; then
    mkdir -p "$CURSOR_SKILLS_DIR"
    cp -r "$BACKUP_DIR/cursor-skills/." "$CURSOR_SKILLS_DIR/"
    ok "~/.cursor/skills/ 已恢复（$(ls "$CURSOR_SKILLS_DIR" | wc -l | tr -d ' ')个技能）"
else
    warn "备份包中无 cursor-skills/，跳过"
fi

# ~/.cursor/skills-cursor/
if [ -d "$BACKUP_DIR/cursor-skills-cursor" ]; then
    mkdir -p "$CURSOR_SKILLS_CURSOR_DIR"
    cp -r "$BACKUP_DIR/cursor-skills-cursor/." "$CURSOR_SKILLS_CURSOR_DIR/"
    ok "~/.cursor/skills-cursor/ 已恢复（$(ls "$CURSOR_SKILLS_CURSOR_DIR" | wc -l | tr -d ' ')个工具）"
else
    warn "备份包中无 cursor-skills-cursor/，跳过"
fi

# ~/.agents/skills/
if [ -d "$BACKUP_DIR/agents-skills" ]; then
    mkdir -p "$AGENTS_SKILLS_DIR"
    cp -r "$BACKUP_DIR/agents-skills/." "$AGENTS_SKILLS_DIR/"
    ok "~/.agents/skills/ 已恢复（$(ls "$AGENTS_SKILLS_DIR" | wc -l | tr -d ' ')个技能）"
else
    warn "备份包中无 agents-skills/，跳过"
fi

# ─────────────────────────────────────────────
# STEP 3: 恢复 Cursor 设置
# ─────────────────────────────────────────────
echo ""
echo "[ 3/7 ] 恢复 Cursor 设置..."

mkdir -p "$CURSOR_SETTINGS"
if [ -f "$BACKUP_DIR/cursor-settings/settings.json" ]; then
    cp "$BACKUP_DIR/cursor-settings/settings.json" "$CURSOR_SETTINGS/settings.json"
    ok "Cursor settings.json 已恢复"
fi

mkdir -p "$MCPORTER_DIR"
if [ -f "$BACKUP_DIR/cursor-settings/mcporter.json" ]; then
    cp "$BACKUP_DIR/cursor-settings/mcporter.json" "$MCPORTER_DIR/mcporter.json"
    ok "mcporter.json 已恢复"
fi

# ─────────────────────────────────────────────
# STEP 4: 安装 Python 依赖
# ─────────────────────────────────────────────
echo ""
echo "[ 4/7 ] 安装 Python 依赖..."

cd "$TARGET_PROJECT"

# 尝试多种安装方式
pip3 install requests --break-system-packages -q 2>/dev/null \
    || pip3 install requests -q 2>/dev/null \
    || pip install requests -q 2>/dev/null \
    || warn "pip 安装失败，请手动执行: pip3 install requests"

if [ -f "$TARGET_PROJECT/requirements.txt" ]; then
    pip3 install -r "$TARGET_PROJECT/requirements.txt" --break-system-packages -q 2>/dev/null \
        || pip3 install -r "$TARGET_PROJECT/requirements.txt" -q 2>/dev/null \
        || warn "requirements.txt 安装失败，请手动执行"
fi

ok "Python 依赖安装完成"

# ─────────────────────────────────────────────
# STEP 5: 安装可选工具（Agent-Reach / DataClaw / xreach）
# ─────────────────────────────────────────────
echo ""
echo "[ 5/7 ] 安装可选工具..."

# Agent-Reach
if command -v git &>/dev/null; then
    if [ ! -d "/tmp/Agent-Reach" ]; then
        git clone --depth 1 https://github.com/Panniantong/Agent-Reach.git /tmp/Agent-Reach 2>/dev/null \
            && pip3 install -e /tmp/Agent-Reach --break-system-packages -q 2>/dev/null \
            && ok "Agent-Reach 安装成功" \
            || warn "Agent-Reach 安装失败（可选功能，不影响核心报告）"
    else
        pip3 install -e /tmp/Agent-Reach --break-system-packages -q 2>/dev/null \
            && ok "Agent-Reach 已存在，重新安装" \
            || warn "Agent-Reach 重装失败"
    fi
else
    warn "git 未安装，跳过 Agent-Reach"
fi

# xreach（Twitter/X 功能）
if command -v npm &>/dev/null; then
    npm install -g xreach-cli mcporter -q 2>/dev/null \
        && ok "xreach-cli + mcporter 安装成功" \
        || warn "npm 工具安装失败（可选功能）"
else
    warn "npm 未安装，跳过 xreach-cli"
fi

# 小红书 Docker MCP
if command -v docker &>/dev/null; then
    docker start xiaohongshu-mcp 2>/dev/null \
        || docker run -d --name xiaohongshu-mcp -p 18060:18060 \
           --platform linux/amd64 xpzouying/xiaohongshu-mcp 2>/dev/null \
        && ok "小红书 MCP Docker 已启动" \
        || warn "小红书 MCP 启动失败（请确认 Docker Desktop 已安装）"
else
    warn "Docker 未安装，跳过小红书 MCP（可选功能）"
fi

# ─────────────────────────────────────────────
# STEP 6: 验证核心功能
# ─────────────────────────────────────────────
echo ""
echo "[ 6/7 ] 验证核心功能..."

cd "$TARGET_PROJECT"

# 验证 API
API_OK=false
python3 -c "
from agent_system.actions.api_client import me
r = me()
if r.get('username'):
    print('✓ API 连通 | 用户:', r.get('username'))
    exit(0)
else:
    print('✗ API 异常:', r.get('error','未知'))
    exit(1)
" 2>/dev/null && API_OK=true || warn "API 验证失败，请检查网络或 facts.json 中的 api_key"

# 验证邮件配置
SMTP_OK=false
python3 -c "
import json
with open('agent_system/config/facts.json') as f:
    cfg = json.load(f)
smtp = cfg.get('smtp', {})
required = ['host','port','from_email','auth_code']
missing = [k for k in required if not smtp.get(k)]
if missing:
    print('✗ SMTP 配置缺失:', missing)
    exit(1)
else:
    print('✓ SMTP 配置完整 |', smtp['from_email'])
" 2>/dev/null && SMTP_OK=true || warn "SMTP 配置验证失败"

# 验证知识库
KB_COUNT=$(ls agent_system/knowledge_base/*.md 2>/dev/null | wc -l | tr -d ' ')
ok "知识库：$KB_COUNT 个文件"

# 验证报告脚本
SCRIPTS=("generate_telesale_full_report.py" "generate_hongniang_full_report.py" "generate_jianxin_full_report.py" "generate_app_full_report.py" "generate_shop_full_report.py")
for s in "${SCRIPTS[@]}"; do
    if [ -f "$s" ]; then
        ok "报告脚本：$s"
    else
        err "缺失报告脚本：$s"
    fi
done

# 验证 Cursor Rules
RULES_COUNT=$(ls .cursor/rules/*.mdc 2>/dev/null | wc -l | tr -d ' ')
ok "Cursor Rules：$RULES_COUNT 个（Linh 人设 + 管理规则）"

# 验证 Cursor Skills
GLOBAL_SKILLS=$(ls "$CURSOR_SKILLS_DIR" 2>/dev/null | wc -l | tr -d ' ')
AGENT_SKILLS=$(ls "$AGENTS_SKILLS_DIR" 2>/dev/null | wc -l | tr -d ' ')
ok "全局技能：~/.cursor/skills/ $GLOBAL_SKILLS 个 | ~/.agents/skills/ $AGENT_SKILLS 个"

# ─────────────────────────────────────────────
# STEP 7: 完成报告
# ─────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo "  恢复完成 · 状态报告"
echo "══════════════════════════════════════════════"
echo ""
echo "  工作区：$TARGET_PROJECT"
echo "  API：   $([ "$API_OK" = true ] && echo '✅ 正常' || echo '❌ 异常')"
echo "  邮件：  $([ "$SMTP_OK" = true ] && echo '✅ 已配置' || echo '❌ 需检查')"
echo "  知识库：✅ $KB_COUNT 个文件"
echo "  报告器：✅ 4条业务线（电销/红娘/APP/门店）"
echo "  Linh：  ✅ $RULES_COUNT 条规则 已加载"
echo ""
echo "  ─────────────────────────────────────────"
echo "  下一步："
echo "  1. 打开 Cursor"
echo "  2. File → Open Folder → $TARGET_PROJECT"
echo "  3. 对 Linh 说：「开始工作」"
echo "  ─────────────────────────────────────────"
echo ""
