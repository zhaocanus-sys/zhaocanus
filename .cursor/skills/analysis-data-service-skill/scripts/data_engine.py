#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据分析查询引擎 — 连接 CynosDB Libra 分析引擎，执行业务数据查询。
"""
from typing import List, Dict, Optional, Any
import json

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

from config import ANALYTICS_DB
from datasource_registry import (
    DATASOURCE_REGISTRY,
    resolve_table,
    get_database_for_table,
)


class DataEngine:
    """CynosDB 分析引擎查询封装"""

    def __init__(self, query_timeout: int = 60):
        self._conn = None
        self._query_timeout = query_timeout

    def _get_conn(self):
        if self._conn is None or not self._conn.open:
            self._conn = pymysql.connect(
                host=ANALYTICS_DB["host"],
                port=ANALYTICS_DB["port"],
                user=ANALYTICS_DB["user"],
                password=ANALYTICS_DB["password"],
                charset=ANALYTICS_DB["charset"],
                cursorclass=_LoggingDictCursor,
                connect_timeout=15,
                read_timeout=self._query_timeout,
            )
        return self._conn

    def close(self):
        if self._conn and self._conn.open:
            self._conn.close()
            self._conn = None

    def check_health(self) -> dict:
        """检查分析引擎连通性和库表可访问性"""
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("SELECT VERSION() AS ver")
            version = cur.fetchone()["ver"]

            databases = {}
            for db_name in ("compass_data", "zhenai_externalContact"):
                try:
                    cur.execute(f"SELECT COUNT(*) AS cnt FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s", (db_name,))
                    cnt = cur.fetchone()["cnt"]
                    databases[db_name] = cnt
                except Exception as e:
                    databases[db_name] = f"ERROR: {e}"

            return {
                "status": "healthy",
                "version": version,
                "databases": databases,
            }
        except Exception as e:
            return {
                "status": "unreachable",
                "error": str(e),
            }

    _ALLOWED_PREFIXES = ("SELECT", "SHOW", "DESC", "DESCRIBE", "EXPLAIN", "WITH")

    def execute_sql(self, sql: str, params: tuple = None, database: str = None) -> List[Dict]:
        """执行只读 SQL 查询（仅允许 SELECT/SHOW/DESC/EXPLAIN/WITH）"""
        stripped = sql.strip().lstrip("(").upper()
        if not any(stripped.startswith(p) for p in self._ALLOWED_PREFIXES):
            raise ValueError(f"仅允许只读查询语句（SELECT/SHOW/DESC/EXPLAIN），拒绝执行: {sql[:80]}")
        conn = self._get_conn()
        with conn.cursor() as cur:
            if database:
                cur.execute(f"USE `{database}`")
            cur.execute(sql, params)
            return cur.fetchall()

    def get_table_columns(self, table_name: str, database: str = None) -> List[Dict]:
        """获取表结构（字段名、类型、是否可空、键、默认值）"""
        if not database:
            database = get_database_for_table(table_name)
        if not database:
            raise ValueError(f"Unknown table: {table_name}")

        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(f"SHOW COLUMNS FROM `{database}`.`{table_name}`")
            rows = cur.fetchall()
        return [
            {
                "field": r["Field"],
                "type": r["Type"],
                "null": r["Null"],
                "key": r["Key"],
                "default": r["Default"],
            }
            for r in rows
        ]

    def get_table_sample(self, table_name: str, database: str = None, limit: int = 5) -> List[Dict]:
        """获取表的样本数据"""
        if not database:
            database = get_database_for_table(table_name)
        if not database:
            raise ValueError(f"Unknown table: {table_name}")

        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM `{database}`.`{table_name}` LIMIT %s", (limit,))
            return cur.fetchall()

    def get_table_count(self, table_name: str, database: str = None) -> int:
        """获取表的行数（近似值，从 information_schema 读取以避免全表扫描）"""
        if not database:
            database = get_database_for_table(table_name)
        if not database:
            raise ValueError(f"Unknown table: {table_name}")

        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT TABLE_ROWS FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
                (database, table_name),
            )
            row = cur.fetchone()
        return row["TABLE_ROWS"] if row else 0

    def query_table(
        self,
        table_name: str,
        database: str = None,
        date: str = None,
        filters: Dict[str, Any] = None,
        columns: List[str] = None,
        order_by: str = None,
        limit: int = 500,
        offset: int = 0,
    ) -> List[Dict]:
        """智能查询业务表

        Args:
            table_name: 表名
            database: 数据库名（不传则自动从注册表推断）
            date: 日期过滤（自动识别 ftime/fdate 等日期字段）
            filters: 附加过滤条件 {column: value}
            columns: 指定返回字段（不传则 SELECT *）
            order_by: 排序字段
            limit: 返回行数上限
            offset: 偏移量
        """
        if not database:
            database = get_database_for_table(table_name)
        if not database:
            raise ValueError(f"Unknown table: {table_name}")

        select_clause = ", ".join(f"`{c}`" for c in columns) if columns else "*"
        sql = f"SELECT {select_clause} FROM `{database}`.`{table_name}`"
        params: list = []
        where_parts: list = []

        if date:
            date_col = self._detect_date_column(table_name, database)
            if date_col:
                clean_date = date.replace("-", "")
                where_parts.append(f"`{date_col}` = %s")
                params.append(clean_date)

        if filters:
            for col, val in filters.items():
                where_parts.append(f"`{col}` = %s")
                params.append(val)

        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)

        if order_by:
            sql += f" ORDER BY `{order_by}`"

        sql += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def _detect_date_column(self, table_name: str, database: str) -> Optional[str]:
        """自动检测表中的日期字段（优先 ftime → fdate → dt → date）"""
        try:
            cols = self.get_table_columns(table_name, database)
            col_names = [c["field"] for c in cols]
        except Exception as e:
            print(f"[WARN] 无法检测 {database}.{table_name} 的日期字段: {e}")
            return None

        for candidate in ("ftime", "fdate", "dt", "date", "ftime_d", "data_date"):
            if candidate in col_names:
                return candidate
        for name in col_names:
            if "time" in name.lower() or "date" in name.lower():
                return name
        return None


def format_results_as_text(rows: List[Dict], max_col_width: int = 30) -> str:
    """将查询结果格式化为对齐的文本表格"""
    if not rows:
        return "(empty)"

    headers = list(rows[0].keys())
    col_widths = {}
    for h in headers:
        values = [str(r.get(h, ""))[:max_col_width] for r in rows]
        col_widths[h] = max(len(h), max(len(v) for v in values))

    header_line = " | ".join(h.ljust(col_widths[h]) for h in headers)
    sep_line = "-+-".join("-" * col_widths[h] for h in headers)

    lines = [header_line, sep_line]
    for r in rows:
        line = " | ".join(str(r.get(h, ""))[:max_col_width].ljust(col_widths[h]) for h in headers)
        lines.append(line)

    return "\n".join(lines)


def format_results_as_json(rows: List[Dict]) -> str:
    """将查询结果格式化为 JSON"""
    def _default(obj):
        from datetime import datetime, date
        from decimal import Decimal
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        return str(obj)

    return json.dumps(rows, ensure_ascii=False, indent=2, default=_default)
