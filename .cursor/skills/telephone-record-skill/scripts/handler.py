#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Description: 电话录音查询工具 — 支持 7 类录音的查询、详情与统计（敏感字段已屏蔽）
# Usage: python handler.py types
# Usage: python handler.py query telsales --date 2026-03-19
# Usage: python handler.py detail telsales 43082
# Usage: python handler.py doctor

import argparse
import sys
import os

# Windows 终端 UTF-8 输出
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import RECORDING_TYPES, resolve_type
from diagnostics import CheckResult, render_report, run_runtime_checks, run_setup_checks


# ── 数据源标识 ─────────────────────────────────────

SKILL_NAME = "telephone-record-skill"
SKILL_LABEL = "📞 电话录音查询"
ENGINE = "CynosDB"


def _print_source(rtype: str = None, extra: str = None):
    """输出数据源标识行，让用户/Agent 明确数据来源"""
    parts = [f"技能: {SKILL_NAME}", f"引擎: {ENGINE}"]
    if rtype and rtype in RECORDING_TYPES:
        info = RECORDING_TYPES[rtype]
        parts.append(f"库: {info['database']}")
        parts.append(f"表: {info['table']}")
    if extra:
        parts.append(extra)
    print(f"[数据源] {' | '.join(parts)}")


def _print_feedback_hint():
    """在查询结果末尾输出反馈提示"""
    print("\n📝 如数据与实际不符，可告知我\"反馈数据问题\"提交核实请求")


# ── 子命令实现 ────────────────────────────────────


def cmd_types(args):
    """列出所有录音类型"""
    _print_source(extra=f"共 {len(RECORDING_TYPES)} 种录音类型")
    print("📋 支持的录音类型:\n")
    for key, info in RECORDING_TYPES.items():
        aliases = ", ".join(info["aliases"]) if info["aliases"] else "-"
        print(f"  {key:<14} {info['label']:<12} 别名: {aliases}")
        print(f"  {'':14} 数据库: {info['database']}.{info['table']}")
        print()


def cmd_query(args):
    """查询录音列表"""
    from recording_client import RecordingClient
    from auth_guard import check_sensitive_access

    rtype = _resolve_type(args.type)
    user_info = getattr(args, "_user_info", None)
    client = RecordingClient(can_view_sensitive=check_sensitive_access(user_info))

    try:
        total = client.count(
            rtype,
            date=args.date,
            date_start=args.date_start,
            date_end=args.date_end,
            worker_name=args.worker,
            worker_id=args.worker_id,
            member_id=args.member_id,
            keyword=args.keyword,
        )

        rows = client.query(
            rtype,
            date=args.date,
            date_start=args.date_start,
            date_end=args.date_end,
            worker_name=args.worker,
            worker_id=args.worker_id,
            member_id=args.member_id,
            keyword=args.keyword,
            limit=args.limit,
            offset=args.offset,
        )
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        sys.exit(1)
    finally:
        client.close()

    info = RECORDING_TYPES[rtype]
    _print_source(rtype)
    print(f"📋 {info['label']} 查询结果 (共 {total} 条，显示 {len(rows)} 条):\n")

    if not rows:
        print("  (无匹配记录)")
        return

    for row in rows:
        rid = row.get("id", "")
        call_time = row.get("call_time") or row.get("apply_time") or ""
        worker = row.get("worker_name") or row.get("applicant_name") or row.get("owner_name") or ""
        member = row.get("member_id") or row.get("member_name") or ""
        duration = row.get("duration") or ""

        print(f"  ID: {rid} | 时间: {call_time} | 坐席: {worker} | 会员: {member} | 时长: {duration}")
        print()
    _print_feedback_hint()


def cmd_detail(args):
    """查看录音详情"""
    from recording_client import RecordingClient
    from auth_guard import check_sensitive_access

    rtype = _resolve_type(args.type)
    user_info = getattr(args, "_user_info", None)
    client = RecordingClient(can_view_sensitive=check_sensitive_access(user_info))

    try:
        row = client.get_detail(rtype, args.id)
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        sys.exit(1)
    finally:
        client.close()

    if not row:
        print(f"❌ 未找到 {RECORDING_TYPES[rtype]['label']} ID={args.id} 的记录")
        sys.exit(1)

    info = RECORDING_TYPES[rtype]
    _print_source(rtype)
    print(f"📄 {info['label']} 详情 (ID: {args.id})\n")
    print("=" * 60)
    for k, v in row.items():
        val = str(v) if v is not None else "(空)"
        if len(val) > 200:
            print(f"  {k}:")
            print(f"    {val}")
        else:
            print(f"  {k:<35} = {val}")
    print("=" * 60)
    _print_feedback_hint()


def cmd_schema(args):
    """查看表结构"""
    from recording_client import RecordingClient

    rtype = _resolve_type(args.type)
    client = RecordingClient()  # schema 不涉及敏感字段

    try:
        schema = client.get_schema(rtype)
    except Exception as e:
        print(f"❌ 查询表结构失败: {e}")
        sys.exit(1)
    finally:
        client.close()

    info = RECORDING_TYPES[rtype]
    _print_source(rtype)
    print(f"📐 {info['label']} 表结构 ({info['database']}.{info['table']}):\n")
    for col in schema:
        null = "NULL" if col["Null"] == "YES" else "NOT NULL"
        key = f" [{col['Key']}]" if col["Key"] else ""
        print(f"  {col['Field']:<40} {col['Type']:<30} {null}{key}")


def cmd_doctor(args):
    """环境与数据库诊断"""
    setup_results = run_setup_checks()
    print(render_report(setup_results, title="安装环境检查"))

    if any(r.status == "error" for r in setup_results):
        print("\n❌ 本地环境还未准备好，先修复上面的依赖问题。")
        sys.exit(1)

    if args.setup_only:
        return

    print()
    runtime_results = run_runtime_checks()
    print(render_report(runtime_results, title="数据库连通性检查"))

    statuses = [r.status for r in runtime_results]
    if "error" in statuses:
        sys.exit(1)
    if "warning" in statuses:
        sys.exit(2)


def cmd_count(args):
    """按条件统计录音数量"""
    from recording_client import RecordingClient

    rtype = _resolve_type(args.type)
    client = RecordingClient()  # count 不涉及敏感字段

    try:
        total = client.count(
            rtype,
            date=args.date,
            date_start=args.date_start,
            date_end=args.date_end,
            worker_name=args.worker,
            worker_id=args.worker_id,
            member_id=args.member_id,
        )
    except Exception as e:
        print(f"❌ 统计失败: {e}")
        sys.exit(1)
    finally:
        client.close()

    info = RECORDING_TYPES[rtype]
    _print_source(rtype)
    print(f"📊 {info['label']} 统计结果: 共 {total} 条记录")
    _print_feedback_hint()


# ── 工具函数 ──────────────────────────────────────


def _resolve_type(name: str) -> str:
    """解析录音类型，失败时打印提示并退出"""
    key = resolve_type(name)
    if not key:
        print(f"❌ 未知录音类型: {name}")
        print("   可用类型:")
        for k, info in RECORDING_TYPES.items():
            print(f"     {k:<14} {info['label']}")
        sys.exit(1)
    return key


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
        description="电话录音查询与分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python handler.py types                                              # 列出录音类型
  python handler.py doctor                                             # 诊断环境和数据库
  python handler.py doctor --setup-only                                # 仅检查依赖
  python handler.py query telsales --date 2026-03-19                   # 查询电销录音
  python handler.py query callin --worker 张三 --limit 10              # 按坐席查400录音
  python handler.py query matchmaker --date-start 2026-03-01 --date-end 2026-03-15  # 日期范围
  python handler.py detail telsales 43082                              # 查看详情（不含录音文本/地址）
  python handler.py count telsales --date 2026-03-19                   # 统计录音数量
  python handler.py schema voicefox                                    # 查看表结构
        """)
    sub = parser.add_subparsers(dest="command")

    # types
    sub.add_parser("types", help="列出所有录音类型")

    # doctor
    p_doc = sub.add_parser("doctor", help="环境与数据库连通性诊断")
    p_doc.add_argument("--setup-only", action="store_true",
                       help="仅检查本地依赖，不检查数据库连接")

    # query
    p_query = sub.add_parser("query", help="查询录音列表")
    p_query.add_argument("type", help="录音类型 (telsales/matchmaker/callin/voicefox/callout/refund/callout_detail)")
    p_query.add_argument("--date", help="精确日期 (YYYY-MM-DD)")
    p_query.add_argument("--date-start", help="起始日期 (YYYY-MM-DD)")
    p_query.add_argument("--date-end", help="结束日期 (YYYY-MM-DD)")
    p_query.add_argument("--worker", help="坐席姓名 (模糊匹配)")
    p_query.add_argument("--worker-id", type=int, help="坐席 ID")
    p_query.add_argument("--member-id", type=int, help="会员 ID")
    p_query.add_argument("--keyword", help="转写文本关键词")
    p_query.add_argument("--limit", type=int, default=50, help="返回条数 (默认: 50)")
    p_query.add_argument("--offset", type=int, default=0, help="分页偏移 (默认: 0)")

    # detail
    p_detail = sub.add_parser("detail", help="查看录音详情")
    p_detail.add_argument("type", help="录音类型")
    p_detail.add_argument("id", type=int, help="记录 ID")

    # schema
    p_schema = sub.add_parser("schema", help="查看表结构")
    p_schema.add_argument("type", help="录音类型")

    # count
    p_count = sub.add_parser("count", help="统计录音数量")
    p_count.add_argument("type", help="录音类型")
    p_count.add_argument("--date", help="精确日期 (YYYY-MM-DD)")
    p_count.add_argument("--date-start", help="起始日期 (YYYY-MM-DD)")
    p_count.add_argument("--date-end", help="结束日期 (YYYY-MM-DD)")
    p_count.add_argument("--worker", help="坐席姓名 (模糊匹配)")
    p_count.add_argument("--worker-id", type=int, help="坐席 ID")
    p_count.add_argument("--member-id", type=int, help="会员 ID")

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

    # 日期快捷方式
    if hasattr(args, "date") and args.date:
        from datetime import datetime, timedelta
        if args.date == "today":
            args.date = datetime.now().strftime("%Y-%m-%d")
        elif args.date == "yesterday":
            args.date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

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
        "types": cmd_types,
        "doctor": cmd_doctor,
        "query": cmd_query,
        "detail": cmd_detail,
        "schema": cmd_schema,
        "count": cmd_count,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
