#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API Key 鉴权守卫 — 本地校验，从 auth_config.json 读取用户与权限。"""

import json
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_CONFIG_FILE = _SCRIPT_DIR / "auth_config.json"

_config_cache = None
_api_key_index = None


def _print_safe(msg):
    """Windows GBK 终端兼容的打印。"""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("utf-8", errors="replace").decode("ascii", errors="replace"))


def _load_config():
    """加载 auth_config.json 并缓存。"""
    global _config_cache, _api_key_index
    if _config_cache is not None:
        return _config_cache

    if not _CONFIG_FILE.exists():
        return None

    try:
        data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    _config_cache = data

    _api_key_index = {}
    for username, user_data in data.get("users", {}).items():
        key = user_data.get("api_key", "")
        if key:
            _api_key_index[key] = (username, user_data)

    return data


def _get_api_key():
    """按优先级读取 API Key：环境变量 > 本地文件。"""
    key = os.environ.get("ZHENAI_API_KEY", "").strip()
    if key:
        return key
    key_file = Path.home() / ".zhenai-skills" / "api_key"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8-sig").strip() or None
    return None


def require_auth(allow_skip=False):
    """鉴权入口。验证通过返回用户信息 dict，失败则 sys.exit(1)。

    返回值结构:
        {sub, name, role, teams, depts, data_scope, can_query_raw, can_view_sensitive}

    allow_skip=True 时（如 doctor 命令），鉴权失败不阻断执行。
    """
    api_key = _get_api_key()
    if not api_key:
        if allow_skip:
            _print_safe("[WARN] ZHENAI_API_KEY 未配置，鉴权跳过")
            return None
        _print_safe("[ERROR] 请设置环境变量 ZHENAI_API_KEY（格式 za_xxx）或写入 ~/.zhenai-skills/api_key")
        sys.exit(1)

    config = _load_config()
    if not config:
        if allow_skip:
            _print_safe("[WARN] auth_config.json 未找到或格式错误，鉴权跳过")
            return None
        _print_safe(f"[ERROR] 鉴权配置文件缺失: {_CONFIG_FILE}")
        sys.exit(1)

    entry = _api_key_index.get(api_key)
    if not entry:
        if allow_skip:
            _print_safe("[WARN] API Key 无效，鉴权跳过")
            return None
        _print_safe("[ERROR] API Key 无效，请检查 ZHENAI_API_KEY")
        sys.exit(1)

    username, user_data = entry
    role = user_data.get("role", "")
    role_info = config.get("roles", {}).get(role, {})

    # 权限优先级: 用户级显式设置 > 角色默认值
    def _perm(key):
        if key in user_data:
            return bool(user_data[key])
        return bool(role_info.get(key, False))

    return {
        "sub": username,
        "name": user_data.get("name", ""),
        "role": role,
        "teams": user_data.get("teams", []),
        "depts": user_data.get("depts", []),
        "data_scope": user_data.get("data_scope", ""),
        "can_query_raw": _perm("can_query_raw"),
        "can_view_sensitive": _perm("can_view_sensitive"),
    }


# ── 权限检查 API ──────────────────────────────────


def check_team_access(user_info, team):
    """检查用户是否有权访问指定团队的数据。

    Args:
        user_info: require_auth() 的返回值
        team: 团队标识（如 "telesale", "wechat_archive"）

    Returns:
        bool
    """
    if not user_info:
        return False
    teams = user_info.get("teams", [])
    if "all" in teams:
        return True
    return team in teams


def check_sensitive_access(user_info):
    """检查用户是否有权查看敏感内容（会话正文、录音转写等）。

    Returns:
        bool
    """
    if not user_info:
        return False
    return user_info.get("can_view_sensitive", False)


def check_raw_sql(user_info):
    """检查用户是否有权执行自由 SQL。

    Returns:
        bool
    """
    if not user_info:
        return False
    return user_info.get("can_query_raw", False)
