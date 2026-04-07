#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电话录音 MySQL 查询客户端
支持 7 类录音表的统一查询、详情获取和表结构探查
敏感字段（录音文本、录音地址）在查询和详情中自动屏蔽，仅可通过 count() 统计
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pymysql

class _LoggingDictCursor(pymysql.cursors.DictCursor):
    """自动输出执行的 SQL 和参数"""
    def execute(self, query, args=None):
        stripped = " ".join(query.split()).strip()
        if stripped not in ("SELECT 1", "SELECT 1;"):
            print(f"[查询SQL] {stripped}")
            if args:
                display = list(args) if isinstance(args, (list, tuple)) else [args]
                s = str(display)
                if len(s) > 500:
                    s = s[:500] + f"...(共{len(display)}个参数)"
                print(f"[查询参数] {s}")
        return super().execute(query, args)

from config import (
    DEFAULT_QUERY_LIMIT,
    QUERY_TIMEOUT,
    RECORDING_DB,
    RECORDING_TYPES,
    resolve_type,
)


class RecordingClient:
    """电话录音数据库查询客户端"""

    def __init__(self, can_view_sensitive: bool = False):
        self._conn: Optional[pymysql.Connection] = None
        self._can_view_sensitive = can_view_sensitive

    # ── 连接管理 ──

    def _get_conn(self) -> pymysql.Connection:
        if self._conn is None or not self._conn.open:
            self._conn = pymysql.connect(
                host=RECORDING_DB["host"],
                port=RECORDING_DB["port"],
                user=RECORDING_DB["user"],
                password=RECORDING_DB["password"],
                charset=RECORDING_DB["charset"],
                cursorclass=_LoggingDictCursor,
                connect_timeout=15,
                read_timeout=QUERY_TIMEOUT,
            )
        return self._conn

    def close(self):
        if self._conn and self._conn.open:
            self._conn.close()
            self._conn = None

    def ping(self) -> bool:
        """测试数据库连通性"""
        try:
            conn = self._get_conn()
            conn.ping(reconnect=True)
            return True
        except Exception:
            return False

    # ── 类型解析 ──

    @staticmethod
    def list_types() -> List[Dict]:
        """列出所有录音类型"""
        result = []
        for key, info in RECORDING_TYPES.items():
            result.append({
                "key": key,
                "label": info["label"],
                "aliases": info["aliases"],
                "database": info["database"],
                "table": info["table"],
            })
        return result

    @staticmethod
    def _resolve(record_type: str) -> Tuple[str, dict]:
        """解析录音类型，返回 (key, type_info)。无效类型抛异常。"""
        key = resolve_type(record_type)
        if not key:
            valid = ", ".join(RECORDING_TYPES.keys())
            raise ValueError(f"未知录音类型: {record_type}。可用类型: {valid}")
        return key, RECORDING_TYPES[key]

    def _full_table(self, info: dict) -> str:
        return f"`{info['database']}`.`{info['table']}`"

    @staticmethod
    def _build_time_conditions(
        time_col: str,
        date: Optional[str] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
    ) -> Tuple[List[str], List[str]]:
        """将日期筛选参数转换为范围比较条件，避免 DATE() 包裹导致索引失效。

        Returns:
            (conditions, params) — SQL 片段列表和对应参数列表
        """
        if not time_col:
            return [], []

        conditions: List[str] = []
        params: List[str] = []

        def _next_day(d: str) -> str:
            return (datetime.strptime(d, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

        if date:
            day_start = f"{date} 00:00:00"
            conditions.append(f"`{time_col}` >= %s AND `{time_col}` < %s")
            params.extend([day_start, _next_day(date)])
        else:
            if date_start:
                conditions.append(f"`{time_col}` >= %s")
                params.append(f"{date_start} 00:00:00")
            if date_end:
                conditions.append(f"`{time_col}` < %s")
                params.append(_next_day(date_end))

        return conditions, params

    # ── 表结构 ──

    def get_schema(self, record_type: str) -> List[Dict]:
        """获取指定录音表的字段结构"""
        _, info = self._resolve(record_type)
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(f"DESCRIBE {self._full_table(info)}")
            return cur.fetchall()

    # ── 查询 ──

    def query(
        self,
        record_type: str,
        date: Optional[str] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        worker_name: Optional[str] = None,
        worker_id: Optional[int] = None,
        member_id: Optional[int] = None,
        keyword: Optional[str] = None,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0,
    ) -> List[Dict]:
        """
        按条件查询录音列表（不含完整转写文本，仅摘要前 100 字符）。

        Args:
            record_type: 录音类型 key 或中文名/别名
            date: 精确日期 YYYY-MM-DD
            date_start / date_end: 日期范围
            worker_name: 坐席姓名（模糊匹配）
            worker_id: 坐席 ID
            member_id: 会员 ID
            keyword: 转写文本关键词搜索
            limit: 返回条数上限
            offset: 分页偏移
        """
        key, info = self._resolve(record_type)
        fields = info["fields"]
        table = self._full_table(info)

        sensitive = info.get("sensitive_fields", set())
        select_cols = []
        for logical, actual in fields.items():
            if logical in sensitive and not self._can_view_sensitive:
                continue
            select_cols.append(f"`{actual}` AS `{logical}`")
        select_sql = ", ".join(select_cols)

        # 构建 WHERE
        conditions: List[str] = []
        params: List = []

        time_col = fields.get("call_time") or fields.get("apply_time", "")
        tc, tp = self._build_time_conditions(time_col, date, date_start, date_end)
        conditions.extend(tc)
        params.extend(tp)

        if worker_name:
            wn_col = fields.get("worker_name") or fields.get("applicant_name") or fields.get("owner_name")
            if wn_col:
                conditions.append(f"`{wn_col}` LIKE %s")
                params.append(f"%{worker_name}%")

        if worker_id is not None:
            wi_col = fields.get("worker_id")
            if wi_col:
                conditions.append(f"`{wi_col}` = %s")
                params.append(worker_id)

        if member_id is not None:
            mi_col = fields.get("member_id")
            if mi_col:
                conditions.append(f"`{mi_col}` = %s")
                params.append(member_id)

        if keyword:
            trans_col = fields.get("transcription", "")
            if trans_col:
                conditions.append(f"`{trans_col}` LIKE %s")
                params.append(f"%{keyword}%")

        where_sql = " AND ".join(conditions) if conditions else "1=1"
        order_col = fields.get("call_time") or fields.get("apply_time") or fields.get("created_at", "id")
        sql = (
            f"SELECT {select_sql} FROM {table} "
            f"WHERE {where_sql} "
            f"ORDER BY `{order_col}` DESC "
            f"LIMIT %s OFFSET %s"
        )
        params.extend([limit, offset])

        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def count(
        self,
        record_type: str,
        date: Optional[str] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        worker_name: Optional[str] = None,
        worker_id: Optional[int] = None,
        member_id: Optional[int] = None,
        keyword: Optional[str] = None,
    ) -> int:
        """按条件统计录音总数"""
        _, info = self._resolve(record_type)
        fields = info["fields"]
        table = self._full_table(info)

        conditions: List[str] = []
        params: List = []

        time_col = fields.get("call_time") or fields.get("apply_time", "")
        tc, tp = self._build_time_conditions(time_col, date, date_start, date_end)
        conditions.extend(tc)
        params.extend(tp)

        if worker_name:
            wn_col = fields.get("worker_name") or fields.get("applicant_name") or fields.get("owner_name")
            if wn_col:
                conditions.append(f"`{wn_col}` LIKE %s")
                params.append(f"%{worker_name}%")
        if worker_id is not None:
            wi_col = fields.get("worker_id")
            if wi_col:
                conditions.append(f"`{wi_col}` = %s")
                params.append(worker_id)
        if member_id is not None:
            mi_col = fields.get("member_id")
            if mi_col:
                conditions.append(f"`{mi_col}` = %s")
                params.append(member_id)
        if keyword:
            trans_col = fields.get("transcription", "")
            if trans_col:
                conditions.append(f"`{trans_col}` LIKE %s")
                params.append(f"%{keyword}%")

        where_sql = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT COUNT(*) AS cnt FROM {table} WHERE {where_sql}"

        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return row["cnt"] if row else 0

    # ── 详情 ──

    def get_detail(self, record_type: str, record_id: int) -> Optional[Dict]:
        """获取单条录音详情（敏感字段受 can_view_sensitive 权限控制）"""
        _, info = self._resolve(record_type)
        fields = info["fields"]
        table = self._full_table(info)
        id_col = fields["id"]
        sensitive = info.get("sensitive_fields", set())

        select_cols = []
        for logical, actual in fields.items():
            if logical in sensitive and not self._can_view_sensitive:
                continue
            select_cols.append(f"`{actual}` AS `{logical}`")
        select_sql = ", ".join(select_cols)

        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(f"SELECT {select_sql} FROM {table} WHERE `{id_col}` = %s", (record_id,))
            return cur.fetchone()

    # ── 连通性探测 ──

    def probe_table(self, record_type: str) -> Tuple[bool, str]:
        """探测指定表是否可访问，返回 (ok, message)"""
        try:
            _, info = self._resolve(record_type)
            table = self._full_table(info)
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) AS cnt FROM {table} LIMIT 1")
                row = cur.fetchone()
                cnt = row["cnt"] if row else 0
                return True, f"{info['label']} ({info['table']}) 可访问，共 {cnt} 条记录"
        except Exception as e:
            return False, str(e)
