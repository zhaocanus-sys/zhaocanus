#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Description: 珍爱网数据分析服务 — CLI 入口
# Usage: python3 handler.py data sources
# Usage: python3 handler.py data query --table Dept --limit 10
# Usage: python3 handler.py org search 刘源

import argparse
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from diagnostics import (
    CheckResult,
    render_report,
    run_runtime_checks,
    run_setup_checks,
)


# ── 工具函数 ──────────────────────────────────────


def _get_org_resolver(required: bool = False):
    """获取组织架构解析器（可选）"""
    try:
        from org_resolver import OrgResolver
        return OrgResolver()
    except ImportError:
        if required:
            print("❌ 缺少 pymysql 依赖，请执行: pip3 install pymysql")
            sys.exit(1)
        return None
    except Exception as e:
        if required:
            print(f"❌ 连接 CynosDB 数据库失败: {e}")
            sys.exit(1)
        return None


def _doctor_org_probe() -> CheckResult:
    try:
        org = _get_org_resolver(required=True)
        tops = org.get_top_depts()
        return CheckResult(
            name="组织架构数据库",
            status="ok",
            summary=f"CynosDB 连接正常，当前可读取 {len(tops)} 个顶层部门。",
        )
    except SystemExit:
        return CheckResult(
            name="组织架构数据库",
            status="warning",
            summary="无法连接 CynosDB 数据库。",
            action="确认网络连通性和数据库账号权限。",
        )
    except Exception as e:
        return CheckResult(
            name="组织架构数据库",
            status="warning",
            summary="CynosDB 数据库探测失败。",
            action="确认 pymysql 依赖和网络连通性。",
            details=str(e),
        )


def _doctor_analytics_probe() -> CheckResult:
    """探测数据分析引擎连通性"""
    try:
        from data_engine import DataEngine
        engine = DataEngine()
        result = engine.check_health()
        if result["status"] == "healthy":
            db_info = ", ".join(f"{k}: {v}表" for k, v in result["databases"].items())
            return CheckResult(
                name="数据分析引擎",
                status="ok",
                summary=f"Libra 分析引擎连接正常 (v{result['version']})。{db_info}",
            )
        return CheckResult(
            name="数据分析引擎",
            status="error",
            summary=f"分析引擎不可达: {result.get('error', 'unknown')}",
            action="检查网络连通性或联系管理员。",
        )
    except Exception as e:
        return CheckResult(
            name="数据分析引擎",
            status="warning",
            summary="数据分析引擎探测失败。",
            action="确认 pymysql 依赖和网络连通性。",
            details=str(e),
        )


# ── 数据源标识 ─────────────────────────────────────

SKILL_NAME = "analysis-data-service-skill"
SKILL_LABEL = "📊 数据分析服务"
ENGINE_LIBRA = "CynosDB Libra 分析引擎"
ENGINE_CYNOSDB = "CynosDB"


def _print_source(engine: str, database: str = None, table: str = None, extra: str = None):
    """输出数据源标识行，让用户/Agent 明确数据来源"""
    parts = [f"技能: {SKILL_NAME}", f"引擎: {engine}"]
    if database:
        parts.append(f"库: {database}")
    if table:
        parts.append(f"表: {table}")
    if extra:
        parts.append(extra)
    print(f"[数据源] {' | '.join(parts)}")


def _print_feedback_hint():
    """在查询结果末尾输出反馈提示"""
    print("\n📝 如数据与实际不符，可告知我\"反馈数据问题\"提交核实请求")


# ── 子命令实现 ────────────────────────────────────


def cmd_doctor(args):
    """环境与连通性诊断"""
    setup_results = run_setup_checks()
    print(render_report(setup_results, title="安装环境检查"))

    setup_has_error = any(r.status == "error" for r in setup_results)
    if args.setup_only:
        if setup_has_error:
            sys.exit(1)
        return

    if setup_has_error:
        print("\n❌ 本地环境还未准备好，先修复上面的 setup 问题。")
        sys.exit(1)

    runtime_results = run_runtime_checks(
        org_probe=_doctor_org_probe,
        analytics_probe=_doctor_analytics_probe,
    )
    print()
    print(render_report(runtime_results, title="数据库连通性检查"))

    statuses = [r.status for r in runtime_results]
    if "error" in statuses:
        sys.exit(1)
    if "warning" in statuses:
        sys.exit(2)


def cmd_org_search(args):
    """组织架构：搜索员工"""
    org = _get_org_resolver(required=True)
    results = org.search_users(args.keyword, active_only=not args.all)

    _print_source(ENGINE_CYNOSDB, "compass_data", "Worker")
    label = "全部" if args.all else "在职"
    print(f"🔍 搜索 \"{args.keyword}\" ({label}) 共 {len(results)} 人:\n")
    for u in results:
        dept_str = u.get("wx_dept_path") or u.get("crm_dept") or "未知部门"
        print(f"  {u['name']:<12} | userId: {u['userid']:<35} | {u.get('position', ''):<8} | {u['state_label']} | {dept_str}")
    _print_feedback_hint()


def cmd_org_dept(args):
    """组织架构：浏览部门树"""
    org = _get_org_resolver(required=True)
    _print_source(ENGINE_CYNOSDB, "compass_data", "Dept")

    if args.crm:
        depts = org.list_crm_depts(active_only=not args.all_depts)
        label = "全部" if args.all_depts else "启用"
        print(f"📂 CRM 部门 ({label}) 共 {len(depts)} 个:\n")
        for d in depts:
            status = "" if not d.get("disabled") else " [已禁用]"
            print(f"  {d['deptName']:<20} | deptId: {d['deptId']}{status}")
    elif args.search:
        results = org.search_dept(args.search)
        print(f"🔍 搜索部门 \"{args.search}\" 共 {len(results)} 个:\n")
        for d in results:
            sub = f" ({d['child_count']} 个子部门)" if d["child_count"] > 0 else ""
            print(f"  {d['name']:<20} | ID: {d['id']}{sub}")
            print(f"    路径: {d['path']}")
    elif args.id:
        path = org.get_dept_path(args.id)
        children = org.get_dept_children(args.id)
        print(f"📂 {path} (ID: {args.id})")
        print(f"   子部门共 {len(children)} 个:\n")
        for c in children:
            sub = f" ({c['child_count']} 个子部门)" if c["child_count"] > 0 else ""
            print(f"  {c['name']:<20} | ID: {c['id']}{sub}")
    else:
        tops = org.get_top_depts()
        print(f"📂 顶层部门共 {len(tops)} 个:\n")
        for d in tops:
            sub = f" ({d['child_count']} 个子部门)" if d["child_count"] > 0 else ""
            print(f"  {d['name']:<20} | ID: {d['id']}{sub}")


def cmd_org_members(args):
    """组织架构：列出部门成员"""
    org = _get_org_resolver(required=True)
    _print_source(ENGINE_CYNOSDB, "compass_data", "Worker")

    if args.crm:
        members = org.list_crm_dept_members(args.dept)
        label = f"CRM deptId={args.dept}"
    else:
        members = org.list_dept_members(args.dept, recursive=args.recursive)
        path = org.get_dept_path(args.dept)
        label = path or f"deptId={args.dept}"
        if args.recursive:
            label += " (含子部门)"

    print(f"👥 {label} 共 {len(members)} 名在职员工:\n")
    for u in members:
        dept_str = u.get("crm_dept", "")
        print(f"  {u['name']:<12} | userId: {u['userid']:<35} | {u.get('position', ''):<8} | {dept_str}")


def cmd_org_resolve(args):
    """组织架构：按 userId 查用户详情"""
    org = _get_org_resolver(required=True)
    _print_source(ENGINE_CYNOSDB, "compass_data", "Worker")
    user = org.resolve_user(args.userid)

    if not user:
        print(f"❌ 未找到用户: {args.userid}")
        sys.exit(1)

    print(f"👤 用户详情:")
    print(f"   姓名:     {user['name']}")
    print(f"   userId:   {user['userid']}")
    print(f"   职位:     {user.get('position', '')}")
    print(f"   状态:     {user['state_label']}")
    print(f"   CRM部门:  {user.get('crm_dept') or '无'}")
    if user.get("email"):
        print(f"   邮箱:     {user['email']}")
    if user.get("wx_dept_paths"):
        print(f"   企微部门: {' / '.join(user['wx_dept_paths'])}")


# ── data 子命令实现 ────────────────────────────────


def cmd_data_sources(args):
    """列出所有业务域"""
    from datasource_registry import list_sources
    sources = list_sources()
    _print_source(ENGINE_LIBRA, extra=f"共 {len(sources)} 个业务域")
    print(f"📊 数据分析引擎共 {len(sources)} 个业务域:\n")
    for s in sources:
        print(f"  {s['key']:<16} | {s['label']:<12} | {s['database']:<24} | {s['table_count']} 张表")


def cmd_data_tables(args):
    """列出某业务域下的表"""
    from datasource_registry import list_tables, DATASOURCE_REGISTRY
    tables = list_tables(args.source)
    if not tables:
        print(f"❌ 未找到业务域: {args.source}")
        print("   执行 data sources 查看所有可用业务域")
        sys.exit(1)
    src = DATASOURCE_REGISTRY.get(args.source, {})
    _print_source(ENGINE_LIBRA, src.get("database", ""), extra=f"业务域: {src.get('label', args.source)}")
    print(f"📋 [{args.source}] 共 {len(tables)} 张表:\n")
    for t in tables:
        print(f"  {t['table']:<55} | {t['keywords']}")


def cmd_data_columns(args):
    """查看表结构"""
    from data_engine import DataEngine
    from datasource_registry import resolve_table
    engine = DataEngine()
    try:
        cols = engine.get_table_columns(args.table, database=args.database)
    except ValueError as e:
        print(f"❌ {e}")
        print("   提示: 使用 data search --keyword 关键词 查找正确的表名")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 查询表结构失败: {e}")
        sys.exit(1)

    db_name = args.database
    if not db_name:
        resolved = resolve_table(args.table)
        db_name = resolved[1] if resolved else None
    _print_source(ENGINE_LIBRA, db_name, args.table)

    count = engine.get_table_count(args.table, database=args.database)
    print(f"📐 {args.table} ({len(cols)} 个字段, ~{count:,} 行):\n")
    for c in cols:
        nullable = "NULL" if c["null"] == "YES" else "NOT NULL"
        key = f" [{c['key']}]" if c["key"] else ""
        print(f"  {c['field']:<40} | {c['type']:<20} | {nullable}{key}")


def cmd_data_query(args):
    """查询业务表数据"""
    from data_engine import DataEngine, format_results_as_text, format_results_as_json
    from datasource_registry import resolve_table

    engine = DataEngine()
    try:
        rows = engine.query_table(
            table_name=args.table,
            database=args.database,
            date=args.date,
            limit=args.limit,
            offset=args.offset or 0,
        )
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        sys.exit(1)

    db_name = args.database
    if not db_name:
        resolved = resolve_table(args.table)
        db_name = resolved[1] if resolved else None
    _print_source(ENGINE_LIBRA, db_name, args.table)

    print(f"📊 {args.table} 返回 {len(rows)} 行" + (f" (date={args.date})" if args.date else "") + ":\n")

    if args.format == "json":
        print(format_results_as_json(rows))
    else:
        print(format_results_as_text(rows))
    _print_feedback_hint()


def cmd_data_search(args):
    """按关键词搜索表"""
    from datasource_registry import find_table
    results = find_table(args.keyword)
    if not results:
        print(f"⚠️  没有找到匹配 \"{args.keyword}\" 的表")
        print("   提示: 尝试更短的关键词，或执行 data sources 查看所有业务域")
        return
    _print_source(ENGINE_LIBRA, extra=f"搜索关键词: {args.keyword}")
    print(f"🔍 搜索 \"{args.keyword}\" 匹配 {len(results)} 张表:\n")
    for r in results:
        print(f"  [{r['source']:<12}] {r['table']:<55} | {r['keywords']}")


def cmd_data_sql(args):
    """执行自由 SQL（需要 can_query_raw 权限）"""
    from auth_guard import check_raw_sql
    user_info = getattr(args, "_user_info", None)
    if not check_raw_sql(user_info):
        name = user_info.get("name", "未知") if user_info else "未知"
        print(f"❌ 权限不足: {name} 没有执行自由 SQL 的权限（仅 admin 角色可用）")
        sys.exit(1)

    from data_engine import DataEngine, format_results_as_text, format_results_as_json

    engine = DataEngine(query_timeout=args.timeout)
    try:
        rows = engine.execute_sql(args.sql, database=args.database)
    except Exception as e:
        print(f"❌ SQL 执行失败: {e}")
        sys.exit(1)

    _print_source(ENGINE_LIBRA, args.database, extra=f"自由SQL查询")
    print(f"📊 返回 {len(rows)} 行:\n")
    if args.format == "json":
        print(format_results_as_json(rows))
    else:
        print(format_results_as_text(rows))
    _print_feedback_hint()


def cmd_data_health(args):
    """检查分析引擎连通性"""
    from data_engine import DataEngine
    engine = DataEngine()
    result = engine.check_health()

    _print_source(ENGINE_LIBRA, extra="连通性检查")
    if result["status"] == "healthy":
        print(f"✅ 数据分析引擎连接正常")
        print(f"   版本: {result['version']}")
        for db, count in result["databases"].items():
            print(f"   {db}: {count} 张表")
    else:
        print(f"❌ 数据分析引擎不可达")
        print(f"   错误: {result.get('error', 'unknown')}")
        sys.exit(1)


# ── feedback 子命令实现 ─────────────────────────────


def cmd_feedback_submit(args):
    """提交数据反馈"""
    from feedback_client import submit_feedback, get_feedback_status

    feedback_id = submit_feedback(
        skill_name=SKILL_NAME,
        table=args.table,
        description=args.description,
        issue_type=args.type,
        expected_value=args.expected,
        actual_value=args.actual,
        severity=args.severity,
        sql=args.sql,
        database=args.database,
        command=f"feedback submit --table {args.table}",
    )
    fb = get_feedback_status(feedback_id)
    sync = fb.get("sync_status", "unknown") if fb else "unknown"
    print(f"✅ 反馈已提交，ID: {feedback_id}")
    if sync == "synced":
        print("   📡 已同步到服务端，研发团队将收到通知")
    elif sync == "email_sent":
        print("   📧 已通过邮件通知研发团队")
    else:
        print("   ⚠️ 远程同步和邮件均未成功，反馈已保存到本地，下次提交时自动重试")
    print(f"   查看进度: python scripts/handler.py feedback status --id {feedback_id}")


def cmd_feedback_list(args):
    """查看已提交的反馈"""
    from feedback_client import list_feedback

    items = list_feedback(limit=args.limit, status_filter=args.status)
    if not items:
        print("📭 暂无反馈记录")
        return

    print(f"📋 共 {len(items)} 条反馈:\n")
    for fb in items:
        status_map = {
            "pending": "⏳ 待处理",
            "investigating": "🔍 核实中",
            "verified": "✅ 已确认",
            "fixed": "🔧 已修复",
            "rejected": "❌ 已驳回",
        }
        s = status_map.get(fb.get("status", ""), fb.get("status", ""))
        table = fb.get("query_context", {}).get("table", "")
        desc = fb.get("issue", {}).get("description", "")[:60]
        created = fb.get("created_at", "")[:16]
        print(f"  {fb['feedback_id']} | {s} | {table}")
        print(f"    {desc}")
        print(f"    提交时间: {created}")
        print()


def cmd_feedback_status(args):
    """查询单条反馈状态"""
    from feedback_client import get_feedback_status

    fb = get_feedback_status(args.id)
    if not fb:
        print(f"❌ 未找到反馈: {args.id}")
        sys.exit(1)

    status_map = {
        "pending": "⏳ 待处理",
        "investigating": "🔍 核实中",
        "verified": "✅ 已确认",
        "fixed": "🔧 已修复",
        "rejected": "❌ 已驳回",
    }
    s = status_map.get(fb.get("status", ""), fb.get("status", ""))
    print(f"📄 反馈详情: {fb['feedback_id']}\n")
    print(f"  状态:     {s}")
    print(f"  提交人:   {fb.get('submitted_by', {}).get('name', '')}")
    print(f"  表:       {fb.get('query_context', {}).get('table', '')}")
    print(f"  问题类型: {fb.get('issue', {}).get('type', '')}")
    print(f"  问题描述: {fb.get('issue', {}).get('description', '')}")
    expected = fb.get("issue", {}).get("expected_value", "")
    actual = fb.get("issue", {}).get("actual_value", "")
    if expected:
        print(f"  期望值:   {expected}")
    if actual:
        print(f"  实际值:   {actual}")
    print(f"  严重程度: {fb.get('issue', {}).get('severity', '')}")
    print(f"  提交时间: {fb.get('created_at', '')}")
    resolution = fb.get("resolution")
    if resolution:
        print(f"\n  处理说明: {resolution.get('note', '')}")
        print(f"  处理人:   {resolution.get('resolved_by', '')}")
        print(f"  处理时间: {resolution.get('resolved_at', '')}")


# ── CLI 路由 ──────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="珍爱网数据分析服务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
数据分析:
  python3 handler.py data sources                                    # 列出所有业务域
  python3 handler.py data tables --source telesale                   # 列出域下的表
  python3 handler.py data columns --table Dept                       # 查看表结构
  python3 handler.py data query --table Dept --limit 10              # 查询数据
  python3 handler.py data search --keyword 电销日报                   # 按关键词找表
  python3 handler.py data sql --sql "SELECT * FROM compass_data.Dept LIMIT 5"
  python3 handler.py data health                                     # 分析引擎连通性

组织架构:
  python3 handler.py org search 刘源                                 # 搜索员工
  python3 handler.py org dept --search 网销                          # 搜索部门
  python3 handler.py org members --dept 700262621 --recursive        # 列出部门成员

诊断:
  python3 handler.py doctor                                          # 环境与连通性诊断
        """)
    sub = parser.add_subparsers(dest="command")

    # doctor
    p_doc = sub.add_parser("doctor", help="环境与连通性诊断")
    p_doc.add_argument("--setup-only", action="store_true",
                       help="仅检查本地安装环境，不检查数据库连通性")

    # ── data 子命令组（数据分析） ──
    p_data = sub.add_parser("data", help="数据分析查询（CynosDB 分析引擎）")
    data_sub = p_data.add_subparsers(dest="data_command")

    data_sub.add_parser("sources", help="列出所有业务域")

    p_dt = data_sub.add_parser("tables", help="列出业务域下的表")
    p_dt.add_argument("--source", required=True, help="业务域 key (如 telesale, shop)")

    p_dc = data_sub.add_parser("columns", help="查看表结构")
    p_dc.add_argument("--table", required=True, help="表名")
    p_dc.add_argument("--database", help="数据库名（不传则自动推断）")

    p_dq = data_sub.add_parser("query", help="查询业务表数据")
    p_dq.add_argument("--table", required=True, help="表名")
    p_dq.add_argument("--database", help="数据库名")
    p_dq.add_argument("--date", help="日期过滤 (YYYYMMDD)")
    p_dq.add_argument("--limit", type=int, default=500, help="返回行数上限 (默认: 500)")
    p_dq.add_argument("--offset", type=int, default=0, help="偏移量 (默认: 0)")
    p_dq.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")

    p_ds = data_sub.add_parser("search", help="按关键词搜索表")
    p_ds.add_argument("--keyword", required=True, help="业务关键词")

    p_dsql = data_sub.add_parser("sql", help="执行自由 SQL")
    p_dsql.add_argument("--sql", required=True, help="SQL 查询语句")
    p_dsql.add_argument("--database", help="默认数据库")
    p_dsql.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    p_dsql.add_argument("--timeout", type=int, default=60, help="查询超时秒数 (默认: 60)")

    data_sub.add_parser("health", help="检查分析引擎连通性")

    # ── org 子命令组（组织架构） ──
    p_org = sub.add_parser("org", help="组织架构查询（CynosDB）")
    org_sub = p_org.add_subparsers(dest="org_command")

    p_os = org_sub.add_parser("search", help="按姓名搜索员工")
    p_os.add_argument("keyword", help="搜索关键字（姓名）")
    p_os.add_argument("--all", action="store_true", help="包含离职人员")

    p_od = org_sub.add_parser("dept", help="浏览部门树")
    p_od.add_argument("--id", type=int, help="部门 ID（不指定则显示顶层）")
    p_od.add_argument("--search", help="按名称搜索部门")
    p_od.add_argument("--crm", action="store_true", help="显示 CRM 部门列表（扁平）")
    p_od.add_argument("--all-depts", action="store_true", help="包含已禁用部门")

    p_om = org_sub.add_parser("members", help="列出部门成员")
    p_om.add_argument("--dept", type=int, required=True, help="部门 deptId")
    p_om.add_argument("--crm", action="store_true", help="按 CRM deptId 查询")
    p_om.add_argument("--recursive", "-r", action="store_true", help="包含子部门")

    p_or = org_sub.add_parser("resolve", help="按 userId 查用户详情")
    p_or.add_argument("userid", help="企微 userId")

    # ── feedback 子命令组（数据反馈） ──
    p_fb = sub.add_parser("feedback", help="数据反馈（提交/查看/跟踪）")
    fb_sub = p_fb.add_subparsers(dest="feedback_command")

    p_fbs = fb_sub.add_parser("submit", help="提交数据反馈")
    p_fbs.add_argument("--table", required=True, help="涉及的表名")
    p_fbs.add_argument("--description", required=True, help="问题描述")
    p_fbs.add_argument("--type", default="data_inaccuracy",
                       choices=["data_inaccuracy", "missing_data", "stale_data", "wrong_format", "other"],
                       help="问题类型 (默认: data_inaccuracy)")
    p_fbs.add_argument("--expected", help="期望正确值")
    p_fbs.add_argument("--actual", help="实际看到的值")
    p_fbs.add_argument("--severity", default="medium", choices=["low", "medium", "high"],
                       help="严重程度 (默认: medium)")
    p_fbs.add_argument("--sql", help="相关 SQL 语句")
    p_fbs.add_argument("--database", help="数据库名")

    p_fbl = fb_sub.add_parser("list", help="查看已提交的反馈")
    p_fbl.add_argument("--limit", type=int, default=20, help="返回条数 (默认: 20)")
    p_fbl.add_argument("--status", choices=["pending", "investigating", "verified", "fixed", "rejected"],
                       help="按状态过滤")

    p_fbst = fb_sub.add_parser("status", help="查询反馈状态")
    p_fbst.add_argument("--id", required=True, help="反馈 ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    from auth_guard import require_auth
    user_info = require_auth(allow_skip=(args.command == "doctor"))
    args._user_info = user_info

    if hasattr(args, "date") and args.date:
        from datetime import datetime
        if args.date == "today":
            args.date = datetime.now().strftime("%Y-%m-%d")
        elif args.date == "yesterday":
            from datetime import timedelta
            args.date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    if args.command == "data":
        if not hasattr(args, "data_command") or not args.data_command:
            p_data.print_help()
            sys.exit(0)
        data_dispatch = {
            "sources": cmd_data_sources,
            "tables": cmd_data_tables,
            "columns": cmd_data_columns,
            "query": cmd_data_query,
            "search": cmd_data_search,
            "sql": cmd_data_sql,
            "health": cmd_data_health,
        }
        data_dispatch[args.data_command](args)
        return

    if args.command == "org":
        if not hasattr(args, "org_command") or not args.org_command:
            p_org.print_help()
            sys.exit(0)
        org_dispatch = {
            "search": cmd_org_search,
            "dept": cmd_org_dept,
            "members": cmd_org_members,
            "resolve": cmd_org_resolve,
        }
        org_dispatch[args.org_command](args)
        return

    if args.command == "feedback":
        if not hasattr(args, "feedback_command") or not args.feedback_command:
            p_fb.print_help()
            sys.exit(0)
        fb_dispatch = {
            "submit": cmd_feedback_submit,
            "list": cmd_feedback_list,
            "status": cmd_feedback_status,
        }
        fb_dispatch[args.feedback_command](args)
        return

    dispatch = {
        "doctor": cmd_doctor,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
