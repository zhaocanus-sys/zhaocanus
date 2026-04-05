#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置常量与路径定义
"""
import os
from pathlib import Path

_DB_HOST = os.environ.get("CYNOSDB_HOST", "bj-cynosdbmysql-grp-ggzfrbiy.sql.tencentcdb.com")
_DB_PORT = int(os.environ.get("CYNOSDB_PORT", "28291"))

# ── 数据库连接（CRM 组织架构等常规表） ──
DB_CONFIG = {
    "host": _DB_HOST,
    "port": _DB_PORT,
    "user": os.environ.get("CYNOSDB_RW_USER", "wenxiaofan_rw"),
    "password": os.environ.get("CYNOSDB_RW_PASS", "omjW#V*2.@&cE54gfTU)"),
    "charset": "utf8mb4",
}

# ── 只读账号（会话存档表专用） ──
DB_CONFIG_RO = {
    "host": _DB_HOST,
    "port": _DB_PORT,
    "user": os.environ.get("CYNOSDB_RO_USER", "wenxiaofan_ro"),
    "password": os.environ.get("CYNOSDB_RO_PASS", "aFq2HsotvSm7=7pQ&gh."),
    "charset": "utf8mb4",
}

# ── 会话存档数据库 & 表名 ──
DB_ARCHIVE = "zhenai_externalContact"
TABLE_ARCHIVE_RECENT = "SessionArchiveMsgRecord_Recent"
TABLE_ARCHIVE_FULL = "SessionArchiveMsgRecord"

# ── CRM 组织架构数据库 & 表名 ──
DB_COMPASS = "compass_data"
TABLE_WORKER = "Worker"
TABLE_DEPT = "Dept"

# ── 企微员工信息表（桥接 CRM 邮箱 → 真实企微 userId） ──
DB_WX = "zhenai_externalContact"
TABLE_WX_WORKER = "WxWorkerInfo"
CORP_SID = "39056d4cc2704cc5865228689c51bb881617852167612"

# ── 运行时路径 ──
CONFIG_DIR = Path.home() / ".conversation-archive"
OUTPUT_DIR = CONFIG_DIR / "output"
CACHE_DIR = CONFIG_DIR / "cache"

# ── 请求控制 ──
DEFAULT_PAGE_SIZE = 100

# ── 消息类型（统计用） ──
MSG_TYPE_TEXT = 1
MSG_TYPE_IMAGE = 3
MSG_TYPE_VOICE = 34
MSG_TYPE_VIDEO = 43

# ── 员工类型（基于 Dept.ability 字段） ──
EMPLOYEE_TYPES = {
    "电销": {"ability": 1},
    "电红": {"ability": 2},
    "网销": {"dept_pattern": "%网销%"},
}

# ── 团队负责人别名 → 员工类型 ──
TEAM_ALIASES = {
    "罗阳": "电销", "罗阳团队": "电销",
    "程朴娟": "网销", "程朴娟团队": "网销",
    "建信": "网销", "建信团队": "网销",
    "张心蕊": "电红", "张心蕊团队": "电红",
}


def email_to_wxid(email: str) -> str:
    """将企业邮箱转换为企微 wxid（仅做 @ → _ 转换，不强制修改域名）"""
    if not email:
        return ""
    return email.replace("@", "_")
