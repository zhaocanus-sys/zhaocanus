#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企微组织架构解析器（CynosDB 版）
  1. WxDepartment 部门树：使用 wenxiaofan_ro 只读账号（该表仅对此账号授权 SELECT）
  2. CRM 链路（辅助标签）：WxWorkerInfo.workerId → compass_data.Worker → Dept
  3. CynosDB WxWorkerInfo（用户查询）：wenxiaofan_rw 分析引擎（TDSQL 分析引擎天然只读）

数据库表映射：
  - WxDepartment    → zhenai_externalContact.WxDepartment（ANALYTICS_DB_RO）
  - WxWorkerInfo    → zhenai_externalContact.WxWorkerInfo（ANALYTICS_DB）
  - Worker          → compass_data.Worker（ANALYTICS_DB）
  - Dept            → compass_data.Dept（ANALYTICS_DB）
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

from config import ANALYTICS_DB, ANALYTICS_DB_RO


class OrgResolver:
    """企微组织架构解析器"""

    def __init__(self):
        self._analytics_conn = None
        self._ro_conn = None  # 仅用于 WxDepartment（表级权限在 ro 账号）
        self._dept_tree: Optional[Dict[int, dict]] = None
        self._crm_dept_map: Optional[Dict[int, str]] = None

    # ── 连接管理 ──────────────────────────────────

    def _get_conn(self):
        """获取分析引擎连接（默认）"""
        if self._analytics_conn is None or not self._analytics_conn.open:
            self._analytics_conn = pymysql.connect(
                host=ANALYTICS_DB["host"],
                port=ANALYTICS_DB["port"],
                user=ANALYTICS_DB["user"],
                password=ANALYTICS_DB["password"],
                charset=ANALYTICS_DB["charset"],
                cursorclass=_LoggingDictCursor,
                connect_timeout=10,
                read_timeout=30,
            )
        return self._analytics_conn

    def _get_ro_conn(self):
        """WxDepartment 专用：wenxiaofan_ro 只读连接"""
        if self._ro_conn is None or not self._ro_conn.open:
            self._ro_conn = pymysql.connect(
                host=ANALYTICS_DB_RO["host"],
                port=ANALYTICS_DB_RO["port"],
                user=ANALYTICS_DB_RO["user"],
                password=ANALYTICS_DB_RO["password"],
                charset=ANALYTICS_DB_RO["charset"],
                cursorclass=_LoggingDictCursor,
                connect_timeout=10,
                read_timeout=30,
            )
        return self._ro_conn

    def close(self):
        if self._analytics_conn and self._analytics_conn.open:
            self._analytics_conn.close()
        self._analytics_conn = None
        if self._ro_conn and self._ro_conn.open:
            self._ro_conn.close()
        self._ro_conn = None

    # ── 部门树 ──────────────────────────────────

    def get_dept_tree(self) -> Dict[int, dict]:
        """加载完整部门树：{dept_id: {name, parentid, children: [id,...]}}"""
        if self._dept_tree is not None:
            return self._dept_tree

        self._dept_tree = self._load_wx_dept_tree()
        return self._dept_tree

    def _load_wx_dept_tree(self) -> Dict[int, dict]:
        """从 Libra 加载企微部门树（经 wenxiaofan_ro 授权 WxDepartment）"""
        conn = self._get_ro_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT deptId, name, parentId "
                "FROM zhenai_externalContact.WxDepartment"
            )
            rows = cur.fetchall()

        tree: Dict[int, dict] = {}
        for r in rows:
            tree[r["deptId"]] = {
                "name": r["name"],
                "parentid": r["parentId"],
                "children": [],
            }

        for dept_id, info in tree.items():
            pid = info["parentid"]
            if pid and pid in tree:
                tree[pid]["children"].append(dept_id)

        return tree

    def get_dept_path(self, dept_id: int) -> str:
        """解析部门全路径：'业务部门 > 呼叫中心 > 深圳网销运营 > 网销一区 > 二部'"""
        tree = self.get_dept_tree()
        parts = []
        current = dept_id
        seen = set()
        while current and current in tree and current not in seen:
            seen.add(current)
            parts.append(tree[current]["name"])
            current = tree[current]["parentid"]
        parts.reverse()
        return " > ".join(parts)

    def get_dept_children(self, dept_id: int) -> List[dict]:
        """获取直接子部门列表"""
        tree = self.get_dept_tree()
        node = tree.get(dept_id)
        if not node:
            return []
        result = []
        for cid in sorted(node["children"]):
            child = tree[cid]
            result.append({
                "id": cid,
                "name": child["name"],
                "child_count": len(child["children"]),
            })
        return result

    def get_top_depts(self) -> List[dict]:
        """获取顶层部门"""
        tree = self.get_dept_tree()
        result = []
        for dept_id, info in tree.items():
            pid = info["parentid"]
            if not pid or pid not in tree:
                result.append({
                    "id": dept_id,
                    "name": info["name"],
                    "child_count": len(info["children"]),
                })
        return sorted(result, key=lambda x: x["id"])

    def search_dept(self, keyword: str) -> List[dict]:
        """按关键字搜索部门（名称模糊匹配）"""
        tree = self.get_dept_tree()
        results = []
        for dept_id, info in tree.items():
            if keyword in info["name"]:
                results.append({
                    "id": dept_id,
                    "name": info["name"],
                    "path": self.get_dept_path(dept_id),
                    "child_count": len(info["children"]),
                })
        return sorted(results, key=lambda x: x["path"])

    # ── CRM 部门（辅助标签） ──────────────────────

    def _resolve_crm_dept(self, crm_worker_id) -> Optional[str]:
        """通过 CRM Worker 表获取部门名"""
        if not crm_worker_id:
            return None
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT d.deptName FROM compass_data.Worker w "
                "JOIN compass_data.Dept d ON w.deptId = d.deptId "
                "WHERE w.workerId = %s",
                (crm_worker_id,)
            )
            row = cur.fetchone()
        return row["deptName"] if row else None

    def list_crm_depts(self, active_only: bool = True) -> List[dict]:
        """列出 CRM 部门"""
        conn = self._get_conn()
        with conn.cursor() as cur:
            sql = "SELECT deptId, deptName, disabled FROM compass_data.Dept"
            if active_only:
                sql += " WHERE disabled = 0"
            sql += " ORDER BY deptName"
            cur.execute(sql)
            return cur.fetchall()

    # ── 用户查询 ──────────────────────────────────

    def resolve_user(self, userid: str) -> Optional[dict]:
        """按企微 userId 查用户详情 + 部门信息"""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT u.userId AS userid, u.name, u.department AS departments, "
                "u.position, u.workStatus AS state, "
                "u.workerId AS crm_worker_id, u.mobile, u.email "
                "FROM zhenai_externalContact.WxWorkerInfo u "
                "WHERE u.userId = %s",
                (userid,)
            )
            row = cur.fetchone()

        if not row:
            return None

        row["state_label"] = "在职" if row["state"] == 1 else "离职"
        row["crm_dept"] = self._resolve_crm_dept(row.get("crm_worker_id"))
        row["wx_dept_paths"] = self._parse_dept_paths(row.get("departments", ""))
        return row

    def search_users(self, keyword: str, active_only: bool = True) -> List[dict]:
        """按姓名模糊搜索用户（带 CRM 部门名 + 企微部门路径）"""
        conn = self._get_conn()
        with conn.cursor() as cur:
            sql = (
                "SELECT u.userId AS userid, u.name, u.department AS departments, "
                "u.position, u.workStatus AS state, "
                "u.workerId AS crm_worker_id, d.deptName AS crm_dept "
                "FROM zhenai_externalContact.WxWorkerInfo u "
                "LEFT JOIN compass_data.Worker w ON u.workerId = w.workerId "
                "LEFT JOIN compass_data.Dept d ON w.deptId = d.deptId "
                "WHERE u.name LIKE %s"
            )
            params = [f"%{keyword}%"]
            if active_only:
                sql += " AND u.workStatus = 1"
            sql += " ORDER BY u.name LIMIT 100"
            cur.execute(sql, params)
            rows = cur.fetchall()

        for r in rows:
            r["state_label"] = "在职" if r["state"] == 1 else "离职"
            r["wx_dept_path"] = self._parse_first_dept_path(r.get("departments", ""))
        return rows

    def list_dept_members(self, dept_id: int, recursive: bool = False) -> List[dict]:
        """通过企微部门 ID 列出成员"""
        if recursive:
            dept_ids = self._collect_sub_depts(dept_id)
        else:
            dept_ids = [dept_id]

        conn = self._get_conn()
        with conn.cursor() as cur:
            conditions = " OR ".join(
                ["FIND_IN_SET(%s, u.department)" for _ in dept_ids]
            )
            sql = (
                "SELECT u.userId AS userid, u.name, u.department AS departments, "
                "u.position, u.workStatus AS state, "
                "u.workerId AS crm_worker_id, d.deptName AS crm_dept "
                "FROM zhenai_externalContact.WxWorkerInfo u "
                "LEFT JOIN compass_data.Worker w ON u.workerId = w.workerId "
                "LEFT JOIN compass_data.Dept d ON w.deptId = d.deptId "
                f"WHERE ({conditions}) AND u.workStatus = 1 "
                "ORDER BY u.name"
            )
            cur.execute(sql, dept_ids)
            rows = cur.fetchall()

        for r in rows:
            r["state_label"] = "在职" if r["state"] == 1 else "离职"
        return rows

    def list_crm_dept_members(self, dept_id: int) -> List[dict]:
        """通过 CRM deptId 列出部门成员"""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT u.userId AS userid, u.name, u.position, "
                "u.workStatus AS state, d.deptName AS crm_dept "
                "FROM zhenai_externalContact.WxWorkerInfo u "
                "JOIN compass_data.Worker w ON u.workerId = w.workerId "
                "JOIN compass_data.Dept d ON w.deptId = d.deptId "
                "WHERE w.deptId = %s AND u.workStatus = 1 "
                "ORDER BY u.name",
                (dept_id,)
            )
            rows = cur.fetchall()

        for r in rows:
            r["state_label"] = "在职" if r["state"] == 1 else "离职"
        return rows

    # ── 内部方法 ──────────────────────────────────

    def _parse_dept_paths(self, departments_str: str) -> List[str]:
        """将逗号分隔的部门ID解析为部门路径列表"""
        if not departments_str:
            return []
        paths = []
        for part in str(departments_str).split(","):
            part = part.strip()
            if part.isdigit():
                path = self.get_dept_path(int(part))
                if path:
                    paths.append(path)
        return paths

    def _parse_first_dept_path(self, departments_str: str) -> str:
        """解析第一个部门ID为路径（用于列表展示）"""
        if not departments_str:
            return ""
        part = str(departments_str).split(",")[0].strip()
        if part.isdigit():
            return self.get_dept_path(int(part))
        return ""

    def _collect_sub_depts(self, dept_id: int) -> List[int]:
        """递归收集某部门及其所有子部门 ID"""
        tree = self.get_dept_tree()
        result = [dept_id]
        queue = [dept_id]
        while queue:
            current = queue.pop(0)
            node = tree.get(current)
            if node:
                for cid in node["children"]:
                    result.append(cid)
                    queue.append(cid)
        return result
