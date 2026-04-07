#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据反馈客户端 — 本地存储 + 远程 API 提交 + 离线重试。

所有 Skill 共用同一份代码（与 auth_guard.py 同模式）。
零额外依赖，仅使用 Python 标准库。
"""

from __future__ import annotations

import hashlib
import json
import os
import smtplib
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _print_safe(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("utf-8", errors="replace").decode("ascii", errors="replace"))


_API_URL = os.environ.get("ZHENAI_API_URL", "")  # 远程同步为可选，留空则仅本地+邮件
_FEEDBACK_DIR = Path.home() / ".zhenai-skills" / "feedback"
_TIMEOUT = 10
_TZ_CST = timezone(timedelta(hours=8))


# ── 本地存储 ──────────────────────────────────────


def _ensure_dir():
    _FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)


def _generate_id() -> str:
    date_part = datetime.now(_TZ_CST).strftime("%Y%m%d")
    uid_part = uuid.uuid4().hex[:6]
    return f"FB-{date_part}-{uid_part}"


def _save_local(feedback: dict) -> Path:
    _ensure_dir()
    path = _FEEDBACK_DIR / f"{feedback['feedback_id']}.json"
    path.write_text(
        json.dumps(feedback, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def _load_local(feedback_id: str) -> dict | None:
    path = _FEEDBACK_DIR / f"{feedback_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _list_local(limit: int = 20, status_filter: str = None) -> list[dict]:
    _ensure_dir()
    files = sorted(_FEEDBACK_DIR.glob("FB-*.json"), reverse=True)
    results = []
    for f in files:
        if len(results) >= limit:
            break
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if status_filter and data.get("status") != status_filter:
                continue
            results.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return results


# ── 远程 API ──────────────────────────────────────


def _get_api_key() -> str | None:
    key = os.environ.get("ZHENAI_API_KEY", "").strip()
    if key:
        return key
    key_file = Path.home() / ".zhenai-skills" / "api_key"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip() or None
    return None


def _get_cached_user() -> dict | None:
    """从本地 auth_guard 获取当前用户信息（优先），回退到旧缓存文件。"""
    try:
        from auth_guard import require_auth
        user = require_auth(allow_skip=True)
        if user:
            return user
    except Exception:
        pass

    cache_file = Path.home() / ".zhenai-skills" / ".auth_cache"
    if not cache_file.exists():
        return None
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        return data.get("user")
    except (json.JSONDecodeError, OSError):
        return None


def _post_remote(feedback: dict) -> dict | None:
    """POST 反馈到 zhenai-api，成功返回响应 dict，失败返回 None。
    当 _API_URL 未配置时直接返回 None（仅本地+邮件模式）。
    """
    if not _API_URL:
        return None
    api_key = _get_api_key()
    if not api_key:
        return None

    url = f"{_API_URL.rstrip('/')}/feedback"
    body = json.dumps(feedback, ensure_ascii=False).encode("utf-8")
    req = Request(
        url,
        data=body,
        headers={
            "X-API-Key": api_key,
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, OSError):
        return None


def _get_remote(path: str) -> dict | None:
    if not _API_URL:
        return None
    api_key = _get_api_key()
    if not api_key:
        return None

    url = f"{_API_URL.rstrip('/')}{path}"
    req = Request(url, headers={"X-API-Key": api_key})
    try:
        with urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, OSError):
        return None


def _load_smtp_config() -> dict | None:
    cfg_path = Path.home() / ".zhenai-skills" / "smtp_config.json"
    if not cfg_path.exists():
        return None
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


_SEVERITY_LABELS = {"high": "🔴 高", "medium": "🟡 中", "low": "🟢 低"}
_TYPE_LABELS = {
    "data_inaccuracy": "数据不准确",
    "missing_data": "数据缺失",
    "data_delay": "数据延迟",
    "other": "其他",
}


def _build_email_html(feedback: dict) -> str:
    issue = feedback.get("issue", {})
    ctx = feedback.get("query_context", {})
    submitter = feedback.get("submitted_by", {})
    severity = _SEVERITY_LABELS.get(issue.get("severity", ""), issue.get("severity", ""))
    issue_type = _TYPE_LABELS.get(issue.get("type", ""), issue.get("type", ""))

    return f"""\
<div style="font-family:'Microsoft YaHei',Helvetica,Arial,sans-serif;max-width:640px;margin:0 auto">
  <div style="background:#e74c3c;color:#fff;padding:16px 24px;border-radius:8px 8px 0 0">
    <h2 style="margin:0;font-size:18px">📋 数据反馈通知 — {feedback.get('feedback_id','')}</h2>
  </div>
  <div style="border:1px solid #ddd;border-top:none;padding:20px 24px;border-radius:0 0 8px 8px">
    <table style="width:100%;border-collapse:collapse;font-size:14px;line-height:1.8">
      <tr><td style="color:#888;width:100px;padding:4px 0">反馈ID</td>
          <td style="font-weight:bold">{feedback.get('feedback_id','')}</td></tr>
      <tr><td style="color:#888;padding:4px 0">提交人</td>
          <td>{submitter.get('name','未知')} ({submitter.get('sub','')})</td></tr>
      <tr><td style="color:#888;padding:4px 0">Skill</td>
          <td>{feedback.get('skill_name','')}</td></tr>
      <tr><td style="color:#888;padding:4px 0">严重程度</td>
          <td>{severity}</td></tr>
      <tr><td style="color:#888;padding:4px 0">问题类型</td>
          <td>{issue_type}</td></tr>
      <tr><td style="color:#888;padding:4px 0">数据表</td>
          <td><code>{ctx.get('database','')}.{ctx.get('table','')}</code></td></tr>
    </table>
    <hr style="border:none;border-top:1px solid #eee;margin:16px 0">
    <p style="font-size:14px"><b>问题描述：</b><br>{issue.get('description','')}</p>
    <p style="font-size:14px"><b>期望值：</b>{issue.get('expected_value','—')}</p>
    <p style="font-size:14px"><b>实际值：</b>{issue.get('actual_value','—')}</p>
    {f'<div style="background:#f7f7f7;padding:12px;border-radius:4px;margin-top:12px"><b>SQL：</b><br><code style="font-size:12px;word-break:break-all">{ctx.get("sql","")}</code></div>' if ctx.get("sql") else ""}
    <p style="font-size:12px;color:#aaa;margin-top:20px">提交时间：{feedback.get('created_at','')} | 此邮件由 Skill 数据反馈系统自动发送</p>
  </div>
</div>"""


def _send_email_notification(feedback: dict) -> bool:
    """通过 SMTP 发送反馈邮件通知。成功返回 True。"""
    cfg = _load_smtp_config()
    if not cfg:
        return False

    issue = feedback.get("issue", {})
    severity_tag = {"high": "🔴高", "medium": "🟡中", "low": "🟢低"}.get(
        issue.get("severity", ""), ""
    )
    subject = (
        f"[数据反馈{severity_tag}] {feedback.get('feedback_id','')} — "
        f"{issue.get('description','')[:60]}"
    )

    msg = MIMEMultipart("alternative")
    msg["From"] = cfg["sender"]
    msg["To"] = ", ".join(cfg.get("recipients", []))
    cc_list = [c["email"] for c in cfg.get("cc", []) if c.get("email")]
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg["Subject"] = Header(subject, "utf-8")
    msg.attach(MIMEText(_build_email_html(feedback), "html", "utf-8"))

    all_recipients = cfg.get("recipients", []) + cc_list

    try:
        if cfg.get("smtp_ssl", True):
            server = smtplib.SMTP_SSL(cfg["smtp_host"], cfg.get("smtp_port", 465), timeout=15)
        else:
            server = smtplib.SMTP(cfg["smtp_host"], cfg.get("smtp_port", 587), timeout=15)
            server.starttls()
        server.login(cfg["sender"], cfg["password"])
        server.sendmail(cfg["sender"], all_recipients, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        _print_safe(f"[WARN] 邮件发送失败: {e}")
        return False


def _retry_pending():
    """尝试重新提交本地标记为 sync_pending 的反馈。"""
    _ensure_dir()
    for f in _FEEDBACK_DIR.glob("FB-*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("sync_status") != "sync_pending":
            continue
        result = _post_remote(data)
        if result:
            data["sync_status"] = "synced"
            _save_local(data)
            continue
        if _send_email_notification(data):
            data["sync_status"] = "email_sent"
            _save_local(data)


# ── 公开 API ──────────────────────────────────────


def submit_feedback(
    skill_name: str,
    table: str,
    description: str,
    issue_type: str = "data_inaccuracy",
    expected_value: str = None,
    actual_value: str = None,
    severity: str = "medium",
    sql: str = None,
    database: str = None,
    command: str = None,
) -> str:
    """提交数据反馈。返回 feedback_id。

    本地存储 + 远程 POST 双写。远程失败时标记 sync_pending，下次自动重试。
    """
    _retry_pending()

    feedback_id = _generate_id()
    now = datetime.now(_TZ_CST).isoformat()

    user = _get_cached_user() or {}
    submitted_by = {
        "sub": user.get("sub", "unknown"),
        "name": user.get("name", "unknown"),
    }

    feedback = {
        "feedback_id": feedback_id,
        "skill_name": skill_name,
        "submitted_by": submitted_by,
        "query_context": {
            "command": command or "",
            "sql": sql or "",
            "database": database or "",
            "table": table,
        },
        "issue": {
            "type": issue_type,
            "description": description,
            "expected_value": expected_value or "",
            "actual_value": actual_value or "",
            "severity": severity,
        },
        "created_at": now,
        "status": "pending",
        "resolution": None,
        "sync_status": "sync_pending",
    }

    _save_local(feedback)

    result = _post_remote(feedback)
    if result:
        feedback["sync_status"] = "synced"
        _save_local(feedback)
        return feedback_id

    if _send_email_notification(feedback):
        feedback["sync_status"] = "email_sent"
        _save_local(feedback)

    return feedback_id


def list_feedback(limit: int = 20, status_filter: str = None) -> list[dict]:
    """查询已提交的反馈列表。优先远程，失败回退本地。"""
    params = f"?limit={limit}"
    if status_filter:
        params += f"&status={status_filter}"
    remote = _get_remote(f"/feedback{params}")
    if remote and isinstance(remote, list):
        return remote

    return _list_local(limit=limit, status_filter=status_filter)


def get_feedback_status(feedback_id: str) -> dict | None:
    """查询单条反馈状态。优先远程，失败回退本地。"""
    remote = _get_remote(f"/feedback/{feedback_id}")
    if remote:
        return remote

    return _load_local(feedback_id)
