#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企航SCRM API 客户端
Token-based 认证，通过 QR 登录获取 token，持久化到 ~/.analysis-data-service/token.json
"""
import json
import sys
import time
from datetime import datetime
from typing import List, Dict, Optional

import requests

from config import BASE_URL, TOKEN_PATH, REQUEST_INTERVAL, DEFAULT_PAGE_SIZE, REQUEST_TIMEOUT


class SCRMClient:
    """企航SCRM HTTP API 客户端"""

    def __init__(self, token: str):
        self.token = token
        self.base_url = BASE_URL

    # ── 工厂方法 ──────────────────────────────────

    @classmethod
    def from_saved_token(cls) -> Optional['SCRMClient']:
        """从磁盘加载 token 并验证有效性"""
        if not TOKEN_PATH.exists():
            return None
        try:
            data = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
            token = data.get("token", "").strip()
            if not token:
                return None
            client = cls(token)
            if client._validate_token():
                return client
            return None
        except (json.JSONDecodeError, KeyError, IOError):
            return None

    @staticmethod
    def save_token(token: str):
        """持久化 token"""
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(json.dumps({
            "token": token,
            "saved_at": datetime.now().isoformat(),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 内部方法 ──────────────────────────────────

    def _validate_token(self) -> bool:
        """轻量级 token 有效性检查"""
        try:
            resp = requests.post(
                f"{self.base_url}/workapi/sessionArchive/getArchiveUser",
                params={"token": self.token},
                headers=self._HEADERS,
                json={"workStatus": 1, "pageSize": 1, "pageNo": 0},
                timeout=10,
            )
            return resp.status_code != 403
        except requests.RequestException:
            return False

    # SCRM API 必需的请求头（zone: ccm 缺失会导致部分接口返回空数据）
    _HEADERS = {
        "Origin": "https://call-workweixin.zhenai.com",
        "Referer": "https://call-workweixin.zhenai.com/",
        "X-Requested-With": "XMLHttpRequest",
        "zone": "ccm",
    }

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """统一请求：自动注入 token + zone header，403 时提示重新登录"""
        params = kwargs.pop("params", {})
        params["token"] = self.token

        # 合并必需 header
        headers = {**self._HEADERS, **kwargs.pop("headers", {})}

        resp = getattr(requests, method)(
            f"{self.base_url}{path}",
            params=params,
            headers=headers,
            timeout=kwargs.pop("timeout", REQUEST_TIMEOUT),
            **kwargs,
        )

        if resp.status_code == 403:
            print("❌ Token 已过期 (HTTP 403)，请重新执行: python3 handler.py login")
            sys.exit(1)

        resp.raise_for_status()
        return resp.json()

    def _paginate(self, method: str, path: str,
                  page_size: int = DEFAULT_PAGE_SIZE,
                  body: dict = None, extra_params: dict = None) -> List[Dict]:
        """通用分页拉取（pageNo 从 0 开始）"""
        all_items: List[Dict] = []
        page = 0
        while True:
            if method == "post":
                payload = {**(body or {}), "pageSize": page_size, "pageNo": page}
                data = self._request("post", path, json=payload)
            else:
                p = {**(extra_params or {}), "pageSize": page_size, "pageNo": page}
                data = self._request("get", path, params=p)

            batch = data.get("data", [])
            if not batch:
                break
            all_items.extend(batch)
            total = data.get("count", 0)
            if total and len(all_items) >= total:
                break
            page += 1
            time.sleep(REQUEST_INTERVAL)
        return all_items

    # ── 公开 API ──────────────────────────────────

    def get_archive_users(self, work_status: int = 1,
                          search: str = None) -> List[Dict]:
        """获取员工列表。search 按姓名/userId 搜索（accountInfo 参数）"""
        body = {"workStatus": work_status}
        if search:
            body["accountInfo"] = search
        return self._paginate("post",
            "/workapi/sessionArchive/getArchiveUser",
            body=body)

    def get_sessions(self, worker_userid: str, session_type: int = 1) -> List[Dict]:
        """获取会话列表 (sessionType: 0=外部私聊, 1=群聊)"""
        return self._paginate("get",
            "/workapi/sessionArchive/getArchiveSession",
            extra_params={
                "wxWorkerUserid": worker_userid,
                "sessionType": session_type,
                "reply": 2,
            })

    def get_inner_sessions(self, worker_userid: str) -> List[Dict]:
        """获取内部员工会话列表"""
        return self._paginate("get",
            "/workapi/sessionArchive/getInnerArchiveSession",
            extra_params={"wxWorkerUserid": worker_userid})

    def get_messages(self, worker_userid: str, customer_userid: str,
                     session_type: int = 1,
                     page_size: int = DEFAULT_PAGE_SIZE) -> List[Dict]:
        """分页获取聊天消息"""
        return self._paginate("get",
            "/workapi/sessionArchive/pageMsgRecord",
            page_size=page_size,
            extra_params={
                "sessionType": session_type,
                "accountId": worker_userid,
                "userId": customer_userid,
                "clientType": 1,
            })

    def search_message_context(self, session_type: int, account_id: str,
                               user_id: str, msg_id: str,
                               before_count: int = 10,
                               after_count: int = 10) -> List[Dict]:
        """搜索消息上下文"""
        data = self._request("get",
            "/workapi/sessionArchive/searchMsgContextRecord",
            params={
                "sessionType": session_type,
                "accountId": account_id,
                "userId": user_id,
                "msgId": msg_id,
                "clientType": 1,
                "beforeCount": before_count,
                "afterCount": after_count,
            })
        return data.get("data", [])

    def get_room_members(self, room_id: str) -> List[Dict]:
        """获取群成员列表"""
        data = self._request("get",
            "/workapi/aggregateChat/getRoomMember",
            params={"roomId": room_id})
        return data.get("data", [])

    def get_friend_remark(self, worker_userid: str, customer_userid: str) -> Dict:
        """获取客户备注信息"""
        return self._request("get",
            "/workapi/aggregateChat/getFriendRemark",
            params={
                "wxWorkerUserid": worker_userid,
                "wxCustomerUserid": customer_userid,
            })

    def get_companies(self) -> List[Dict]:
        """获取企业列表（含 sid/corpId）"""
        data = self._request("get",
            "/workapi/companyInfoController/query",
            params={"pageSize": 999, "pageNo": 0})
        return data.get("list", [])

    def get_department_tree(self, corp_sid: str = None) -> List[Dict]:
        """获取企微部门树（嵌套结构）。corp_sid 为空时自动选择珍爱网"""
        if not corp_sid:
            corp_sid = self._resolve_zhenai_sid()
        if not corp_sid:
            return []
        data = self._request("get",
            "/workapi/WxDepartment/getDepartmentList",
            params={"corpId": corp_sid})
        return data.get("data", [])

    def get_department_workers(self, dept_id: int) -> List[Dict]:
        """获取部门下的员工列表"""
        data = self._request("get",
            "/workapi/WxDepartment/getDepartmentWorkerList",
            params={"departmentId": dept_id})
        return data.get("data", [])

    def _resolve_zhenai_sid(self) -> Optional[str]:
        """自动查找珍爱网的 corp sid"""
        companies = self.get_companies()
        for c in companies:
            if c.get("name") == "珍爱网":
                return c["sid"]
        # 回退：选员工数最多的
        if companies:
            best = max(companies, key=lambda x: x.get("num", 0))
            return best.get("sid")
        return None

    def get_token_info(self) -> Dict:
        """返回 token 摘要（脱敏）"""
        saved = {}
        if TOKEN_PATH.exists():
            try:
                saved = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "token_preview": f"{self.token[:8]}...{self.token[-4:]}",
            "saved_at": saved.get("saved_at", "unknown"),
            "valid": self._validate_token(),
        }
