#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息预处理器
将 SCRM 原始消息转为 Agent 可消费的聊天记录格式
"""
from datetime import datetime
from typing import List, Dict, Optional, Set

from config import MSG_TYPE_TEXT, MSG_TYPE_VOICE, MSG_TYPE_LINK, MSG_TYPE_FILE


class MessageProcessor:
    """SCRM 原始消息 → AI 可读聊天记录"""

    # 对 AI 分析有价值的消息类型
    USEFUL_TYPES: Set[int] = {MSG_TYPE_TEXT, MSG_TYPE_VOICE, MSG_TYPE_LINK}

    # 系统噪声（过滤掉）
    NOISE_PATTERNS = [
        "加入了群聊", "退出了群聊", "修改群名为",
        "邀请你加入了群聊", "撤回了一条消息", "拍了拍",
        "群公告已更新", "开启了朋友验证",
    ]

    @classmethod
    def filter_and_format(cls, messages: List[Dict],
                          user_map: Optional[Dict[str, str]] = None,
                          include_file: bool = False) -> str:
        """
        原始消息 → '[HH:MM] 姓名: 内容' 格式的聊天记录文本

        Args:
            messages: pageMsgRecord 返回的消息列表
            user_map: {userId: 姓名} 映射表
            include_file: 是否包含文件消息（文件名）
        """
        useful = cls.USEFUL_TYPES.copy()
        if include_file:
            useful.add(MSG_TYPE_FILE)

        lines = []
        for m in sorted(messages, key=lambda x: x.get("msgTimestamp", 0)):
            msg_type = m.get("msgType", 0)
            if msg_type not in useful:
                continue

            # 按类型提取内容
            content = cls._extract_content(m, msg_type)
            if not content:
                continue

            # 过滤系统噪声
            if any(noise in content for noise in cls.NOISE_PATTERNS):
                continue

            # 解析发送者（群聊用 roomSenderWxid，私聊用 wxidFrom）
            sender_id = m.get("roomSenderWxid") or m.get("wxidFrom", "")
            sender_name = (user_map or {}).get(sender_id, sender_id)

            # 格式化时间
            ts = m.get("msgTimestamp", 0)
            if ts > 0:
                time_str = datetime.fromtimestamp(ts / 1000).strftime("%H:%M")
            else:
                time_str = "??:??"

            lines.append(f"[{time_str}] {sender_name}: {content}")

        return "\n".join(lines)

    @classmethod
    def filter_by_date(cls, messages: List[Dict], target_date: str) -> List[Dict]:
        """按日期筛选消息 (target_date: 'YYYY-MM-DD')"""
        result = []
        for m in messages:
            ts = m.get("msgTimestamp", 0)
            if ts <= 0:
                continue
            msg_date = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
            if msg_date == target_date:
                result.append(m)
        return result

    @classmethod
    def filter_by_date_range(cls, messages: List[Dict],
                             start_date: str, end_date: str) -> List[Dict]:
        """按日期范围筛选 (inclusive)"""
        result = []
        for m in messages:
            ts = m.get("msgTimestamp", 0)
            if ts <= 0:
                continue
            d = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
            if start_date <= d <= end_date:
                result.append(m)
        return result

    @classmethod
    def stats(cls, messages: List[Dict]) -> Dict:
        """消息统计"""
        type_counts: Dict[int, int] = {}
        senders: set = set()
        for m in messages:
            mt = m.get("msgType", 0)
            type_counts[mt] = type_counts.get(mt, 0) + 1
            senders.add(m.get("roomSenderWxid") or m.get("wxidFrom", ""))

        type_names = {1: "文本", 2: "图片", 3: "语音", 4: "视频",
                      5: "文件", 6: "链接", 7: "小程序", 8: "表情"}
        named_counts = {type_names.get(k, f"type_{k}"): v
                        for k, v in sorted(type_counts.items())}

        return {
            "total": len(messages),
            "types": named_counts,
            "unique_senders": len(senders),
            "text_count": type_counts.get(1, 0),
        }

    # ── 内部方法 ──

    @staticmethod
    def _extract_content(m: Dict, msg_type: int) -> str:
        """按消息类型提取内容"""
        if msg_type == MSG_TYPE_TEXT:
            return (m.get("msg") or "").strip()
        elif msg_type == MSG_TYPE_VOICE:
            text = (m.get("audioText") or "").strip()
            return f"[语音] {text}" if text else ""
        elif msg_type == MSG_TYPE_LINK:
            title = m.get("linkTitle", "")
            url = m.get("linkUrl", "")
            return f"[链接] {title} {url}".strip()
        elif msg_type == MSG_TYPE_FILE:
            fname = m.get("fileName", "")
            return f"[文件] {fname}" if fname else ""
        return ""
