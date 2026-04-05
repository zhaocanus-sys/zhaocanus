#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
珍爱网数据分析服务 — 配置常量与路径定义
"""
import os
from pathlib import Path

# ── 路径（运行时数据隔离） ──
CONFIG_DIR = Path.home() / ".analysis-data-service"
CACHE_DIR  = CONFIG_DIR / "cache"

_DB_HOST = os.environ.get("CYNOSDB_HOST", "bj-cynosdbmysql-grp-ggzfrbiy.sql.tencentcdb.com")
_DB_PORT = int(os.environ.get("CYNOSDB_PORT", "28291"))

# ── CynosDB 分析引擎（Libra 列存，业务查询走 RW 账号，天然只读） ──
ANALYTICS_DB = {
    "host": _DB_HOST,
    "port": _DB_PORT,
    "user": os.environ.get("CYNOSDB_RW_USER", "wenxiaofan_rw"),
    "password": os.environ.get("CYNOSDB_RW_PASS", "omjW#V*2.@&cE54gfTU)"),
    "charset": "utf8mb4",
}

# ── 只读账号（仅 zhenai_externalContact.WxDepartment；该表仅对 wenxiaofan_ro 授权 SELECT） ──
ANALYTICS_DB_RO = {
    "host": _DB_HOST,
    "port": _DB_PORT,
    "user": os.environ.get("CYNOSDB_RO_USER", "wenxiaofan_ro"),
    "password": os.environ.get("CYNOSDB_RO_PASS", "aFq2HsotvSm7=7pQ&gh."),
    "charset": "utf8mb4",
}
