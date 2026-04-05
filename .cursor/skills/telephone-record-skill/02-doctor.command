#!/bin/bash
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

clear
echo "=================================="
echo "电话录音查询工具 - 第 2 步 / 诊断"
echo "=================================="
echo ""

python3 scripts/handler.py doctor
code=$?

if [ "$code" -eq 0 ]; then
    echo ""
    echo "✅ 所有检查通过，可以开始使用"
    echo "下一步：请双击 03-query.command 查看录音数据"
elif [ "$code" -eq 2 ]; then
    echo ""
    echo "⚠️  存在警告，部分功能受限"
    echo "请把这个窗口完整截图发给管理员。"
else
    echo ""
    echo "❌ 诊断发现问题"
    echo "请把这个窗口完整截图发给管理员。"
fi

echo ""
read -r -p "按回车键关闭窗口..."
exit "${code:-1}"
