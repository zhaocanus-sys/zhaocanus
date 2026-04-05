#!/usr/bin/env python3
"""
珍爱网数据分析 API 查询脚本
用法: python3 query.py <命令> [参数...]
"""

import argparse
import json
import sys
from typing import Optional

import requests

# API配置
BASE_URL = "http://42.193.182.174:8090"


def get_headers(api_key: Optional[str] = None) -> dict:
    """获取请求头"""
    if not api_key:
        print("错误: 未提供 API Key。请使用 --key 参数指定，例如: --key za_xxxx", file=sys.stderr)
        sys.exit(1)
    return {"X-API-Key": api_key}


def make_request(method: str, path: str, params: Optional[dict] = None, 
                 api_key: Optional[str] = None) -> dict:
    """发起API请求"""
    url = f"{BASE_URL}{path}"
    headers = get_headers(api_key)
    
    try:
        resp = requests.request(method, url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP错误: {e}", file=sys.stderr)
        if e.response is not None:
            print(f"响应内容: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_me(args):
    """查看当前用户信息"""
    data = make_request("GET", "/auth/me", api_key=args.key)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_teams(args):
    """获取团队与数据源配置（API tools/config）"""
    data = make_request("GET", "/api/v1/tools/config", api_key=args.key)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_datasources(args):
    """获取数据源列表"""
    data = make_request("GET", "/api/v1/datasource/list", api_key=args.key)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_daily(args):
    """获取团队日报数据"""
    params = {
        "page": args.page,
        "page_size": args.size
    }
    if args.date:
        params["date"] = args.date
    
    data = make_request("GET", f"/api/v1/team/{args.team}/daily", params=params, api_key=args.key)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_trend(args):
    """获取团队趋势数据"""
    params = {"days": args.days}
    data = make_request("GET", f"/api/v1/team/{args.team}/trend", params=params, api_key=args.key)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_tables(args):
    """查看团队可用数据表"""
    data = make_request("GET", f"/api/v1/team/{args.team}/tables", api_key=args.key)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_query(args):
    """自定义查询"""
    params = {
        "table_role": args.table_role,
        "select": args.select,
        "page": args.page,
        "page_size": args.size
    }
    if args.date:
        params["date"] = args.date
    
    data = make_request("GET", f"/api/v1/team/{args.team}/query", params=params, api_key=args.key)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_ad_categories(args):
    """广告投放报表分类"""
    data = make_request("GET", "/api/v1/advertising/categories", api_key=args.key)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_ad_report(args):
    """按报表ID查询投放数据"""
    params = {
        "page": args.page,
        "page_size": args.size
    }
    if args.date:
        params["date"] = args.date
    
    data = make_request("GET", f"/api/v1/advertising/report/{args.report_id}", 
                       params=params, api_key=args.key)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_ad_daily(args):
    """投放日报总览"""
    params = {}
    if args.date:
        params["date"] = args.date
    
    data = make_request("GET", "/api/v1/advertising/daily", params=params, api_key=args.key)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_wechat_employees(args):
    """查询指定类型的员工列表"""
    params = {"employee_type": args.employee_type}
    if args.keyword:
        params["keyword"] = args.keyword
    if args.exact_dept:
        params["exact_dept"] = args.exact_dept
    if args.worker_name:
        params["worker_name"] = args.worker_name
    data = make_request("GET", "/api/v1/wechat-session/employees", params=params, api_key=args.key)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_wechat_messages(args):
    """查询企微会话记录"""
    params = {
        "employee_type": args.employee_type,
        "date_start": args.date_start,
        "date_end": args.date_end,
        "page": args.page,
        "page_size": args.size,
    }
    if args.keyword:
        params["keyword"] = args.keyword
    if args.exact_dept:
        params["exact_dept"] = args.exact_dept
    if args.worker_name:
        params["worker_name"] = args.worker_name
    data = make_request("GET", "/api/v1/wechat-session/messages", params=params, api_key=args.key)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_wechat_stats(args):
    """查询企微会话统计"""
    params = {
        "employee_type": args.employee_type,
        "date_start": args.date_start,
        "date_end": args.date_end,
    }
    if args.keyword:
        params["keyword"] = args.keyword
    if args.exact_dept:
        params["exact_dept"] = args.exact_dept
    if args.worker_name:
        params["worker_name"] = args.worker_name
    data = make_request("GET", "/api/v1/wechat-session/stats", params=params, api_key=args.key)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_vip_list(args):
    """查询VIP用户列表"""
    params = {
        "maturity_min": args.maturity_min,
        "maturity_max": args.maturity_max,
        "page": args.page,
        "page_size": args.size,
    }
    data = make_request("GET", "/api/v1/vip-users/list", params=params, api_key=args.key)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_vip_notes(args):
    """根据memberId列表查询小记"""
    params = {
        "member_ids": args.member_ids,
        "note_limit": args.note_limit,
    }
    data = make_request("GET", "/api/v1/vip-users/notes", params=params, api_key=args.key)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_vip_analysis(args):
    """VIP用户小记聚合分析（一键接口）"""
    params = {
        "maturity_min": args.maturity_min,
        "maturity_max": args.maturity_max,
        "note_limit": args.note_limit,
        "page": args.page,
        "page_size": args.size,
    }
    data = make_request("GET", "/api/v1/vip-users/analysis", params=params, api_key=args.key)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_health(args):
    """数据健康度检查"""
    if args.team:
        path = f"/api/v1/health/{args.team}"
    else:
        path = "/api/v1/health/"
    
    data = make_request("GET", path, api_key=args.key)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="珍爱网数据分析 API 查询工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # me命令
    parser_me = subparsers.add_parser("me", help="查看当前用户信息")
    parser_me.add_argument("--key", help="API Key")
    parser_me.set_defaults(func=cmd_me)
    
    # teams命令
    parser_teams = subparsers.add_parser("teams", help="获取团队与数据源配置")
    parser_teams.add_argument("--key", help="API Key")
    parser_teams.set_defaults(func=cmd_teams)
    
    # datasources命令
    parser_ds = subparsers.add_parser("datasources", help="获取数据源列表")
    parser_ds.add_argument("--key", help="API Key")
    parser_ds.set_defaults(func=cmd_datasources)
    
    # daily命令
    parser_daily = subparsers.add_parser("daily", help="获取团队日报数据")
    parser_daily.add_argument("team", choices=["telesale", "jianxin", "invite", "shop", 
                                               "hongniang", "app", "qyh", "xfh",
                                               "wechat_archive", "shyb", "refund", "yf",
                                               "performance", "organization"],
                             help="团队名称")
    parser_daily.add_argument("--date", help="日期 (YYYYMMDD)")
    parser_daily.add_argument("--page", type=int, default=1, help="页码")
    parser_daily.add_argument("--size", type=int, default=500, help="每页大小")
    parser_daily.add_argument("--key", help="API Key")
    parser_daily.set_defaults(func=cmd_daily)
    
    # trend命令
    parser_trend = subparsers.add_parser("trend", help="获取团队趋势数据")
    parser_trend.add_argument("team", choices=["telesale", "jianxin", "invite", "shop", 
                                               "hongniang", "app", "qyh", "xfh",
                                               "wechat_archive", "shyb", "refund", "yf",
                                               "performance", "organization"],
                             help="团队名称")
    parser_trend.add_argument("--days", type=int, default=7, help="天数")
    parser_trend.add_argument("--key", help="API Key")
    parser_trend.set_defaults(func=cmd_trend)
    
    # tables命令
    parser_tables = subparsers.add_parser("tables", help="查看团队可用数据表")
    parser_tables.add_argument("team", choices=["telesale", "jianxin", "invite", "shop", 
                                                "hongniang", "app", "qyh", "xfh",
                                                "wechat_archive", "shyb", "refund", "yf",
                                                "advertising", "performance", "organization"],
                              help="团队名称")
    parser_tables.add_argument("--key", help="API Key")
    parser_tables.set_defaults(func=cmd_tables)
    
    # query命令
    parser_query = subparsers.add_parser("query", help="自定义查询")
    parser_query.add_argument("team", choices=["telesale", "jianxin", "invite", "shop", 
                                               "hongniang", "app", "qyh", "xfh",
                                               "wechat_archive", "shyb", "refund", "yf",
                                               "advertising", "performance", "organization"],
                             help="团队名称")
    parser_query.add_argument("table_role", help="数据表角色")
    parser_query.add_argument("--date", help="日期 (YYYYMMDD)")
    parser_query.add_argument("--select", default="*", help="选择字段")
    parser_query.add_argument("--page", type=int, default=1, help="页码")
    parser_query.add_argument("--size", type=int, default=500, help="每页大小")
    parser_query.add_argument("--key", help="API Key")
    parser_query.set_defaults(func=cmd_query)
    
    # ad-categories命令
    parser_ad_cat = subparsers.add_parser("ad-categories", help="广告投放报表分类")
    parser_ad_cat.add_argument("--key", help="API Key")
    parser_ad_cat.set_defaults(func=cmd_ad_categories)
    
    # ad-report命令
    parser_ad_report = subparsers.add_parser("ad-report", help="按报表ID查询投放数据")
    parser_ad_report.add_argument("report_id", help="报表ID")
    parser_ad_report.add_argument("--date", help="日期 (YYYYMMDD)")
    parser_ad_report.add_argument("--page", type=int, default=1, help="页码")
    parser_ad_report.add_argument("--size", type=int, default=500, help="每页大小")
    parser_ad_report.add_argument("--key", help="API Key")
    parser_ad_report.set_defaults(func=cmd_ad_report)
    
    # ad-daily命令
    parser_ad_daily = subparsers.add_parser("ad-daily", help="投放日报总览")
    parser_ad_daily.add_argument("--date", help="日期 (YYYYMMDD)")
    parser_ad_daily.add_argument("--key", help="API Key")
    parser_ad_daily.set_defaults(func=cmd_ad_daily)
    
    # health命令
    parser_health = subparsers.add_parser("health", help="数据健康度检查")
    parser_health.add_argument("team", nargs="?", 
                              choices=["telesale", "jianxin", "invite", "shop", 
                                      "hongniang", "app", "qyh", "xfh",
                                      "wechat_archive", "shyb", "refund", "yf",
                                      "advertising", "performance", "organization"],
                              help="团队名称（可选）")
    parser_health.add_argument("--key", help="API Key")
    parser_health.set_defaults(func=cmd_health)
    
    # vip-list命令
    parser_vip_list = subparsers.add_parser("vip-list", help="查询VIP用户列表")
    parser_vip_list.add_argument("--maturity-min", type=int, default=-1, help="成熟度最小值(含)")
    parser_vip_list.add_argument("--maturity-max", type=int, default=8, help="成熟度最大值(含)")
    parser_vip_list.add_argument("--page", type=int, default=1, help="页码")
    parser_vip_list.add_argument("--size", type=int, default=200, help="每页大小")
    parser_vip_list.add_argument("--key", help="API Key")
    parser_vip_list.set_defaults(func=cmd_vip_list)

    # vip-notes命令
    parser_vip_notes = subparsers.add_parser("vip-notes", help="根据memberId列表查询小记")
    parser_vip_notes.add_argument("member_ids", help="会员ID列表，逗号分隔")
    parser_vip_notes.add_argument("--note-limit", type=int, default=20, help="每个会员最多小记条数")
    parser_vip_notes.add_argument("--key", help="API Key")
    parser_vip_notes.set_defaults(func=cmd_vip_notes)

    # vip-analysis命令
    parser_vip_analysis = subparsers.add_parser("vip-analysis", help="VIP用户小记聚合分析（一键）")
    parser_vip_analysis.add_argument("--maturity-min", type=int, default=-1, help="成熟度最小值(含)")
    parser_vip_analysis.add_argument("--maturity-max", type=int, default=8, help="成熟度最大值(含)")
    parser_vip_analysis.add_argument("--note-limit", type=int, default=10, help="每个VIP最多小记条数")
    parser_vip_analysis.add_argument("--page", type=int, default=1, help="页码")
    parser_vip_analysis.add_argument("--size", type=int, default=50, help="每页VIP用户数")
    parser_vip_analysis.add_argument("--key", help="API Key")
    parser_vip_analysis.set_defaults(func=cmd_vip_analysis)

    # wechat-employees命令
    _et_choices = ["网销", "电销", "电红"]
    parser_we = subparsers.add_parser("wechat-employees", help="查询指定类型的员工列表(含wxid)")
    parser_we.add_argument("employee_type", choices=_et_choices, help="员工类型")
    parser_we.add_argument("--keyword", help="网销部门名关键词，如'深圳网销'")
    parser_we.add_argument("--exact-dept", help="部门名精确匹配，如'广州网销二部-8部'")
    parser_we.add_argument("--worker-name", help="员工姓名精确过滤(逗号分隔多人)")
    parser_we.add_argument("--key", help="API Key")
    parser_we.set_defaults(func=cmd_wechat_employees)

    # wechat-messages命令
    parser_wm = subparsers.add_parser("wechat-messages", help="查询企微会话记录")
    parser_wm.add_argument("employee_type", choices=_et_choices, help="员工类型")
    parser_wm.add_argument("date_start", help="开始日期 YYYYMMDD")
    parser_wm.add_argument("date_end", help="结束日期 YYYYMMDD")
    parser_wm.add_argument("--keyword", help="网销部门名关键词")
    parser_wm.add_argument("--exact-dept", help="部门名精确匹配")
    parser_wm.add_argument("--worker-name", help="员工姓名精确过滤(逗号分隔多人)")
    parser_wm.add_argument("--page", type=int, default=1, help="页码")
    parser_wm.add_argument("--size", type=int, default=100, help="每页大小")
    parser_wm.add_argument("--key", help="API Key")
    parser_wm.set_defaults(func=cmd_wechat_messages)

    # wechat-stats命令
    parser_ws = subparsers.add_parser("wechat-stats", help="查询企微会话统计(按员工/部门汇总)")
    parser_ws.add_argument("employee_type", choices=_et_choices, help="员工类型")
    parser_ws.add_argument("date_start", help="开始日期 YYYYMMDD")
    parser_ws.add_argument("date_end", help="结束日期 YYYYMMDD")
    parser_ws.add_argument("--keyword", help="网销部门名关键词")
    parser_ws.add_argument("--exact-dept", help="部门名精确匹配")
    parser_ws.add_argument("--worker-name", help="员工姓名精确过滤(逗号分隔多人)")
    parser_ws.add_argument("--key", help="API Key")
    parser_ws.set_defaults(func=cmd_wechat_stats)

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
