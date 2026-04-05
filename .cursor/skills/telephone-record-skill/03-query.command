#!/bin/bash
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

clear
echo "=================================="
echo "电话录音查询工具 - 查询示例"
echo "=================================="
echo ""

echo "▶ 录音类型列表:"
echo ""
python3 scripts/handler.py types

echo ""
echo "▶ 今天的电销录音（前 5 条）:"
echo ""
python3 scripts/handler.py query telsales --date today --limit 5

echo ""
read -r -p "按回车键关闭窗口..."
