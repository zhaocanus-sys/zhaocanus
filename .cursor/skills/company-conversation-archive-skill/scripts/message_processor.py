#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息类型名称映射（纯统计辅助）
不处理任何消息内容，仅提供 msgType → 中文名 的映射
"""
from typing import Dict

MSG_TYPE_NAMES: Dict[int, str] = {
    1: "文本",
    3: "图片",
    34: "语音",
    43: "视频",
    47: "表情",
    49: "链接/文件",
    110: "名片",
    119: "小程序",
    4901: "撤回",
}


def type_label(msg_type: int) -> str:
    return MSG_TYPE_NAMES.get(msg_type, f"type_{msg_type}")
