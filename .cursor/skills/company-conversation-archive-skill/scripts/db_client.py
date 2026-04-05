#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话存档 MySQL 数据客户端
直接从腾讯云 MySQL 读取会话存档和组织架构数据
"""
from datetime import datetime
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
    DB_CONFIG, DB_CONFIG_RO, DB_ARCHIVE,
    TABLE_ARCHIVE_RECENT, TABLE_ARCHIVE_FULL,
    DEFAULT_PAGE_SIZE,
    DB_COMPASS, TABLE_WORKER, TABLE_DEPT,
    DB_WX, TABLE_WX_WORKER, CORP_SID,
    EMPLOYEE_TYPES, TEAM_ALIASES, email_to_wxid,
)


SENSITIVE_COLUMNS = frozenset({"msg", "audioText"})

SAFE_SELECT = (
    "id, wxid, wxidFrom, wxidTo, msgType, msgTimestamp, "
    "roomWxid, msgAction, linkTitle, linkUrl, fileName, createTime"
)


class DBClient:
    """会话存档数据库客户端"""

    def __init__(self, use_full_archive: bool = False, can_view_sensitive: bool = False):
        self._conn = None
        self._ro_conn = None
        self._wxid_cache: Optional[Dict[str, str]] = None
        self._can_view_sensitive = can_view_sensitive
        self._archive_table = (
            f"{DB_ARCHIVE}.{TABLE_ARCHIVE_FULL}" if use_full_archive
            else f"{DB_ARCHIVE}.{TABLE_ARCHIVE_RECENT}"
        )

    def _get_conn(self):
        """CRM/组织架构表使用的 RW 连接"""
        if self._conn is None or not self._conn.open:
            self._conn = pymysql.connect(
                **DB_CONFIG,
                cursorclass=_LoggingDictCursor,
                connect_timeout=15,
                read_timeout=60,
            )
        return self._conn

    def _get_ro_conn(self):
        """会话存档表使用的 RO 连接"""
        if self._ro_conn is None or not self._ro_conn.open:
            self._ro_conn = pymysql.connect(
                **DB_CONFIG_RO,
                cursorclass=_LoggingDictCursor,
                connect_timeout=15,
                read_timeout=60,
            )
        return self._ro_conn

    def close(self):
        if self._conn and self._conn.open:
            self._conn.close()
            self._conn = None
        if self._ro_conn and self._ro_conn.open:
            self._ro_conn.close()
            self._ro_conn = None

    def test_connection(self) -> bool:
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            ro_conn = self._get_ro_conn()
            with ro_conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except Exception as e:
            print(f"[ERR] 数据库连接测试失败: {e}")
            self.close()
            return False

    # ── wxid 桥接解析（通过 WxWorkerInfo 获取真实企微 userId） ──

    def resolve_real_wxids(self, emails: List[str] = None) -> Dict[str, str]:
        """通过 WxWorkerInfo 将 CRM 邮箱批量映射为真实企微 userId。
        返回 {email: userId} 字典。
        若不传 emails 则加载全量映射并缓存。
        """
        if emails is None and self._wxid_cache is not None:
            return self._wxid_cache

        conn = self._get_conn()
        with conn.cursor() as cur:
            if emails:
                ph = ",".join(["%s"] * len(emails))
                cur.execute(
                    f"SELECT email, userId FROM {DB_WX}.{TABLE_WX_WORKER} "
                    f"WHERE sid = %s AND email IN ({ph}) "
                    f"AND workStatus = 1",
                    [CORP_SID] + list(emails),
                )
            else:
                cur.execute(
                    f"SELECT email, userId FROM {DB_WX}.{TABLE_WX_WORKER} "
                    f"WHERE sid = %s AND workStatus = 1 "
                    f"AND email IS NOT NULL AND email != ''",
                    (CORP_SID,),
                )
            rows = cur.fetchall()

        result = {r["email"]: r["userId"] for r in rows if r.get("email")}

        if emails is None:
            self._wxid_cache = result

        return result

    def _get_wxid_map(self) -> Dict[str, str]:
        """获取或加载 wxid 映射缓存"""
        if self._wxid_cache is None:
            self.resolve_real_wxids()
        return self._wxid_cache or {}

    @staticmethod
    def _enrich_worker(row: Dict, wxid_map: Dict[str, str] = None) -> Dict:
        """为员工记录添加 wxid 和状态标签"""
        row["status_label"] = "在职" if row.get("dimissionDate") is None else "离职"
        email = row.get("email") or ""
        if wxid_map and email in wxid_map:
            row["wxid"] = wxid_map[email]
        else:
            row["wxid"] = email_to_wxid(email)
        return row

    # ── 员工查询（CRM 组织架构） ──────────────────────

    def get_workers(self, active_only: bool = True, search: str = None,
                    dept_id: int = None, limit: int = 200) -> List[Dict]:
        """获取员工列表，支持按姓名搜索、按部门筛选"""
        conn = self._get_conn()
        wxid_map = self._get_wxid_map()
        with conn.cursor() as cur:
            sql = (
                f"SELECT w.workerId, w.workerName, w.email, w.deptId, w.groupId, "
                f"w.phoneNumber, w.joinDate, w.dimissionDate, w.workerStatus, "
                f"w.skill, w.brandId, d.deptName "
                f"FROM {DB_COMPASS}.{TABLE_WORKER} w "
                f"LEFT JOIN {DB_COMPASS}.{TABLE_DEPT} d ON w.deptId = d.deptId "
                f"WHERE 1=1"
            )
            params = []
            if active_only:
                sql += " AND w.workerStatus = 1 AND w.dimissionDate IS NULL"
            if search:
                sql += " AND (w.workerName LIKE %s OR CAST(w.workerId AS CHAR) = %s)"
                params.extend([f"%{search}%", search])
            if dept_id is not None:
                sql += " AND w.deptId = %s"
                params.append(dept_id)
            sql += f" ORDER BY w.workerName LIMIT {limit}"
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [self._enrich_worker(r, wxid_map) for r in rows]

    def get_worker_by_id(self, worker_id: int) -> Optional[Dict]:
        """按工号查询员工详情"""
        conn = self._get_conn()
        wxid_map = self._get_wxid_map()
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT w.*, d.deptName "
                f"FROM {DB_COMPASS}.{TABLE_WORKER} w "
                f"LEFT JOIN {DB_COMPASS}.{TABLE_DEPT} d ON w.deptId = d.deptId "
                f"WHERE w.workerId = %s",
                (worker_id,),
            )
            row = cur.fetchone()
        if row:
            self._enrich_worker(row, wxid_map)
        return row

    # ── 部门查询 ──────────────────────────────────

    def get_depts(self, active_only: bool = True) -> List[Dict]:
        """获取部门列表"""
        conn = self._get_conn()
        with conn.cursor() as cur:
            sql = f"SELECT * FROM {DB_COMPASS}.{TABLE_DEPT}"
            if active_only:
                sql += " WHERE disabled = 0"
            sql += " ORDER BY deptName"
            cur.execute(sql)
            return cur.fetchall()

    def get_dept_by_id(self, dept_id: int) -> Optional[Dict]:
        """按 ID 查部门"""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT * FROM {DB_COMPASS}.{TABLE_DEPT} WHERE deptId = %s",
                (dept_id,),
            )
            return cur.fetchone()

    def get_dept_members(self, dept_id: int, active_only: bool = True) -> List[Dict]:
        """列出部门成员"""
        return self.get_workers(active_only=active_only, dept_id=dept_id, limit=1000)

    # ── 按员工类型查询 ──────────────────────────────

    def get_employees_by_type(
        self, employee_type: str, active_only: bool = True, search: str = None
    ) -> List[Dict]:
        """按员工类型（电销/电红/网销/建信）或团队别名查询员工列表，返回带真实 wxid。"""
        resolved_type = TEAM_ALIASES.get(employee_type, employee_type)
        type_config = EMPLOYEE_TYPES.get(resolved_type)
        if not type_config:
            return []
        conn = self._get_conn()
        wxid_map = self._get_wxid_map()
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
            if search:
                sql += " AND w.workerName LIKE %s"
                params.append(f"%{search}%")
            sql += " ORDER BY d.deptName, w.workerName"
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [self._enrich_worker(r, wxid_map) for r in rows]

    # ── 会话查询（纯存档表，不依赖 CRM） ──────────────

    def get_archive_users(self, search: str = None) -> List[Dict]:
        """获取有会话存档记录的员工列表（仅从存档表提取 wxid/userId）。"""
        conn = self._get_ro_conn()
        with conn.cursor() as cur:
            sql = (
                f"SELECT DISTINCT a.wxid, a.userId "
                f"FROM {self._archive_table} a "
                f"WHERE a.wxid IS NOT NULL AND a.wxid != '' "
            )
            params = []
            if search:
                sql += " AND (a.wxid LIKE %s OR a.userId LIKE %s)"
                params.extend([f"%{search}%", f"%{search}%"])
            sql += " LIMIT 500"
            cur.execute(sql, params)
            rows = cur.fetchall()
        return rows

    def get_sessions(self, wxid: str, session_type: str = "external") -> List[Dict]:
        """获取员工的会话列表
        session_type: 'external' (外部私聊/群聊), 'group' (群聊), 'private' (私聊)
        """
        conn = self._get_ro_conn()
        with conn.cursor() as cur:
            if session_type == "group":
                sql = (
                    f"SELECT roomWxid as chatId, "
                    f"MAX(msgTimestamp) as lastMsgTime, COUNT(*) as msgCount "
                    f"FROM {self._archive_table} "
                    f"WHERE wxid = %s AND roomWxid != '' "
                    f"GROUP BY roomWxid ORDER BY lastMsgTime DESC LIMIT 100"
                )
                cur.execute(sql, (wxid,))
            elif session_type == "private":
                sql = (
                    f"SELECT chatGroup as chatId, wxidTo, "
                    f"MAX(msgTimestamp) as lastMsgTime, COUNT(*) as msgCount "
                    f"FROM {self._archive_table} "
                    f"WHERE wxid = %s AND (roomWxid = '' OR roomWxid IS NULL) "
                    f"GROUP BY chatGroup, wxidTo ORDER BY lastMsgTime DESC LIMIT 100"
                )
                cur.execute(sql, (wxid,))
            else:
                sql = (
                    f"SELECT chatGroup as chatId, roomWxid, "
                    f"MAX(msgTimestamp) as lastMsgTime, COUNT(*) as msgCount "
                    f"FROM {self._archive_table} "
                    f"WHERE wxid = %s "
                    f"GROUP BY chatGroup, roomWxid ORDER BY lastMsgTime DESC LIMIT 200"
                )
                cur.execute(sql, (wxid,))

            rows = cur.fetchall()

        for r in rows:
            ts = r.get("lastMsgTime", 0)
            if ts and ts > 0:
                r["lastMsgTimeStr"] = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M")
            else:
                r["lastMsgTimeStr"] = ""
        return rows

    def count_messages(self, wxid: str = None, date: str = None) -> int:
        """统计消息数量"""
        conn = self._get_ro_conn()
        with conn.cursor() as cur:
            sql = f"SELECT COUNT(*) as cnt FROM {self._archive_table} WHERE 1=1"
            params = []

            if wxid:
                sql += " AND wxid = %s"
                params.append(wxid)

            if date:
                start_ts = int(datetime.strptime(date, "%Y-%m-%d").timestamp() * 1000)
                end_ts = start_ts + 86400000
                sql += " AND msgTimestamp >= %s AND msgTimestamp < %s"
                params.extend([start_ts, end_ts])

            cur.execute(sql, params)
            return cur.fetchone()["cnt"]

    # ── 统计分析（纯聚合，不返回任何消息内容） ─────────

    def get_message_type_stats(self, wxid: str = None,
                               date: str = None,
                               date_start: str = None,
                               date_end: str = None) -> List[Dict]:
        """按消息类型统计数量分布"""
        conn = self._get_ro_conn()
        with conn.cursor() as cur:
            sql = (
                f"SELECT msgType, COUNT(*) AS cnt "
                f"FROM {self._archive_table} WHERE 1=1"
            )
            params = self._build_time_params(sql, date, date_start, date_end, wxid)
            sql = params.pop("sql")
            cur.execute(sql + " GROUP BY msgType ORDER BY cnt DESC", params.pop("params"))
            return cur.fetchall()

    def get_daily_activity(self, wxid: str = None,
                           date_start: str = None,
                           date_end: str = None) -> List[Dict]:
        """按天统计消息数量趋势"""
        conn = self._get_ro_conn()
        with conn.cursor() as cur:
            sql = (
                f"SELECT DATE(FROM_UNIXTIME(msgTimestamp/1000)) AS msg_date, "
                f"COUNT(*) AS cnt "
                f"FROM {self._archive_table} WHERE 1=1"
            )
            params = self._build_time_params(sql, None, date_start, date_end, wxid)
            sql = params.pop("sql")
            cur.execute(sql + " GROUP BY msg_date ORDER BY msg_date", params.pop("params"))
            return cur.fetchall()

    def get_hourly_activity(self, wxid: str = None,
                            date: str = None,
                            date_start: str = None,
                            date_end: str = None) -> List[Dict]:
        """按小时统计消息分布"""
        conn = self._get_ro_conn()
        with conn.cursor() as cur:
            sql = (
                f"SELECT HOUR(FROM_UNIXTIME(msgTimestamp/1000)) AS msg_hour, "
                f"COUNT(*) AS cnt "
                f"FROM {self._archive_table} WHERE 1=1"
            )
            params = self._build_time_params(sql, date, date_start, date_end, wxid)
            sql = params.pop("sql")
            cur.execute(sql + " GROUP BY msg_hour ORDER BY msg_hour", params.pop("params"))
            return cur.fetchall()

    def get_sender_stats(self, wxid: str = None,
                         date: str = None,
                         date_start: str = None,
                         date_end: str = None,
                         limit: int = 50) -> List[Dict]:
        """按发送人统计消息数量"""
        conn = self._get_ro_conn()
        with conn.cursor() as cur:
            sql = (
                f"SELECT COALESCE(NULLIF(roomSenderWxid,''), wxidFrom) AS sender, "
                f"COUNT(*) AS cnt "
                f"FROM {self._archive_table} WHERE 1=1"
            )
            params = self._build_time_params(sql, date, date_start, date_end, wxid)
            sql = params.pop("sql")
            cur.execute(
                sql + f" GROUP BY sender ORDER BY cnt DESC LIMIT {limit}",
                params.pop("params"),
            )
            return cur.fetchall()

    def get_session_stats(self, wxid: str,
                          date: str = None,
                          date_start: str = None,
                          date_end: str = None) -> List[Dict]:
        """按会话统计消息数量"""
        conn = self._get_ro_conn()
        with conn.cursor() as cur:
            sql = (
                f"SELECT chatGroup AS chat_id, roomWxid, COUNT(*) AS cnt, "
                f"MIN(msgTimestamp) AS first_msg, MAX(msgTimestamp) AS last_msg "
                f"FROM {self._archive_table} WHERE wxid = %s"
            )
            p = [wxid]
            if date:
                start_ts = int(datetime.strptime(date, "%Y-%m-%d").timestamp() * 1000)
                end_ts = start_ts + 86400000
                sql += " AND msgTimestamp >= %s AND msgTimestamp < %s"
                p.extend([start_ts, end_ts])
            elif date_start or date_end:
                if date_start:
                    start_ts = int(datetime.strptime(date_start, "%Y-%m-%d").timestamp() * 1000)
                    sql += " AND msgTimestamp >= %s"
                    p.append(start_ts)
                if date_end:
                    end_ts = int(datetime.strptime(date_end, "%Y-%m-%d").timestamp() * 1000) + 86400000
                    sql += " AND msgTimestamp < %s"
                    p.append(end_ts)
            cur.execute(
                sql + " GROUP BY chatGroup, roomWxid ORDER BY cnt DESC LIMIT 100", p
            )
            rows = cur.fetchall()
        for r in rows:
            for key in ("first_msg", "last_msg"):
                ts = r.get(key, 0)
                if ts and ts > 0:
                    r[f"{key}_str"] = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M")
        return rows

    def _build_time_params(self, sql: str, date: str = None,
                           date_start: str = None, date_end: str = None,
                           wxid: str = None) -> Dict:
        """构建时间和 wxid 过滤参数"""
        params = []
        if wxid:
            sql += " AND wxid = %s"
            params.append(wxid)
        if date:
            start_ts = int(datetime.strptime(date, "%Y-%m-%d").timestamp() * 1000)
            end_ts = start_ts + 86400000
            sql += " AND msgTimestamp >= %s AND msgTimestamp < %s"
            params.extend([start_ts, end_ts])
        else:
            if date_start:
                start_ts = int(datetime.strptime(date_start, "%Y-%m-%d").timestamp() * 1000)
                sql += " AND msgTimestamp >= %s"
                params.append(start_ts)
            if date_end:
                end_ts = int(datetime.strptime(date_end, "%Y-%m-%d").timestamp() * 1000) + 86400000
                sql += " AND msgTimestamp < %s"
                params.append(end_ts)
        return {"sql": sql, "params": params}
