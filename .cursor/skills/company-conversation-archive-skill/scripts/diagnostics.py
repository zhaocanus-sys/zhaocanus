#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境与连接诊断
"""
from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from typing import Iterable, List, Optional


STATUS_ICONS = {
    "ok": "[OK]",
    "warning": "[WARN]",
    "error": "[ERR]",
    "info": "[INFO]",
}


@dataclass
class CheckResult:
    name: str
    status: str
    summary: str
    action: str = ""
    details: str = ""


def render_report(results: Iterable[CheckResult], title: str = "诊断报告") -> str:
    lines = [f"=== {title} ==="]
    for result in results:
        icon = STATUS_ICONS.get(result.status, "-")
        lines.append(f"{icon} {result.name}: {result.summary}")
        if result.action:
            lines.append(f"   下一步: {result.action}")
        if result.details:
            lines.append(f"   详情: {result.details}")
    return "\n".join(lines)


def _module_exists(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def check_auth_status() -> CheckResult:
    """检查 API Key 鉴权配置状态（本地校验模式）。"""
    import json
    import os
    from pathlib import Path

    script_dir = Path(__file__).resolve().parent
    config_file = script_dir / "auth_config.json"

    if not config_file.exists():
        return CheckResult(
            name="鉴权配置",
            status="error",
            summary="auth_config.json 未找到。",
            action=f"请确认 {config_file} 存在。",
        )

    try:
        config = json.loads(config_file.read_text(encoding="utf-8"))
        user_count = len(config.get("users", {}))
        role_count = len(config.get("roles", {}))
    except (json.JSONDecodeError, OSError) as e:
        return CheckResult(
            name="鉴权配置",
            status="error",
            summary=f"auth_config.json 解析失败: {e}",
            action="检查文件格式是否为合法 JSON。",
        )

    api_key = os.environ.get("ZHENAI_API_KEY", "").strip()
    source = "环境变量"
    if not api_key:
        key_file = Path.home() / ".zhenai-skills" / "api_key"
        if key_file.exists():
            api_key = key_file.read_text(encoding="utf-8-sig").strip()
            source = f"文件 {key_file}"

    if not api_key:
        return CheckResult(
            name="鉴权配置",
            status="warning",
            summary=f"配置正常（{user_count} 用户, {role_count} 角色），但未设置 API Key。",
            action="设置环境变量 ZHENAI_API_KEY=za_xxx 或写入 ~/.zhenai-skills/api_key",
        )

    if not api_key.startswith("za_"):
        return CheckResult(
            name="鉴权配置",
            status="warning",
            summary=f"API Key 格式异常（来源: {source}），应以 za_ 开头。",
            action="请确认使用正确的 API Key（格式 za_xxx）。",
        )

    matched_user = None
    for username, user_data in config.get("users", {}).items():
        if user_data.get("api_key") == api_key:
            matched_user = (username, user_data)
            break

    if not matched_user:
        return CheckResult(
            name="鉴权配置",
            status="error",
            summary=f"API Key 在配置中未找到（来源: {source}）。",
            action="确认 API Key 正确，或联系管理员更新 auth_config.json。",
        )

    username, user_data = matched_user
    role = user_data.get("role", "")
    role_info = config.get("roles", {}).get(role, {})
    teams = user_data.get("teams", [])
    teams_str = "全部" if "all" in teams else ", ".join(teams)
    perms = []
    if role_info.get("can_query_raw"):
        perms.append("自由SQL")
    if role_info.get("can_view_sensitive"):
        perms.append("敏感数据")
    perms_str = ", ".join(perms) if perms else "基础查询"

    return CheckResult(
        name="鉴权配置",
        status="ok",
        summary=f"本地校验通过 — {user_data.get('name', username)} ({role})，团队: {teams_str}，权限: {perms_str}。",
    )


def check_local_dependencies() -> List[CheckResult]:
    deps = [
        ("pymysql", "MySQL 数据库驱动"),
        ("requests", "HTTP 请求库"),
        ("anthropic", "Anthropic AI 后端（可选）"),
        ("zhipuai", "智谱 AI 后端（可选）"),
    ]
    results: List[CheckResult] = []
    for module_name, label in deps:
        exists = _module_exists(module_name)
        is_optional = module_name in ("anthropic", "zhipuai")
        if exists:
            results.append(CheckResult(
                name=f"依赖 {module_name}", status="ok",
                summary=f"{label} 已安装。",
            ))
        elif is_optional:
            results.append(CheckResult(
                name=f"依赖 {module_name}", status="info",
                summary=f"{label} 未安装（不影响核心功能）。",
                action=f"如需 AI 分析功能，请安装: pip install {module_name}",
            ))
        else:
            results.append(CheckResult(
                name=f"依赖 {module_name}", status="error",
                summary=f"{label} 未安装。",
                action=f"请安装: pip install {module_name}",
            ))
    return results


def check_db_connection() -> CheckResult:
    """检查数据库连接"""
    try:
        from db_client import DBClient
        client = DBClient()
        try:
            if client.test_connection():
                return CheckResult(
                    name="数据库连接", status="ok",
                    summary="数据库连接正常。",
                )
            else:
                return CheckResult(
                    name="数据库连接", status="error",
                    summary="数据库连接失败。",
                    action="请检查网络连接、VPN 状态，或联系管理员确认数据库访问权限。",
                )
        finally:
            client.close()
    except Exception as e:
        return CheckResult(
            name="数据库连接", status="error",
            summary="数据库连接异常。",
            action="请检查网络连接和数据库配置。",
            details=str(e),
        )


def check_archive_data() -> CheckResult:
    """检查会话存档数据可读性"""
    try:
        from db_client import DBClient
        client = DBClient()
        count = client.count_messages()
        client.close()
        if count > 0:
            return CheckResult(
                name="会话存档数据", status="ok",
                summary=f"会话存档表可读，共 {count:,} 条消息记录。",
            )
        else:
            return CheckResult(
                name="会话存档数据", status="warning",
                summary="会话存档表可访问但无数据。",
                action="确认数据库中是否有会话存档数据写入。",
            )
    except Exception as e:
        return CheckResult(
            name="会话存档数据", status="warning",
            summary="无法查询会话存档数据。",
            details=str(e),
        )


# def check_org_data() -> CheckResult:
#     """检查组织架构数据可读性（已注释，分析引擎模式不使用）"""
#     try:
#         from org_resolver import OrgResolver
#         org = OrgResolver()
#         depts = org.list_depts()
#         org.close()
#         return CheckResult(
#             name="组织架构数据", status="ok",
#             summary=f"组织架构表可读，共 {len(depts)} 个启用部门。",
#         )
#     except Exception as e:
#         return CheckResult(
#             name="组织架构数据", status="warning",
#             summary="无法查询组织架构数据。",
#             action="确认 compass_data 库的访问权限。",
#             details=str(e),
#         )


def run_all_checks() -> List[CheckResult]:
    results = [check_auth_status()]
    results.extend(check_local_dependencies())
    results.append(check_db_connection())
    results.append(check_archive_data())
    # results.append(check_org_data())
    return results
