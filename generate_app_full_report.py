# -*- coding: utf-8 -*-
"""
APP 全量深度体检报告生成器 v2
架构：3张数据表全量解析 · 20+分析模块 · 并行API · 情景记忆
拆分：app_report_data.py(聚合) + app_report_html.py(渲染) + 本文件(主控)
"""
import sys
import datetime
from agent_system.actions.api_client import daily, query, parallel_fetch
from agent_system.actions.report_exporter import export_html
from agent_system.actions.email_sender import send_report_email

from app_report_data import (
    parse_rows, agg_app, agg_orders, agg_traffic,
    build_trend_data, APP_METRIC_LABELS,
)
from app_report_html import assemble_full_html

DATE = "20260227"
DATE_DISPLAY = "2026-02-27"


def prev_date(d):
    dt = datetime.datetime.strptime(d, "%Y%m%d") - datetime.timedelta(days=1)
    return dt.strftime("%Y%m%d")


def main():
    global DATE, DATE_DISPLAY
    if "--date" in sys.argv:
        idx = sys.argv.index("--date")
        if idx + 1 < len(sys.argv):
            DATE = sys.argv[idx + 1].replace("-", "")
            DATE_DISPLAY = f"{DATE[:4]}-{DATE[4:6]}-{DATE[6:]}"

    base_dt = datetime.datetime.strptime(DATE, "%Y%m%d")

    # ── 并行拉取全部API（3张表 + 昨日 + 10天趋势 = 14次调用并行） ──
    print(f"[APP报告v2] 并行拉取全部数据 {DATE}...")
    calls = [
        lambda: daily("app", DATE),                         # 0: 今日daily
        lambda: daily("app", prev_date(DATE)),               # 1: 昨日daily
        lambda: query("app", "orders", DATE, size=2000),     # 2: 订单表
        lambda: query("app", "traffic", DATE, size=500),     # 3: 流量表
    ]
    for delta in range(9, -1, -1):
        d = (base_dt - datetime.timedelta(days=delta)).strftime("%Y%m%d")
        calls.append(lambda d=d: daily("app", d))           # 4-13: 10天趋势

    results = parallel_fetch(calls)

    resp_today = results[0]
    resp_prev = results[1]
    resp_orders = results[2]
    resp_traffic = results[3]

    rows_today = parse_rows(resp_today)
    rows_prev = parse_rows(resp_prev)
    orders_rows = parse_rows(resp_orders)
    traffic_rows = parse_rows(resp_traffic)

    trend_rows = []
    for i, delta in enumerate(range(9, -1, -1)):
        d = (base_dt - datetime.timedelta(days=delta)).strftime("%Y%m%d")
        for row in parse_rows(results[4 + i]):
            row["ftime"] = d
            trend_rows.append(row)

    print(f"[APP报告v2] 数据: daily={len(rows_today)}行, orders={len(orders_rows)}行, "
          f"traffic={len(traffic_rows)}行, trend={len(trend_rows)}天")

    # ── 数据聚合 ──
    t = agg_app(rows_today)
    p = agg_app(rows_prev) if rows_prev else {}
    orders = agg_orders(orders_rows)
    traffic = agg_traffic(traffic_rows)
    trends = build_trend_data(trend_rows)

    if not t:
        print("[APP报告v2] 无数据，退出")
        return

    # ── HTML生成 ──
    html = assemble_full_html(t, p, orders, traffic, trends, DATE_DISPLAY)

    # ── 情景记忆 ──
    from agent_system.actions.memory_manager import ReportMemory
    mem = ReportMemory()
    save_metrics = {k: t.get(k, 0) for k in APP_METRIC_LABELS if k in t}
    mem.save("app", DATE, save_metrics)
    trend_html = mem.trend_comparison_html("app", DATE, save_metrics, APP_METRIC_LABELS)
    if trend_html:
        html = html.replace("</body></html>", trend_html + "\n</body></html>")

    # ── 导出 ──
    filename = f"APP_Full_{DATE_DISPLAY}.html"
    no_email = "--no-email" in sys.argv
    path = export_html(html, filename, open_browser=True)
    print(f"[APP报告v2] 已导出: {path} ({len(html)//1024}KB)")

    if not no_email:
        subject = f"APP全量深度体检报告 {DATE_DISPLAY}"
        ok = send_report_email(subject, html)
        print(f"[APP报告v2] 邮件: {'成功' if ok else '失败'}")
    else:
        print("[APP报告v2] 跳过邮件发送")


if __name__ == "__main__":
    main()
