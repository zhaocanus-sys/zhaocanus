#!/bin/bash
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

clear
echo "=================================="
echo "电话录音查询工具 - 第 1 步 / 安装"
echo "=================================="
echo ""
echo "正在安装依赖并执行安装后自检，请稍等..."
echo ""

if bash install.sh; then
    code=0
    echo ""
    echo "✅ 安装完成"
    echo "下一步：请双击 02-doctor.command"
else
    code=$?
    echo ""
    echo "❌ 安装失败"
    echo "请把这个窗口完整截图发给管理员，方便定位缺失的依赖或网络问题。"
fi

echo ""
read -r -p "按回车键关闭窗口..."
exit "${code:-1}"
