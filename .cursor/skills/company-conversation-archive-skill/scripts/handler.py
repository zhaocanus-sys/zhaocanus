#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Description: 企微会话存档统计分析工具 — 纯统计模式，不展示任何聊天内容
# Usage: python handler.py doctor
# Usage: python handler.py list-users
# Usage: python handler.py list-sessions --wxid zhangsan_zhenai.com
# Usage: python handler.py stats --wxid zhangsan_zhenai.com --date 2026-03-20

import argparse
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import TABLE_ARCHIVE_RECENT, TABLE_ARCHIVE_FULL
from diagnostics import CheckResult, render_report, run_all_checks


# ── 数据源标识 ─────────────────────────────────────

SKILL_NAME = "company-conversation-archive-skill"
SKILL_LABEL = "💬 企微会话存档统计"
ENGINE = "CynosDB"
DB_NAME = "zhenai_externalContact"


def _print_source(table: str = None, extra: str = None):
    parts = [f"技能: {SKILL_NAME}", f"引擎: {ENGINE}", f"库: {DB_NAME}"]
    if table:
        parts.append(f"表: {table}")
    if extra:
        parts.append(extra)
    print(f"[数据源] {' | '.join(parts)}")


def _print_feedback_hint():
    print("\n📝 如数据与实际不符，可告知我\"反馈数据问题\"提交核实请求")


# ── 子命令实现 ────────────────────────────────────


def cmd_doctor(args):
    """数据库连接与环境诊断"""
    results = run_all_checks()
    print(render_report(results, title="环境与连接诊断"))

    has_error = any(r.status == "error" for r in results)
    has_warning = any(r.status == "warning" for r in results)

    if has_error:
        sys.exit(1)
    if has_warning:
        sys.exit(2)


def cmd_list_users(args):
    """列出有会话存档的员工"""
    client = _get_client(args)

    try:
        users = client.get_archive_users(search=args.search)

        if not users:
            if args.search:
                print(f"[WARN] 没有找到匹配 \"{args.search}\" 的员工")
            else:
                print("[WARN] 没有找到有会话存档的员工")
            return

        tbl = TABLE_ARCHIVE_FULL if getattr(args, "full", False) else TABLE_ARCHIVE_RECENT
        _print_source(tbl)
        label = f"搜索 \"{args.search}\"" if args.search else "全部"
        print(f"[LIST] {label} 共 {len(users)} 名员工:\n")
        for u in users:
            wxid = u.get("wxid", "")
            user_id = u.get("userId", "")
            print(f"  wxid: {wxid:<35} | userId: {user_id}")
        _print_feedback_hint()
    except Exception as e:
        print("[ERR] 查询会话存档员工失败")
        print(f"   详情: {e}")
        sys.exit(1)
    finally:
        client.close()


def cmd_list_sessions(args):
    """列出员工的会话列表"""
    client = _get_client(args)

    try:
        sessions = client.get_sessions(args.wxid, session_type=args.type)

        tbl = TABLE_ARCHIVE_FULL if getattr(args, "full", False) else TABLE_ARCHIVE_RECENT
        _print_source(tbl)
        type_label = {"private": "私聊", "group": "群聊", "external": "全部"}
        print(f"[LIST] {type_label.get(args.type, args.type)} 会话共 {len(sessions)} 个:\n")

        for s in sessions:
            chat_id = s.get("chatId", "")
            room = s.get("roomWxid", "")
            count = s.get("msgCount", 0)
            last_time = s.get("lastMsgTimeStr", "")
            session_label = "[群聊]" if room else "[私聊]"
            print(f"  {session_label} chatId: {chat_id:<50} | 消息数: {count:<6} | 最后: {last_time}")
    except Exception as e:
        print("[ERR] 查询会话列表失败")
        print(f"   详情: {e}")
        sys.exit(1)
    finally:
        client.close()


def cmd_stats(args):
    """统计分析（纯聚合数据，不展示消息内容）"""
    from message_processor import type_label

    client = _get_client(args)
    tbl = TABLE_ARCHIVE_FULL if getattr(args, "full", False) else TABLE_ARCHIVE_RECENT
    _print_source(tbl, extra="统计分析")

    wxid = getattr(args, "wxid", None)
    date = getattr(args, "date", None)
    date_start = getattr(args, "date_start", None)
    date_end = getattr(args, "date_end", None)

    try:
        total = client.count_messages(wxid=wxid, date=date)
        print(f"\n📊 消息总数: {total}\n")

        print("── 消息类型分布 ──")
        type_stats = client.get_message_type_stats(
            wxid=wxid, date=date, date_start=date_start, date_end=date_end
        )
        for row in type_stats:
            name = type_label(row["msgType"])
            print(f"  {name:<12} {row['cnt']:>8} 条")

        print("\n── 发送人 TOP 20 ──")
        sender_stats = client.get_sender_stats(
            wxid=wxid, date=date, date_start=date_start, date_end=date_end, limit=20
        )
        for i, row in enumerate(sender_stats, 1):
            print(f"  {i:>2}. {row['sender']:<40} {row['cnt']:>6} 条")

        if date_start or date_end:
            print("\n── 每日消息趋势 ──")
            daily = client.get_daily_activity(
                wxid=wxid, date_start=date_start, date_end=date_end
            )
            for row in daily:
                d = str(row["msg_date"])
                bar = "█" * min(int(row["cnt"] / max(1, max(r["cnt"] for r in daily)) * 30), 30)
                print(f"  {d}  {bar} {row['cnt']}")

        print("\n── 小时分布 ──")
        hourly = client.get_hourly_activity(
            wxid=wxid, date=date, date_start=date_start, date_end=date_end
        )
        for row in hourly:
            h = f"{row['msg_hour']:02d}:00"
            max_cnt = max(r["cnt"] for r in hourly) if hourly else 1
            bar = "█" * min(int(row["cnt"] / max(1, max_cnt) * 30), 30)
            print(f"  {h}  {bar} {row['cnt']}")

        if wxid:
            print("\n── 会话消息分布 ──")
            session_stats = client.get_session_stats(
                wxid=wxid, date=date, date_start=date_start, date_end=date_end
            )
            for row in session_stats[:20]:
                chat_id = row.get("chat_id", "")
                room = row.get("roomWxid", "")
                label = "[群聊]" if room else "[私聊]"
                first = row.get("first_msg_str", "")
                last = row.get("last_msg_str", "")
                print(f"  {label} {chat_id:<45} {row['cnt']:>6} 条  ({first} ~ {last})")

    except Exception as e:
        print(f"[ERR] 统计查询失败: {e}")
        sys.exit(1)
    finally:
        client.close()

    _print_feedback_hint()


# ── 工具函数 ──────────────────────────────────────


def _get_client(args=None):
    from db_client import DBClient
    from auth_guard import check_sensitive_access
    use_full = getattr(args, "full", False) if args else False
    user_info = getattr(args, "_user_info", None) if args else None
    client = DBClient(
        use_full_archive=use_full,
        can_view_sensitive=check_sensitive_access(user_info),
    )
    if not client.test_connection():
        print("[ERR] 数据库连接失败")
        print("   下一步: 执行 python scripts/handler.py doctor 查看诊断结果")
        sys.exit(1)
    return client


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
        description="企微会话存档统计分析工具（纯统计模式，不展示聊天内容）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python handler.py doctor                                            # 环境诊断
  python handler.py list-users                                        # 列出有存档的员工
  python handler.py list-users --search 张三                          # 搜索员工
  python handler.py list-sessions --wxid zhangsan_zhenai.com          # 列出会话
  python handler.py stats --wxid zhangsan_zhenai.com --date 2026-03-20  # 统计分析
  python handler.py stats --date-start 2026-03-01 --date-end 2026-03-31 # 日期范围统计
        """)
    sub = parser.add_subparsers(dest="command")

    # doctor
    sub.add_parser("doctor", help="数据库连接与环境诊断")

    # list-users
    p_lu = sub.add_parser("list-users", help="列出有会话存档的员工")
    p_lu.add_argument("--search", "-s", help="按姓名/wxid/userId 搜索")
    p_lu.add_argument("--full", action="store_true", help="使用全量存档表（默认近三月）")

    # list-sessions
    p_ls = sub.add_parser("list-sessions", help="列出员工的会话")
    p_ls.add_argument("--wxid", required=True, help="员工 wxid")
    p_ls.add_argument("--type", choices=["external", "group", "private"],
                      default="external", help="会话类型 (默认: external)")
    p_ls.add_argument("--full", action="store_true", help="使用全量存档表")

    # stats
    p_stats = sub.add_parser("stats", help="统计分析（消息数量/类型/发送人/时段分布）")
    p_stats.add_argument("--wxid", help="员工 wxid（可选，不传则统计全员）")
    p_stats.add_argument("--date", help="精确日期 (YYYY-MM-DD 或 today/yesterday)")
    p_stats.add_argument("--date-start", help="起始日期 (YYYY-MM-DD)")
    p_stats.add_argument("--date-end", help="结束日期 (YYYY-MM-DD)")
    p_stats.add_argument("--full", action="store_true", help="使用全量存档表")

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

    from auth_guard import require_auth, check_team_access
    user_info = require_auth(allow_skip=(args.command == "doctor"))
    args._user_info = user_info

    if args.command != "doctor" and user_info and not check_team_access(user_info, "wechat_archive"):
        name = user_info.get("name", "未知")
        print(f"❌ 权限不足: {name} 没有访问企微会话存档的权限（需要 wechat_archive 团队）")
        sys.exit(1)

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
        "doctor": cmd_doctor,
        "list-users": cmd_list_users,
        "list-sessions": cmd_list_sessions,
        "stats": cmd_stats,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
