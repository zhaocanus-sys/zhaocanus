#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组织架构解析器
通过 CRM compass_data + WxWorkerInfo 桥接，解析员工信息并获取真实企微 userId
"""
from typing import List, Dict, Optional

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
    DB_CONFIG, DB_COMPASS, TABLE_WORKER, TABLE_DEPT,
    DB_WX, TABLE_WX_WORKER, CORP_SID,
    EMPLOYEE_TYPES, TEAM_ALIASES, email_to_wxid,
)


class OrgResolver:
    """组织架构解析器"""

    def __init__(self):
        self._conn = None
        self._wxid_cache: Optional[Dict[str, str]] = None

    def _get_conn(self):
        if self._conn is None or not self._conn.open:
            self._conn = pymysql.connect(
                **DB_CONFIG,
                cursorclass=_LoggingDictCursor,
                connect_timeout=15,
                read_timeout=30,
            )
        return self._conn

    def close(self):
        if self._conn and self._conn.open:
            self._conn.close()
            self._conn = None

    def _get_wxid_map(self) -> Dict[str, str]:
        """加载或返回 WxWorkerInfo email→userId 映射缓存"""
        if self._wxid_cache is not None:
            return self._wxid_cache
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT email, userId FROM {DB_WX}.{TABLE_WX_WORKER} "
                f"WHERE sid = %s AND workStatus = 1 "
                f"AND email IS NOT NULL AND email != ''",
                (CORP_SID,),
            )
            rows = cur.fetchall()
        self._wxid_cache = {r["email"]: r["userId"] for r in rows if r.get("email")}
        return self._wxid_cache

    def _enrich_row(self, row: Dict) -> Dict:
        """为员工记录添加真实 wxid 和状态标签"""
        row["status_label"] = "在职" if row.get("dimissionDate") is None else "离职"
        email = row.get("email") or ""
        wxid_map = self._get_wxid_map()
        if email in wxid_map:
            row["wxid"] = wxid_map[email]
        else:
            row["wxid"] = email_to_wxid(email)
        return row

    # ── 员工查询 ──────────────────────────────────

    def search_users(self, keyword: str, active_only: bool = True) -> List[Dict]:
        """按姓名模糊搜索员工"""
        conn = self._get_conn()
        with conn.cursor() as cur:
            sql = (
                f"SELECT w.workerId, w.workerName, w.email, w.deptId, w.groupId, "
                f"w.phoneNumber, w.joinDate, w.dimissionDate, w.workerStatus, "
                f"d.deptName "
                f"FROM {DB_COMPASS}.{TABLE_WORKER} w "
                f"LEFT JOIN {DB_COMPASS}.{TABLE_DEPT} d ON w.deptId = d.deptId "
                f"WHERE w.workerName LIKE %s"
            )
            params = [f"%{keyword}%"]
            if active_only:
                sql += " AND w.dimissionDate IS NULL"
            sql += " ORDER BY w.workerName LIMIT 100"
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [self._enrich_row(r) for r in rows]

    def resolve_user(self, worker_id: int) -> Optional[Dict]:
        """按工号查用户详情"""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT w.*, d.deptName "
                f"FROM {DB_COMPASS}.{TABLE_WORKER} w "
                f"LEFT JOIN {DB_COMPASS}.{TABLE_DEPT} d ON w.deptId = d.deptId "
                f"WHERE w.workerId = %s",
                (worker_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return self._enrich_row(row)

    # ── 部门查询 ──────────────────────────────────

    def list_depts(self, active_only: bool = True) -> List[Dict]:
        """列出所有部门"""
        conn = self._get_conn()
        with conn.cursor() as cur:
            sql = f"SELECT * FROM {DB_COMPASS}.{TABLE_DEPT}"
            if active_only:
                sql += " WHERE disabled = 0"
            sql += " ORDER BY deptName"
            cur.execute(sql)
            return cur.fetchall()

    def search_dept(self, keyword: str) -> List[Dict]:
        """按名称搜索部门"""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT * FROM {DB_COMPASS}.{TABLE_DEPT} "
                f"WHERE deptName LIKE %s ORDER BY deptName",
                (f"%{keyword}%",),
            )
            return cur.fetchall()

    def list_dept_members(self, dept_id: int, active_only: bool = True) -> List[Dict]:
        """列出部门成员"""
        conn = self._get_conn()
        with conn.cursor() as cur:
            sql = (
                f"SELECT w.workerId, w.workerName, w.email, w.deptId, w.groupId, "
                f"w.phoneNumber, w.joinDate, w.dimissionDate, w.workerStatus, "
                f"d.deptName "
                f"FROM {DB_COMPASS}.{TABLE_WORKER} w "
                f"LEFT JOIN {DB_COMPASS}.{TABLE_DEPT} d ON w.deptId = d.deptId "
                f"WHERE w.deptId = %s"
            )
            params = [dept_id]
            if active_only:
                sql += " AND w.dimissionDate IS NULL"
            sql += " ORDER BY w.workerName"
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [self._enrich_row(r) for r in rows]

    # ── 按员工类型查询 ──────────────────────────────

    def get_employees_by_type(
        self, employee_type: str, active_only: bool = True
    ) -> List[Dict]:
        """按员工类型（电销/电红/网销/建信）或团队别名查询员工列表，返回带真实 wxid。"""
        resolved_type = TEAM_ALIASES.get(employee_type, employee_type)
        type_config = EMPLOYEE_TYPES.get(resolved_type)
        if not type_config:
            return []
        conn = self._get_conn()
        with conn.cursor() as cur:
            if "ability" in type_config:
                sql = (
                    f"SELECT w.workerId, w.workerName, w.email, w.deptId, w.groupId, "
                    f"w.phoneNumber, w.joinDate, w.dimissionDate, w.workerStatus, "
                    f"d.deptName, d.ability "
                    f"FROM {DB_COMPASS}.{TABLE_WORKER} w "
                    f"JOIN {DB_COMPASS}.{TABLE_DEPT} d ON w.deptId = d.deptId "
                    f"WHERE d.ability = %s"
                )
                params: list = [type_config["ability"]]
            else:
                sql = (
                    f"SELECT w.workerId, w.workerName, w.email, w.deptId, w.groupId, "
                    f"w.phoneNumber, w.joinDate, w.dimissionDate, w.workerStatus, "
                    f"d.deptName, d.ability "
                    f"FROM {DB_COMPASS}.{TABLE_WORKER} w "
                    f"JOIN {DB_COMPASS}.{TABLE_DEPT} d ON w.deptId = d.deptId "
                    f"WHERE d.deptName LIKE %s"
                )
                params = [type_config["dept_pattern"]]
            if active_only:
                sql += " AND w.dimissionDate IS NULL"
            sql += " ORDER BY d.deptName, w.workerName"
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [self._enrich_row(r) for r in rows]
