#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置常量与路径定义
电话录音查询 Skill — 7 类录音的数据库连接与表映射
"""

from __future__ import annotations

import os
from pathlib import Path

# ── 路径（运行时数据隔离，所有产出物统一在 ~/.telephone-record/ 下） ──
CONFIG_DIR = Path.home() / ".telephone-record"
OUTPUT_DIR = CONFIG_DIR / "output"
CACHE_DIR  = CONFIG_DIR / "cache"

# ── 录音数据库连接（只读账号，6 类录音表专用） ──
RECORDING_DB = {
    "host": os.environ.get("CYNOSDB_HOST", "bj-cynosdbmysql-grp-ggzfrbiy.sql.tencentcdb.com"),
    "port": int(os.environ.get("CYNOSDB_PORT", "28291")),
    "user": os.environ.get("CYNOSDB_RO_USER", "wenxiaofan_ro"),
    "password": os.environ.get("CYNOSDB_RO_PASS", "aFq2HsotvSm7=7pQ&gh."),
    "charset": "utf8mb4",
}

# ── 请求控制 ──
DEFAULT_QUERY_LIMIT = 50
QUERY_TIMEOUT = 30  # 单次查询超时（秒）

# ── 7 类录音定义 ──
# 每种录音的 key、中文名、别名、数据库、表名、字段映射以及敏感字段标记
# sensitive_fields: 不可暴露的逻辑字段名（录音文本、录音地址），仅可用于 COUNT 统计
RECORDING_TYPES = {
    "telsales": {
        "label": "电销录音",
        "aliases": ["电话销售录音", "电销"],
        "database": "compass_data",
        "table": "telSales_call_transcription",
        "sensitive_fields": {"transcription", "record_url"},
        "fields": {
            "id": "id",
            "call_id": "callout_id",
            "member_id": "member_id",
            "worker_id": "worker_id",
            "worker_name": "worker_name",
            "call_time": "callout_time",
            "duration": "link_time",
            "record_url": "record_url",
            "transcription": "transcription",
            "status": "transcription_status",
            "created_at": "created_at",
        },
    },
    "matchmaker": {
        "label": "电红录音",
        "aliases": ["电话红娘录音", "电红"],
        "database": "compass_data",
        "table": "matchmaker_call_transcription",
        "sensitive_fields": {"transcription", "record_url"},
        "fields": {
            "id": "id",
            "call_id": "callout_id",
            "member_id": "member_id",
            "worker_id": "worker_id",
            "worker_name": "worker_name",
            "call_time": "callout_time",
            "duration": "link_time",
            "record_url": "record_url",
            "transcription": "transcription",
            "status": "transcription_status",
            "created_at": "created_at",
        },
    },
    "callin": {
        "label": "400客服录音",
        "aliases": ["客服录音", "400录音", "callin"],
        "database": "compass_data",
        "table": "callin_call_transcription",
        "sensitive_fields": {"transcription", "record_url"},
        "fields": {
            "id": "id",
            "call_id": "callin_id",
            "member_id": "member_id",
            "worker_id": "worker_id",
            "worker_name": "worker_name",
            "call_time": "callin_time",
            "caller_tel": "callin_tel",
            "callee_tel": "callee_tel",
            "call_begin": "callin_begin_time",
            "call_end": "callin_end_time",
            "duration": "duration_seconds",
            "record_url": "record_url",
            "transcription": "transcription",
            "status": "transcription_status",
            "created_at": "created_at",
        },
    },
    "voicefox": {
        "label": "AI客服录音",
        "aliases": ["AI客服", "voicefox"],
        "database": "zhenai_externalContact",
        "table": "voicefox_call_records",
        "sensitive_fields": {"transcription", "record_url"},
        "fields": {
            "id": "id",
            "call_id": "session_id",
            "task_id": "task_id",
            "call_time": "start_at",
            "answer_time": "answer_at",
            "end_time": "end_at",
            "callee": "callee",
            "caller": "caller",
            "direction": "direction",
            "duration": "duration",
            "record_url": "record_file",
            "transcription": "dialogue_text",
            "status": "sync_status",
            "created_at": "created_at",
        },
    },
    "callout": {
        "label": "外呼录音转写",
        "aliases": ["外呼录音", "外呼转写"],
        "database": "compass_data",
        "table": "CallOutRecordTextResult",
        "sensitive_fields": {"transcription", "record_url"},
        "fields": {
            "id": "id",
            "call_id": "callOutId",
            "member_id": "memberId",
            "worker_id": "workerId",
            "worker_name": "workerName",
            "call_time": "callOutTime",
            "call_tel": "callOutTel",
            "duration": "linkTime",
            "record_url": "cloud_record_url",
            "transcription": "text_content",
            "status": "status",
            "created_at": "create_time",
        },
    },
    "refund": {
        "label": "珍爱通退费语音",
        "aliases": ["退费语音", "珍爱通退费"],
        "database": "compass_data",
        "table": "refund_approval_zhenaitong_ai",
        "sensitive_fields": {"transcription"},
        "fields": {
            "id": "id",
            "source_id": "source_id",
            "member_id": "member_id",
            "member_name": "member_name",
            "refund_reason": "refund_reason",
            "refund_amount": "refund_amount",
            "apply_time": "apply_time",
            "applicant_name": "applicant_name",
            "owner_name": "owner_name",
            "owner_dept": "owner_dept",
            "transcription": "member_summary",
            "is_transcribed": "is_transcribed",
            "refund_progress": "refund_progress",
            "created_at": "create_time",
        },
    },
    "callout_detail": {
        "label": "呼出明细",
        "aliases": ["呼出详情", "外呼明细"],
        "database": "compass_data",
        "table": "CalloutDetail",
        "sensitive_fields": {"record_url", "record_filename", "record_backup_url", "local_record_url"},
        "fields": {
            "id": "calloutid",
            "member_id": "memberid",
            "worker_id": "workerid",
            "worker_name": "workername",
            "call_time": "callouttime",
            "call_begin": "calloutbegintime",
            "call_end": "calloutendtime",
            "duration": "linktime",
            "from_tel": "fromcallouttel",
            "call_tel": "callouttel",
            "record_url": "cloud_record_url",
            "local_record_url": "local_record_url",
            "record_filename": "recordfilename",
            "record_backup_url": "cloud_record_backup_url",
            "dept_id": "deptid",
            "call_type": "callType",
        },
    },
}


def resolve_type(name: str) -> str | None:
    """将用户输入的类型名/别名解析为标准 key，返回 None 表示未匹配。"""
    name_lower = name.strip().lower()
    if name_lower in RECORDING_TYPES:
        return name_lower
    for key, info in RECORDING_TYPES.items():
        if name_lower == info["label"].lower():
            return key
        for alias in info["aliases"]:
            if name_lower == alias.lower():
                return key
    return None
