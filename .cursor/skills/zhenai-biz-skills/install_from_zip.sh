#!/usr/bin/env bash
# 从 zhenai-biz-skills.zip 安装到本目录（Cursor 技能根：.../.cursor/skills/zhenai-biz-skills/）
set -euo pipefail

TARGET="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP="${1:-zhenai-biz-skills.zip}"

if [[ ! -f "$ZIP" ]]; then
  echo "未找到压缩包: $ZIP"
  echo "用法: $0 [/绝对或相对路径/zhenai-biz-skills.zip]"
  echo "示例: $0 ~/Downloads/zhenai-biz-skills.zip"
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

unzip -q -o "$ZIP" -d "$TMP"

SRC=""
if [[ -f "$TMP/zhenai-biz-skills/SKILL.md" ]]; then
  SRC="$TMP/zhenai-biz-skills"
elif [[ -f "$TMP/SKILL.md" ]]; then
  SRC="$TMP"
else
  echo "压缩包结构不符合预期（需顶层为 zhenai-biz-skills/ 或直接含 SKILL.md）。实际内容："
  find "$TMP" -maxdepth 3 -type f 2>/dev/null | head -40
  exit 1
fi

rm -rf "$TARGET"
mkdir -p "$TARGET"
cp -a "$SRC"/. "$TARGET"/

echo "已安装到: $TARGET"
echo "可选：与云端对齐（需网络）"
echo "  python3 \"$TARGET/scripts/sync_required_files.py\" --skill-name zhenai-biz-skills \\"
echo "    --base-url http://42.193.182.174:8090/skills/ --local-dir \"$TARGET\" \\"
echo "    --files SKILL.md scripts/sync_required_files.py --pretty"
