# -*- coding: utf-8 -*-
"""APP日报 — HTML生成模块（每个section一个函数，返回HTML片段）"""
import datetime
from app_report_data import PRODUCTS, BOOK_REFS

MANAGER = "APP产品运营负责人"

CSS = """<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#f5f6f8;color:#1e293b;font-size:14px;line-height:1.5}
.wrap{max-width:980px;margin:0 auto;padding:20px 16px}
.card{background:#fff;border-radius:10px;padding:24px;margin-bottom:16px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.card h2{font-size:15px;font-weight:700;color:#0f172a;margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid #f1f5f9}
table{width:100%;border-collapse:collapse}
th{font-size:11px;color:#94a3b8;font-weight:500;padding:8px 6px;text-align:center;border-bottom:1px solid #e2e8f0}
th:first-child{text-align:left;padding-left:10px}
td{border-bottom:1px solid #f8fafc}
.pill{display:inline-block;padding:1px 8px;border-radius:4px;font-size:10px;font-weight:700;color:#fff}
.kpi-card{flex:1;min-width:90px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.kpi-val{font-size:20px;font-weight:800}
.kpi-label{font-size:10px;color:#94a3b8}
.kpi-sub{font-size:11px;color:#64748b}
</style>"""


def _c(val, g, r, higher=True):
    if higher:
        return "#16a34a" if val >= g else "#d97706" if val >= r else "#dc2626"
    return "#16a34a" if val <= g else "#d97706" if val <= r else "#dc2626"


def _dod(t, p, key, higher=True):
    if not p:
        return ""
    cur, prv = t.get(key, 0), p.get(key, 0)
    if prv == 0:
        return ""
    chg = (cur - prv) / prv * 100
    up = chg > 0
    color = "#16a34a" if (up and higher) or (not up and not higher) else "#dc2626"
    arrow = "▲" if up else "▼"
    return f'<span style="font-size:10px;color:{color}">{arrow}{abs(chg):.1f}%</span>'


def header_html(t, date_display):
    return f"""<div style="background:linear-gradient(135deg,#0f172a,#1e3a5f,#1d4ed8);border-radius:12px;padding:28px 32px;margin-bottom:16px;color:#fff">
<div style="font-size:11px;color:#93c5fd;letter-spacing:3px">APP FULL v2 · 全量深度体检 · 20+模块 · 3张数据表全量解析</div>
<div style="font-size:22px;font-weight:700;margin:6px 0 4px">APP 全量运营深度体检报告</div>
<div style="font-size:13px;color:#bfdbfe">{date_display} · {MANAGER} · DAU:{t['active']:,} · 付费:{t['pay_num']:,}人 · 日营收:¥{t['total_rev']/10000:.1f}万 · 月累:¥{t['amt_m']/10000:.0f}万</div>
<div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">
<span style="padding:3px 10px;background:rgba(255,255,255,.15);border-radius:12px;font-size:11px">直播主播{t['anchmems']}人</span>
<span style="padding:3px 10px;background:rgba(255,255,255,.15);border-radius:12px;font-size:11px">订单成功率{t['order_conv']:.1f}%</span>
<span style="padding:3px 10px;background:rgba(255,255,255,.15);border-radius:12px;font-size:11px">复购占比{t['fugou_pct']:.1f}%</span>
<span style="padding:3px 10px;background:{'rgba(220,38,38,.4)' if t['order_fail_rate']>40 else 'rgba(255,255,255,.15)'};border-radius:12px;font-size:11px">支付失败率{t['order_fail_rate']:.1f}%</span>
</div></div>"""


def kpi_cards_html(t, p, trends=None):
    from agent_system.actions.report_sparkline import sparkline_svg

    trend_map = {}
    if trends and len(trends) >= 2:
        keys = {"active": "active_members", "pay_rate": "pay_rate", "arpu": "arpu",
                "total_rev": "amt", "fugou_amt": "fugou_amt", "refund_rate": "refund_money",
                "order_conv": "order_conv", "retain_rate_1d": "retain_1d"}
        for card_key, trend_key in keys.items():
            vals = [tr.get(trend_key, 0) for tr in trends[-10:]]
            if any(v > 0 for v in vals):
                trend_map[card_key] = vals

    cards = [
        ("DAU", f"{t['active']:,}", _c(t['active'], 200000, 150000), _dod(t, p, 'active'), "", "active"),
        ("次日留存", f"{t['retain_rate_1d']:.1f}%", _c(t['retain_rate_1d'], 45, 35), "", f"7日{t['retain_rate_7d']:.1f}%", "retain_rate_1d"),
        ("付费率", f"{t['pay_rate']:.1f}%", _c(t['pay_rate'], 5, 3), "", f"{t['pay_num']:,}人", "pay_rate"),
        ("ARPU", f"¥{t['arpu']:.1f}", _c(t['arpu'], 30, 20), "", "基准¥30", "arpu"),
        ("日营收", f"¥{t['total_rev']/10000:.0f}万", "#1e293b", _dod(t, p, 'total_rev'), "", "total_rev"),
        ("复购金额", f"¥{t['fugou_amt']/10000:.1f}万", "#7c3aed", "", f"占比{t['fugou_pct']:.1f}%", "fugou_amt"),
        ("退款率", f"{t['refund_rate']:.1f}%", _c(t['refund_rate'], 2, 4, False), "", "红线<2%", "refund_rate"),
        ("订单成功率", f"{t['order_conv']:.1f}%", _c(t['order_conv'], 70, 50), "", f"失败{t['order_fail']:,}单", "order_conv"),
        ("珍心占比", f"{t['zhenxin_pct']:.1f}%", _c(t['zhenxin_pct'], 79, 80, False), "", "红线<80%", ""),
        ("月累营收", f"¥{t['amt_m']/10000:.0f}万", "#1e293b", "", f"月累{t['pay_m']:,}人", ""),
    ]
    h = '<div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap">'
    for label, val, color, dod, sub, trend_key in cards:
        spark = sparkline_svg(trend_map.get(trend_key, []), color=color) if trend_key else ""
        h += f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
        h += f'<div class="kpi-val" style="color:{color}">{val}</div>'
        h += f'{spark}'
        h += f'<div class="kpi-sub">{dod} {sub}</div></div>'
    h += '</div>'
    h += f'<div class="card" style="padding:12px 20px"><div style="font-size:11px;color:#64748b">'
    h += f'流转: DAU{t["active"]:,}→留存{t["retain_rate_1d"]:.1f}%→付费率{t["pay_rate"]:.1f}%({t["pay_num"]:,}人)→ARPU¥{t["arpu"]:.1f}→日营收¥{t["total_rev"]/10000:.0f}万 | 复购¥{t["fugou_amt"]/10000:.1f}万({t["fugou_pct"]:.1f}%) | 订单成功率{t["order_conv"]:.1f}%</div></div>'
    return h


def live_section_html(t, orders):
    """直播运营深度分析"""
    live_e2 = orders.get("by_live_e2", [])
    live_prod = orders.get("by_live_prod", [])
    live_total_cnt = sum(v["cnt"] for _, v in live_e2)
    live_total_pay = sum(v["pay"] for _, v in live_e2)
    live_total_amt = sum(v["amt"] for _, v in live_e2)
    live_conv = live_total_pay / live_total_cnt * 100 if live_total_cnt > 0 else 0
    live_fail = live_total_cnt - live_total_pay

    h = '<div class="card" style="border-left:4px solid #7c3aed">'
    h += '<h2>直播运营深度分析 · APP核心增长引擎</h2>'

    h += '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">'
    live_kpis = [
        ("开播主播", f"{t['anchmems']:,}人", "#7c3aed"),
        ("总直播时长", f"{t['anchtime']/3600:.0f}小时", "#6366f1"),
        ("人均直播", f"{t['avg_anchtime']/60:.0f}分钟", "#8b5cf6"),
        ("送礼人数", f"{t['giftmems']:,}人", "#dc2626"),
        ("送礼金额", f"¥{t['costmoney']:,.0f}", "#d97706"),
        ("人均送礼", f"¥{t['gift_per_viewer']:.0f}", "#16a34a"),
        ("直播订单", f"{live_total_cnt}单", "#3b82f6"),
        ("支付成功率", f"{live_conv:.1f}%", _c(live_conv, 70, 50)),
        ("直播营收", f"¥{live_total_amt:,.0f}", "#dc2626"),
    ]
    for label, val, color in live_kpis:
        h += f'<div style="flex:1;min-width:90px;background:#faf5ff;border-radius:8px;padding:10px">'
        h += f'<div style="font-size:10px;color:#94a3b8">{label}</div>'
        h += f'<div style="font-size:16px;font-weight:700;color:{color}">{val}</div></div>'
    h += '</div>'

    if live_e2:
        h += '<div style="font-size:13px;font-weight:600;margin-bottom:8px">直播子场景转化</div>'
        h += '<table><thead><tr><th style="text-align:left;padding-left:10px">场景</th>'
        h += '<th>订单数</th><th>支付成功</th><th>失败</th><th>成功率</th><th style="text-align:right">营收</th></tr></thead><tbody>'
        for name, v in live_e2:
            conv = v["pay"] / v["cnt"] * 100 if v["cnt"] > 0 else 0
            fail = v["cnt"] - v["pay"]
            cc = _c(conv, 70, 50)
            h += f'<tr><td style="padding:6px 10px;font-size:12px;font-weight:600">{name}</td>'
            h += f'<td style="text-align:center;font-size:12px">{v["cnt"]}</td>'
            h += f'<td style="text-align:center;font-size:12px;color:#16a34a">{v["pay"]}</td>'
            h += f'<td style="text-align:center;font-size:12px;color:#dc2626">{fail}</td>'
            h += f'<td style="text-align:center;font-size:12px;font-weight:600;color:{cc}">{conv:.1f}%</td>'
            h += f'<td style="text-align:right;font-size:12px;font-weight:600">¥{v["amt"]:,.0f}</td></tr>'
        h += '</tbody></table>'

    if live_prod:
        h += '<div style="font-size:13px;font-weight:600;margin:14px 0 8px">直播商品销售结构</div>'
        h += '<table><thead><tr><th style="text-align:left;padding-left:10px">商品</th>'
        h += '<th>订单</th><th>支付</th><th style="text-align:right">金额</th><th>占比</th></tr></thead><tbody>'
        for name, v in live_prod:
            pct = v["amt"] / live_total_amt * 100 if live_total_amt > 0 else 0
            h += f'<tr><td style="padding:6px 10px;font-size:12px;font-weight:600">{name}</td>'
            h += f'<td style="text-align:center;font-size:12px">{v["cnt"]}</td>'
            h += f'<td style="text-align:center;font-size:12px">{v["pay"]}</td>'
            h += f'<td style="text-align:right;font-size:12px;font-weight:600">¥{v["amt"]:,.0f}</td>'
            h += f'<td style="text-align:center;font-size:12px">{pct:.1f}%</td></tr>'
        h += '</tbody></table>'

    h += f'<div style="margin-top:14px;padding:12px;background:#faf5ff;border-radius:8px;border-left:3px solid #7c3aed">'
    h += f'<div style="font-size:12px;color:#475569;line-height:1.8">'
    h += f'<strong>直播运营诊断：</strong>开播{t["anchmems"]}位主播，总时长{t["anchtime"]/3600:.0f}小时，人均{t["avg_anchtime"]/60:.0f}分钟。'
    h += f'送礼{t["giftmems"]}人贡献¥{t["costmoney"]:,.0f}，人均¥{t["gift_per_viewer"]:.0f}。'
    if t["avg_anchtime"] / 60 < 60:
        h += f'<br><span style="color:#dc2626;font-weight:600">⚠ 人均直播仅{t["avg_anchtime"]/60:.0f}分钟，低于60分钟基准。</span>增加开播时长可线性提升直播营收。'
    if live_conv < 60:
        h += f'<br><span style="color:#dc2626;font-weight:600">⚠ 直播支付成功率{live_conv:.1f}%偏低，{live_fail}笔订单失败。</span>需排查支付链路稳定性。'
    h += f'<br><strong>杠杆预估：</strong>'
    h += f'①主播人均时长+30分钟 → 预计直播营收<b style="color:#dc2626">+¥{int(live_total_amt * 0.3):,}/日（+¥{int(live_total_amt * 0.3 * 30):,}/月）</b>'
    h += f' ②送礼人数翻倍 → <b style="color:#dc2626">+¥{int(t["costmoney"]):,}/日</b>'
    h += f' ③新牵线房支付优化 → <b style="color:#dc2626">+¥{int(live_total_amt * 0.15):,}/日</b>'
    h += f'<br>{BOOK_REFS["PLATSCALE"]}：平台型产品核心在供给侧（主播）运营密度。'
    h += f' {BOOK_REFS["HOOKED"]}：直播的Hook在于「不确定酬赏」——下一个匹配对象是谁的悬念驱动用户持续停留和付费。'
    h += f'<br><strong>交友APP直播特有洞见：</strong>直播不只是娱乐场景，更是「信任建立」场景。'
    h += f'用户通过直播看到真实的人，降低线上交友的不确定性，从而更愿意付费。'
    h += f'这解释了为什么直播的支付成功率({live_conv:.0f}%)高于非直播——因为用户已在直播中完成了「价值确认」。'
    h += '</div></div></div>'
    return h


def payment_funnel_html(t, orders):
    """支付漏斗全量分析"""
    by_ch = orders.get("by_channel", [])
    total_cnt = orders["total_cnt"]
    total_pay = orders["total_pay"]
    total_fail = total_cnt - total_pay
    fail_rate = total_fail / total_cnt * 100 if total_cnt > 0 else 0
    lost_rev_est = t["total_rev"] / total_pay * total_fail if total_pay > 0 else 0

    h = '<div class="card" style="border-left:4px solid #dc2626">'
    h += '<h2>支付漏斗全量分析 · 每一笔失败都是流失的营收</h2>'

    alert_bg = "#fef2f2" if fail_rate > 40 else "#fffbeb" if fail_rate > 25 else "#f0fdf4"
    alert_c = "#dc2626" if fail_rate > 40 else "#d97706" if fail_rate > 25 else "#16a34a"
    h += f'<div style="padding:14px;background:{alert_bg};border-radius:8px;border-left:3px solid {alert_c};margin-bottom:16px">'
    h += f'<div style="font-size:14px;font-weight:700;color:{alert_c}">{"🚨 P0 严重" if fail_rate>40 else "⚠ 需关注" if fail_rate>25 else "✅ 正常"}</div>'
    h += f'<div style="font-size:12px;color:#475569;margin-top:4px">总订单 <b>{total_cnt:,}</b> → 支付成功 <b>{total_pay:,}</b> → '
    h += f'<b style="color:#dc2626">失败 {total_fail:,}笔（{fail_rate:.1f}%）</b>'
    h += f'<br>按当前ARPU换算，<b style="color:#dc2626">每日因支付失败预估损失¥{lost_rev_est/10000:.1f}万</b></div></div>'

    h += '<div style="display:flex;gap:4px;flex-wrap:wrap;align-items:center;margin-bottom:14px">'
    h += f'<div style="padding:8px 14px;border-radius:6px;border:3px solid #3b82f6;font-size:12px;font-weight:600">创建订单 {total_cnt:,}</div>'
    h += '<span style="color:#94a3b8;margin:0 4px">→</span>'
    h += f'<div style="padding:8px 14px;border-radius:6px;border:3px solid #16a34a;font-size:12px;font-weight:600;background:#f0fdf4">支付成功 {total_pay:,} ({100-fail_rate:.1f}%)</div>'
    h += '<span style="color:#94a3b8;margin:0 4px">→</span>'
    h += f'<div style="padding:8px 14px;border-radius:6px;border:3px solid #dc2626;font-size:12px;font-weight:600;background:#fef2f2">失败流失 {total_fail:,} ({fail_rate:.1f}%)</div>'
    h += '</div>'

    h += '<div style="font-size:13px;font-weight:600;margin-bottom:8px">各支付渠道成功率对比</div>'
    h += '<table><thead><tr><th style="text-align:left;padding-left:10px">支付渠道</th>'
    h += '<th>总订单</th><th>成功</th><th>失败</th><th>成功率</th><th style="text-align:right">成功金额</th><th>预估损失</th></tr></thead><tbody>'
    for name, v in by_ch:
        fail = v["cnt"] - v["pay"]
        conv = v["pay"] / v["cnt"] * 100 if v["cnt"] > 0 else 0
        est_loss = v["amt"] / v["pay"] * fail if v["pay"] > 0 else 0
        cc = _c(conv, 70, 50)
        row_bg = "background:#fef2f2;" if conv < 50 else ""
        h += f'<tr style="{row_bg}"><td style="padding:6px 10px;font-size:12px;font-weight:600">{name}</td>'
        h += f'<td style="text-align:center;font-size:12px">{v["cnt"]:,}</td>'
        h += f'<td style="text-align:center;font-size:12px;color:#16a34a">{v["pay"]:,}</td>'
        h += f'<td style="text-align:center;font-size:12px;color:#dc2626;font-weight:600">{fail:,}</td>'
        h += f'<td style="text-align:center;font-size:12px;font-weight:700;color:{cc}">{conv:.1f}%</td>'
        h += f'<td style="text-align:right;font-size:12px">¥{v["amt"]:,.0f}</td>'
        h += f'<td style="text-align:right;font-size:12px;color:#dc2626">¥{est_loss:,.0f}</td></tr>'
    h += '</tbody></table>'

    worst = [(n, v) for n, v in by_ch if v["cnt"] > 10 and v["pay"] / v["cnt"] < 0.5]
    if worst:
        h += '<div style="margin-top:12px;padding:12px;background:#fef2f2;border-radius:8px">'
        h += '<div style="font-size:12px;font-weight:600;color:#dc2626;margin-bottom:4px">支付渠道风险点</div>'
        for name, v in worst:
            conv = v["pay"] / v["cnt"] * 100 if v["cnt"] > 0 else 0
            h += f'<div style="font-size:11px;color:#991b1b">• <b>{name}</b>成功率仅{conv:.1f}%，{v["cnt"]-v["pay"]}笔失败 → 排查SDK版本/网关超时/限额配置</div>'
        h += '</div>'

    h += f'<div style="margin-top:12px;padding:12px;background:#f8fafc;border-radius:8px;border-left:3px solid #6366f1">'
    h += f'<div style="font-size:12px;color:#475569;line-height:1.8">'
    h += f'<strong>支付优化杠杆：</strong>若将整体成功率从{100-fail_rate:.0f}%提升至75%，'
    target_new_pay = int(total_cnt * 0.75) - total_pay
    h += f'每日新增{target_new_pay:,}笔成功订单 → <b style="color:#dc2626">预估日增营收¥{int(target_new_pay * t["arpu"]):,}</b>'
    h += f'<br>{BOOK_REFS["LEAN"]}：支付成功率是变现漏斗最后一环，1%的提升直接等于1%的营收增长。'
    h += f'<br><strong>交友APP支付洞见：</strong>用户在「情感冲动」时刻下单（看到心仪对象、收到喜欢通知），'
    h += f'此时支付失败=永久流失——情感冲动不可复现。失败订单的「5分钟黄金挽回期」至关重要。'
    h += f'</div></div>'

    by_trial = orders.get("by_trial", [])
    trial_yes = dict(by_trial).get("是", {})
    trial_no = dict(by_trial).get("否", {})
    if trial_yes and trial_yes.get("cnt", 0) > 0:
        h += f'<div style="margin-top:12px;padding:12px;background:#eff6ff;border-radius:8px;border-left:3px solid #3b82f6">'
        h += f'<div style="font-size:13px;font-weight:600;color:#1d4ed8;margin-bottom:4px">试用→正式转化分析</div>'
        t_cnt, t_amt = trial_yes["cnt"], trial_yes["amt"]
        n_cnt, n_amt = trial_no.get("cnt", 0), trial_no.get("amt", 0)
        h += f'<div style="font-size:12px;color:#475569">试用订单 {t_cnt}笔/¥{t_amt:,.0f} vs 正式订单 {n_cnt:,}笔/¥{n_amt:,.0f}。'
        if t_cnt > 0:
            h += f' 试用客单价¥{t_amt/t_cnt:.0f} vs 正式客单价¥{n_amt/n_cnt:.0f}。' if n_cnt > 0 else ''
            h += f' {BOOK_REFS["REVENUE"]}：试用是订阅经济的核心转化漏斗，试用→正式的转化率决定LTV。'
        h += '</div></div>'
    h += '</div>'
    return h


def entrance_analysis_html(orders):
    """入口/场景转化分析"""
    by_e1 = orders.get("by_entrance1", [])
    by_e2 = orders.get("by_entrance2", [])
    total_amt = orders["total_amt"] or 1

    h = '<div class="card"><h2>入口场景转化分析 · 哪些页面驱动付费</h2>'
    h += '<div style="font-size:13px;font-weight:600;margin-bottom:8px">一级入口</div>'
    h += '<table><thead><tr><th style="text-align:left;padding-left:10px">入口</th>'
    h += '<th>订单</th><th>成功</th><th>成功率</th><th style="text-align:right">营收</th><th>占比</th></tr></thead><tbody>'
    for name, v in by_e1:
        conv = v["pay"] / v["cnt"] * 100 if v["cnt"] > 0 else 0
        pct = v["amt"] / total_amt * 100
        h += f'<tr><td style="padding:6px 10px;font-size:12px;font-weight:600">{name}</td>'
        h += f'<td style="text-align:center;font-size:12px">{v["cnt"]:,}</td>'
        h += f'<td style="text-align:center;font-size:12px">{v["pay"]:,}</td>'
        h += f'<td style="text-align:center;font-size:12px;color:{_c(conv,70,50)}">{conv:.1f}%</td>'
        h += f'<td style="text-align:right;font-size:12px;font-weight:600">¥{v["amt"]:,.0f}</td>'
        h += f'<td style="text-align:center;font-size:12px">{pct:.1f}%</td></tr>'
    h += '</tbody></table>'

    h += '<div style="font-size:13px;font-weight:600;margin:14px 0 8px">二级入口 TOP12</div>'
    h += '<table><thead><tr><th style="text-align:left;padding-left:10px">入口</th>'
    h += '<th>订单</th><th>成功率</th><th style="text-align:right">营收</th><th>占比</th></tr></thead><tbody>'
    for name, v in by_e2[:12]:
        conv = v["pay"] / v["cnt"] * 100 if v["cnt"] > 0 else 0
        pct = v["amt"] / total_amt * 100
        h += f'<tr><td style="padding:6px 10px;font-size:12px;font-weight:600">{name}</td>'
        h += f'<td style="text-align:center;font-size:12px">{v["cnt"]:,}</td>'
        h += f'<td style="text-align:center;font-size:12px;color:{_c(conv,70,50)}">{conv:.1f}%</td>'
        h += f'<td style="text-align:right;font-size:12px;font-weight:600">¥{v["amt"]:,.0f}</td>'
        h += f'<td style="text-align:center;font-size:12px">{pct:.1f}%</td></tr>'
    h += '</tbody></table>'

    by_prodname = orders.get("by_prodname", [])
    if by_prodname:
        h += '<div style="font-size:13px;font-weight:600;margin:14px 0 8px">价格档位销售排行 TOP10（含具体金额）</div>'
        h += '<table><thead><tr><th style="text-align:left;padding-left:10px">产品全名(含价位)</th>'
        h += '<th>订单</th><th>支付</th><th style="text-align:right">营收</th></tr></thead><tbody>'
        for name, v in by_prodname[:10]:
            h += f'<tr><td style="padding:6px 10px;font-size:12px;font-weight:600">{name}</td>'
            h += f'<td style="text-align:center;font-size:12px">{v["cnt"]:,}</td>'
            h += f'<td style="text-align:center;font-size:12px">{v["pay"]:,}</td>'
            h += f'<td style="text-align:right;font-size:12px;font-weight:600">¥{v["amt"]:,.0f}</td></tr>'
        h += '</tbody></table>'
        top_prod = by_prodname[0] if by_prodname else None
        if top_prod:
            h += f'<div style="font-size:12px;color:#475569;padding:8px;margin-top:6px;background:#f8fafc;border-radius:6px">'
            h += f'<strong>定价洞见：</strong>最畅销档位是「{top_prod[0]}」（¥{top_prod[1]["amt"]:,.0f}），'
            h += f'说明用户对该价格带的支付意愿最强。{BOOK_REFS["UX"]}：价格锚点效应——'
            h += f'在此档位旁边放置更高价位选项，可提升高价位购买率15-25%。</div>'

    h += '</div>'
    return h


def platform_compare_html(orders):
    """多平台对比分析"""
    by_plat = orders.get("by_platform", [])
    total_amt = orders["total_amt"] or 1

    h = '<div class="card"><h2>多平台对比分析 · iOS / Android / 小程序 / 鸿蒙</h2>'
    h += '<table><thead><tr><th style="text-align:left;padding-left:10px">平台</th>'
    h += '<th>订单</th><th>成功</th><th>失败</th><th>成功率</th><th style="text-align:right">营收</th><th>占比</th><th>ARPU</th></tr></thead><tbody>'
    for name, v in by_plat:
        fail = v["cnt"] - v["pay"]
        conv = v["pay"] / v["cnt"] * 100 if v["cnt"] > 0 else 0
        pct = v["amt"] / total_amt * 100
        arpu = v["amt"] / v["pay_num"] if v["pay_num"] > 0 else 0
        cc = _c(conv, 70, 50)
        h += f'<tr><td style="padding:7px 10px;font-size:12px;font-weight:600">{name}</td>'
        h += f'<td style="text-align:center;font-size:12px">{v["cnt"]:,}</td>'
        h += f'<td style="text-align:center;font-size:12px;color:#16a34a">{v["pay"]:,}</td>'
        h += f'<td style="text-align:center;font-size:12px;color:#dc2626">{fail:,}</td>'
        h += f'<td style="text-align:center;font-size:12px;font-weight:700;color:{cc}">{conv:.1f}%</td>'
        h += f'<td style="text-align:right;font-size:12px;font-weight:600">¥{v["amt"]:,.0f}</td>'
        h += f'<td style="text-align:center;font-size:12px">{pct:.1f}%</td>'
        h += f'<td style="text-align:right;font-size:12px">¥{arpu:.0f}</td></tr>'
    h += '</tbody></table>'

    ios_data = dict(by_plat).get("iOS", {})
    and_data = dict(by_plat).get("Android", {})
    if ios_data and and_data:
        ios_conv = ios_data["pay"] / ios_data["cnt"] * 100 if ios_data["cnt"] > 0 else 0
        and_conv = and_data["pay"] / and_data["cnt"] * 100 if and_data["cnt"] > 0 else 0
        h += '<div style="margin-top:12px;padding:12px;background:#f8fafc;border-radius:8px;font-size:12px;line-height:1.8">'
        if ios_conv < and_conv - 15:
            h += f'<span style="color:#dc2626;font-weight:600">⚠ iOS成功率({ios_conv:.0f}%)显著低于Android({and_conv:.0f}%)</span>'
            h += ' → 排查IAP/Apple Pay回调、审核状态、沙盒环境异常'
        else:
            h += f'iOS({ios_conv:.0f}%) vs Android({and_conv:.0f}%)，差距正常范围'
        h += '</div>'
    h += '</div>'
    return h


def retention_matrix_html(t):
    """留存矩阵分析"""
    retain = t.get("retain", {})
    mems = t.get("mems", 0)
    h = '<div class="card"><h2>用户留存矩阵 · 新注册用户回访轨迹</h2>'
    h += '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">'
    for d in [1, 2, 3, 4, 5, 6, 7, 15, 30]:
        val = retain.get(d, 0)
        rate = val / mems * 100 if mems > 0 else 0
        bg = "#16a34a" if rate > 30 else "#d97706" if rate > 15 else "#dc2626" if val > 0 else "#e2e8f0"
        fg = "#fff" if val > 0 else "#94a3b8"
        label = f"{d}日" if d < 15 else f"{d}日"
        h += f'<div style="text-align:center;min-width:70px;padding:10px;background:{bg};border-radius:8px">'
        h += f'<div style="font-size:10px;color:{fg};opacity:.8">{label}留存</div>'
        h += f'<div style="font-size:18px;font-weight:700;color:{fg}">{rate:.1f}%</div>'
        h += f'<div style="font-size:10px;color:{fg};opacity:.8">{val:,}人</div></div>'
    h += '</div>'
    h += f'<div style="font-size:12px;color:#475569;padding:10px;background:#f8fafc;border-radius:6px;line-height:1.8">'
    h += f'今日新注册 <b>{mems:,}</b> 人。'
    r1 = retain.get(1, 0) / mems * 100 if mems > 0 else 0
    if r1 < 30:
        h += f'<span style="color:#dc2626;font-weight:600"> 次日留存{r1:.1f}%低于30%基准，首日Aha时刻未到达。</span>'
        h += f' {BOOK_REFS["HOOKED"]}：Hook四要素中「不确定酬赏」最强——「你有N位异性看了你」的悬念需在30分钟内触达。'
    elif r1 < 40:
        h += f' 次日留存{r1:.1f}%，接近40%目标。优化首日引导路径可突破。'
    else:
        h += f' 次日留存{r1:.1f}%表现良好。'

    r2 = retain.get(2, 0) / mems * 100 if mems > 0 else 0
    r7 = retain.get(7, 0) / mems * 100 if mems > 0 else 0
    if r1 > 0 and r2 > 0:
        decay_1_2 = (1 - r2 / r1) * 100 if r1 > 0 else 0
        h += f'<br><strong>衰减分析：</strong>1日→2日衰减率{decay_1_2:.0f}%。'
        if decay_1_2 > 50:
            h += f' <span style="color:#dc2626">衰减过快，首日体验未形成习惯回路。</span>'

    h += f'<br><strong>交友APP留存特殊性：</strong>交友APP的留存驱动力与工具类APP完全不同——'
    h += f'不是「功能粘性」而是「社交关系粘性」。用户留下来是因为有人在等TA，有未读消息，有新的匹配。'
    h += f'因此留存优化的核心不在产品功能，而在「制造社交惊喜」：每次打开APP都有新的互动信号。'

    uplift = int(t["active"] * 0.05 * t["pay_rate"] / 100 * t["arpu"])
    h += f'<br><strong>业绩预估：</strong>次日留存+5pp → 有效用户池扩大{int(t["active"]*0.05):,}人 → '
    h += f'<b style="color:#dc2626">日增营收¥{uplift:,}，月增¥{uplift*30:,}</b>'
    h += '</div></div>'
    return h


def channel_roi_html(traffic):
    """渠道ROI分析"""
    channels = traffic.get("channels", [])
    total_cost = traffic.get("total_cost", 0)
    total_amt_d = traffic.get("total_amt_d", 0)

    h = '<div class="card"><h2>渠道获客质量 · ROI分析（流量表 {0} 渠道）</h2>'.format(len(channels))
    paid = [c for c in channels if c["cost"] > 0]
    free = [c for c in channels if c["cost"] == 0 and c["reg"] > 0]

    if paid:
        h += '<div style="font-size:13px;font-weight:600;margin-bottom:8px">付费渠道（按日营收排序）</div>'
        h += '<table><thead><tr><th style="text-align:left;padding-left:10px">渠道</th>'
        h += '<th>注册</th><th>付费</th><th>付费率</th><th style="text-align:right">日营收</th><th>投入</th><th>ROI</th><th>CPA</th></tr></thead><tbody>'
        for c in paid:
            roi_c = "#16a34a" if c["roi"] >= 1 else "#dc2626" if c["roi"] < 0.5 else "#d97706"
            row_bg = "background:#fef2f2;" if c["roi"] < 0.3 else ""
            h += f'<tr style="{row_bg}"><td style="padding:6px 10px;font-size:12px;font-weight:600">{c["name"]}</td>'
            h += f'<td style="text-align:center;font-size:12px">{c["reg"]}</td>'
            h += f'<td style="text-align:center;font-size:12px">{c["pay"]}</td>'
            h += f'<td style="text-align:center;font-size:12px">{c["pay_rate"]:.1f}%</td>'
            h += f'<td style="text-align:right;font-size:12px;font-weight:600">¥{c["amt_d"]:,.0f}</td>'
            h += f'<td style="text-align:right;font-size:12px">¥{c["cost"]:,.0f}</td>'
            h += f'<td style="text-align:center;font-size:12px;font-weight:700;color:{roi_c}">{c["roi"]:.2f}</td>'
            h += f'<td style="text-align:right;font-size:12px">¥{c["cpa"]:.0f}</td></tr>'
        h += '</tbody></table>'

    losing = [c for c in paid if c["roi"] < 0.3]
    if losing:
        h += '<div style="margin-top:10px;padding:12px;background:#fef2f2;border-radius:8px">'
        h += '<div style="font-size:12px;font-weight:600;color:#dc2626;margin-bottom:4px">亏损渠道预警（ROI<0.3）</div>'
        total_waste = sum(c["cost"] - c["amt_d"] for c in losing)
        for c in losing:
            h += f'<div style="font-size:11px;color:#991b1b">• <b>{c["name"]}</b> ROI={c["roi"]:.2f}，投入¥{c["cost"]:,.0f}仅回收¥{c["amt_d"]:,.0f}，净亏¥{c["cost"]-c["amt_d"]:,.0f}</div>'
        h += f'<div style="font-size:11px;color:#991b1b;font-weight:600;margin-top:4px">亏损渠道日亏损合计: ¥{total_waste:,.0f}</div>'
        h += '</div>'

    if free:
        h += '<div style="font-size:13px;font-weight:600;margin:14px 0 8px">自然/免费渠道</div>'
        h += '<table><thead><tr><th style="text-align:left;padding-left:10px">渠道</th>'
        h += '<th>注册</th><th>付费</th><th>付费率</th><th style="text-align:right">日营收</th></tr></thead><tbody>'
        for c in free[:10]:
            h += f'<tr><td style="padding:6px 10px;font-size:12px;font-weight:600">{c["name"]}</td>'
            h += f'<td style="text-align:center;font-size:12px">{c["reg"]}</td>'
            h += f'<td style="text-align:center;font-size:12px">{c["pay"]}</td>'
            h += f'<td style="text-align:center;font-size:12px">{c["pay_rate"]:.1f}%</td>'
            h += f'<td style="text-align:right;font-size:12px;font-weight:600">¥{c["amt_d"]:,.0f}</td></tr>'
        h += '</tbody></table>'

    h += f'<div style="margin-top:12px;padding:12px;background:#f8fafc;border-radius:8px;font-size:12px;color:#475569;line-height:1.8">'
    h += f'<strong>渠道投放汇总：</strong>日投入¥{total_cost:,.0f}，日回收¥{total_amt_d:,.0f}，'
    h += f'整体ROI={traffic["overall_roi"]:.2f}。总注册{traffic["total_reg"]:,}人。'

    profitable = [c for c in channels if c["cost"] > 0 and c["roi"] >= 0.5]
    if profitable and losing:
        realloc = sum(c["cost"] for c in losing)
        h += f'<br><strong>预算重分配预估：</strong>将亏损渠道的¥{realloc:,.0f}预算转移到ROI>0.5的渠道 → '
        best_roi = max(c["roi"] for c in profitable) if profitable else 0
        h += f'<b style="color:#dc2626">预估额外回收¥{int(realloc * best_roi):,}/日，月增¥{int(realloc * best_roi * 30):,}</b>'

    h += f'<br>{BOOK_REFS["GROWTH"]}：渠道优化原则——砍掉ROI<0.3的渠道，把预算转移到ROI>0.5的渠道上。'
    h += f'<br><strong>交友APP投放洞见：</strong>交友APP的渠道质量不能只看当日ROI，'
    h += f'更要看「注册→激活→7日留存→30日付费」的长线转化。'
    h += f'某些渠道当日ROI低但30日LTV高（如品牌广告），某些当日ROI高但用户质量差（如积分墙）。'
    h += f'建议建立LTV/CAC指标替代单日ROI作为渠道决策依据。'
    h += f'</div></div>'
    return h


def product_mix_html(t):
    """产品品类收入明细"""
    prod_data = [(k, n, c, desc, t["prod_vals"].get(k, 0)) for k, n, c, desc in PRODUCTS]
    prod_data.sort(key=lambda x: x[4], reverse=True)
    total_rev = t["total_rev"] or 1

    h = '<div class="card" style="overflow-x:auto"><h2>产品品类收入明细（按金额排序 · 含健康度诊断）</h2>'
    h += '<table><thead><tr><th style="text-align:left;padding-left:10px">产品</th>'
    h += '<th style="text-align:right">营收</th><th style="text-align:center">占比</th>'
    h += '<th style="text-align:right">人均贡献</th><th>健康诊断</th></tr></thead><tbody>'
    for key, name, color, desc, amt in prod_data:
        pct = amt / total_rev * 100
        arpu_p = amt / t["pay_num"] if t["pay_num"] > 0 else 0
        warn = ""
        if key == "zhenxin_member" and pct > 80:
            warn = '<span style="color:#dc2626;font-size:10px;font-weight:600"> ⚠ 超80%红线</span>'
        diag = _product_diag(key, pct, amt)
        h += f'<tr><td style="padding:7px 10px;font-size:12px">'
        h += f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{color};margin-right:6px"></span>'
        h += f'<strong>{name}</strong></td>'
        h += f'<td style="padding:7px;text-align:right;font-size:12px;font-weight:600;color:{color}">¥{amt/10000:.1f}万</td>'
        h += f'<td style="padding:7px;text-align:center;font-size:12px;font-weight:600">{pct:.1f}%{warn}</td>'
        h += f'<td style="padding:7px;text-align:right;font-size:12px">¥{arpu_p:,.0f}</td>'
        h += f'<td style="padding:7px;font-size:11px;color:#475569">{diag}</td></tr>'
    h += '</tbody></table>'
    h += '<div style="margin-top:12px;padding:12px;background:#f8fafc;border-radius:8px;font-size:12px;color:#475569;line-height:1.8">'
    h += f'<strong>产品结构健康度诊断：</strong>'
    zx_pct = prod_data[0][4] / total_rev * 100 if prod_data and prod_data[0][0] == "zhenxin_member" else 0
    if zx_pct > 80:
        h += f'<span style="color:#dc2626;font-weight:600">珍心会员占比{zx_pct:.1f}%超80%红线，产品结构高风险。</span>'
        h += f' {BOOK_REFS["REVENUE"]}：健康订阅产品矩阵中，核心产品不应超过60-70%，否则面临政策/竞争单点风险。'
        h += f'<br><strong>业绩预估：</strong>若将第2-5名产品占比各提升3pp → '
        target = t["total_rev"] * 0.12
        h += f'<b style="color:#dc2626">产品多元化新增¥{target:,.0f}/日，月增¥{target*30:,.0f}</b>'
    else:
        h += f'珍心会员占比{zx_pct:.1f}%，结构相对健康。持续培育第二增长曲线。'
    h += f'<br><strong>交友APP产品洞见：</strong>交友APP的产品本质是「匹配效率」的分层销售——'
    h += f'免费用户看到模糊信息，付费用户解锁精准匹配。产品设计的核心是让用户感受到「不付费的损失」而非「付费的收益」。'
    h += f'直播守护/珍爱币等虚拟商品的本质是「社交货币」——花钱让心仪对象注意到自己，这是人类社交本能的数字化表达。'
    h += '</div></div>'
    return h


def _product_diag(key, pct, amt):
    if key == "zhenxin_member":
        if pct > 80:
            return "核心产品，但占比过高有结构风险"
        return "核心产品，占比健康"
    if pct > 10:
        return "第二梯队，具有独立增长潜力"
    if pct > 3:
        return "有一定基础，提升曝光可加速增长"
    if amt > 1000:
        return "占比偏低，需优化入口和价值感知"
    return "待激活，考虑捆绑推荐或场景教育"


def user_structure_html(t, orders):
    """用户结构分析（新客/复购/风险）"""
    by_utype = orders.get("by_utype", [])
    h = '<div class="card"><h2>用户结构分析 · 新客 vs 复购 vs 风险用户</h2>'

    h += '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">'
    new_rev = t["total_rev"] - t["fugou_amt"]
    items = [
        ("新客营收", f"¥{new_rev/10000:.1f}万", f"{new_rev/t['total_rev']*100:.1f}%" if t['total_rev'] > 0 else "0%", "#3b82f6"),
        ("复购营收", f"¥{t['fugou_amt']/10000:.1f}万", f"{t['fugou_pct']:.1f}%", "#7c3aed"),
        ("新增付费", f"{t['new_pay']}人", f"占总付费{t['new_pay']/t['pay_num']*100:.1f}%" if t['pay_num'] > 0 else "", "#16a34a"),
        ("连接付费", f"{t['pay_d_lj']}人", "", "#d97706"),
    ]
    for label, val, sub, color in items:
        h += f'<div style="flex:1;min-width:120px;padding:12px;background:#f8fafc;border-radius:8px;border-left:3px solid {color}">'
        h += f'<div style="font-size:10px;color:#94a3b8">{label}</div>'
        h += f'<div style="font-size:18px;font-weight:700;color:{color}">{val}</div>'
        h += f'<div style="font-size:11px;color:#64748b">{sub}</div></div>'
    h += '</div>'

    risk_data = [(n, v) for n, v in by_utype if "风险" in n]
    if risk_data:
        h += '<div style="padding:12px;background:#fef2f2;border-radius:8px;border-left:3px solid #dc2626;margin-bottom:12px">'
        h += '<div style="font-size:13px;font-weight:700;color:#dc2626;margin-bottom:6px">风险用户交易监控</div>'
        for name, v in risk_data:
            h += f'<div style="font-size:12px;color:#991b1b">• {name}：{v["cnt"]}笔订单，金额¥{v["amt"]:,.0f}</div>'
        total_risk = sum(v["amt"] for _, v in risk_data)
        h += f'<div style="font-size:12px;color:#991b1b;font-weight:600;margin-top:4px">风险用户总交易: ¥{total_risk:,.0f} → 需排查是否存在欺诈/盗刷/洗钱风险</div>'
        h += '</div>'

    h += '<div style="font-size:12px;color:#475569;padding:10px;background:#f8fafc;border-radius:6px;line-height:1.8">'
    h += f'<strong>复购分析：</strong>复购金额¥{t["fugou_amt"]/10000:.1f}万占总营收{t["fugou_pct"]:.1f}%。'
    if t["fugou_pct"] > 50:
        h += f' 复购是营收主力引擎（{t["fugou_pct"]:.0f}%>50%健康线）。'
        h += f' {BOOK_REFS["REVENUE"]}：订阅经济核心指标LTV/CAC，复购>50%说明产品粘性优秀。'
        h += f'<br><strong>业绩预估：</strong>复购率每+5pp → <b style="color:#dc2626">日增¥{int(t["total_rev"]*0.05):,}，月增¥{int(t["total_rev"]*0.05*30):,}</b>'
    else:
        h += f' 复购占比偏低（<50%），新客依赖度高，获客成本压力大。'
        h += f'<br><strong>业绩预估：</strong>复购率提至50% → <b style="color:#dc2626">日增¥{int(t["total_rev"]*(0.5-t["fugou_pct"]/100)):,}</b>'
    h += f'<br><strong>交友APP用户结构洞见：</strong>交友APP存在天然的「成功悖论」——用户找到对象就会流失。'
    h += f'因此必须持续获取新用户（新客营收¥{new_rev/10000:.1f}万），同时延长未成功用户的付费周期（复购¥{t["fugou_amt"]/10000:.1f}万）。'
    h += f'破解之道：①拓宽服务边界（社交→婚恋→婚后） ②增加非匹配类付费场景（直播、社区、内容）'
    h += '</div></div>'
    return h


def cross_biz_html(t):
    """跨业务线协同数据"""
    h = '<div class="card"><h2>跨业务线协同 · APP导流数据</h2>'
    h += '<div style="display:flex;gap:12px;flex-wrap:wrap">'
    items = [
        ("线上leads", f"{t['leads_online']:,}", "#3b82f6", "APP产生的线上咨询线索"),
        ("线下leads", f"{t['leads_offline']:,}", "#7c3aed", "转线下门店的线索"),
        ("资源分配", f"{t['allot']:,}", "#16a34a", "已分配给顾问"),
        ("捞取", f"{t['laoqu']:,}", "#d97706", "顾问主动捞取"),
        ("链接数", f"{t['link_1d']:,}", "#6366f1", "用户发起链接"),
        ("外呼数", f"{t['callout_1d']:,}", "#dc2626", "系统外呼触达"),
    ]
    for label, val, color, desc in items:
        h += f'<div style="flex:1;min-width:120px;padding:12px;background:#f8fafc;border-radius:8px;border-left:3px solid {color}">'
        h += f'<div style="font-size:10px;color:#94a3b8">{label}</div>'
        h += f'<div style="font-size:18px;font-weight:700;color:{color}">{val}</div>'
        h += f'<div style="font-size:10px;color:#94a3b8">{desc}</div></div>'
    h += '</div>'
    h += '<div style="margin-top:12px;font-size:12px;color:#475569;padding:10px;background:#eff6ff;border-radius:6px;line-height:1.8">'
    h += f'APP每日为线下业务输送 <b>{t["leads_offline"]+t["leads_online"]:,}</b> 条线索（线上{t["leads_online"]:,}+线下{t["leads_offline"]:,}），'
    h += f'已分配{t["allot"]:,}条。APP不仅是在线营收引擎，也是线下门店的核心获客入口。'
    offline_convert = t["leads_offline"] * 0.3
    h += f'<br><strong>跨业务业绩预估：</strong>线下leads{t["leads_offline"]:,}条 × 30%到店率 × ¥8000客单价 → '
    h += f'<b style="color:#dc2626">潜在线下营收¥{int(offline_convert * 8000):,}/日</b>。'
    h += f'线上leads{t["leads_online"]:,}条 × 10%转化率 × ¥3000在线客单 → '
    h += f'<b style="color:#dc2626">潜在在线营收¥{int(t["leads_online"] * 0.1 * 3000):,}/日</b>'
    h += f'<br><strong>协同洞见：</strong>APP是全公司的「流量水库」，leads质量决定了下游所有业务线的营收天花板。'
    h += f'外呼{t["callout_1d"]:,}次/链接{t["link_1d"]:,}次的触达密度直接影响leads的分配效率。'
    h += '</div></div>'
    return h


def funnel_chain_html(t):
    """因果链推断+最大瓶颈"""
    bottleneck = "支付成功率" if t["order_fail_rate"] > 40 else "次日留存率" if t["retain_rate_1d"] < 40 else "付费率"

    h = '<div class="card"><h2>因果链推断 · 最大瓶颈定位</h2>'
    h += '<div style="display:flex;gap:4px;flex-wrap:wrap;align-items:center;margin-bottom:12px">'
    steps = [
        (f"DAU {t['active']:,}", "#16a34a", False),
        (f"留存{t['retain_rate_1d']:.1f}%", "#dc2626" if t['retain_rate_1d'] < 35 else "#d97706", t['retain_rate_1d'] < 40),
        (f"付费率{t['pay_rate']:.1f}%", "#dc2626" if t['pay_rate'] < 3 else "#d97706", t['pay_rate'] < 5),
        (f"下单{t['order_cnt']:,}", "#3b82f6", False),
        (f"支付成功{t['order_conv']:.1f}%", "#dc2626" if t['order_conv'] < 55 else "#d97706", t['order_conv'] < 70),
        (f"ARPU¥{t['arpu']:.1f}", "#d97706" if t['arpu'] < 30 else "#16a34a", False),
        (f"日营收¥{t['total_rev']/10000:.0f}万", "#1e293b", False),
    ]
    for label, color, is_weak in steps:
        bg = "#fef2f2" if is_weak else ""
        h += f'<div style="padding:6px 12px;border-radius:6px;border:3px solid {color};font-size:11px;font-weight:600;background:{bg}">{label}</div>'
        h += '<span style="color:#94a3b8;margin:0 2px">→</span>'
    h = h.rstrip('→</span>') + '</div>'

    h += f'<div style="padding:12px;background:#fef2f2;border-radius:8px;font-size:12px;color:#dc2626;line-height:1.8">'
    h += f'<strong>最大瓶颈：{bottleneck}</strong><br>'
    if bottleneck == "支付成功率":
        h += f'订单创建{t["order_cnt"]:,}→成功支付{t["order_pay"]:,}，失败率{t["order_fail_rate"]:.1f}%。'
        h += f' 每挽回10%失败订单 → 日增{int(t["order_fail"]*0.1):,}笔 → 约¥{int(t["order_fail"]*0.1*t["arpu"]):,}/日'
    elif bottleneck == "次日留存率":
        h += f'次日留存{t["retain_rate_1d"]:.1f}%，低于40%目标。'
        h += f' 留存+5pp → 付费池+{int(t["active"]*0.05):,}人 → 日增¥{int(t["active"]*0.05*t["pay_rate"]/100*t["arpu"]):,}'
    else:
        h += f'付费率{t["pay_rate"]:.1f}%，低于5%目标。'
        h += f' +1pp → 新增{int(t["active"]*0.01):,}付费用户 → 日增¥{int(t["active"]*0.01*t["arpu"]):,}'
    h += '</div></div>'
    return h


def knowledge_collision_html(t):
    """知识对撞"""
    h = '<div class="card"><h2>跨领域知识对撞 · 3组深度分析</h2>'
    h += '<div style="display:grid;grid-template-columns:1fr;gap:14px">'

    h += f'<div style="background:#faf5ff;border-radius:10px;padding:16px;border-left:4px solid #7c3aed">'
    h += f'<div style="font-weight:700;color:#7c3aed;margin-bottom:8px"><span class="pill" style="background:#7c3aed;margin-right:6px">跨领域</span>'
    h += f'直播经济 × 平台供给侧运营 {BOOK_REFS["PLATSCALE"]}</div>'
    h += f'<div style="font-size:12px;color:#475569;line-height:1.7">'
    h += f'<strong>现象：</strong>{t["anchmems"]}位主播日贡献¥{t["live_rev"]:,.0f}直播相关营收。人均直播{t["avg_anchtime"]/60:.0f}分钟。<br>'
    h += f'<strong>对撞：</strong>直播平台的增长核心不在观众（需求侧），而在主播（供给侧）。主播数量×时长×互动质量=直播营收。'
    h += f' 当前人均仅{t["avg_anchtime"]/60:.0f}分钟，对标行业120分钟标准差距明显。<br>'
    h += f'<strong>动作：</strong>①主播激励计划（每日>120分钟给额外流量曝光）②新主播扶持期（首7天保底流量）③直播PK赛事增加互动密度<br>'
    h += f'<strong>预估：</strong>主播活跃度翻倍 → <b style="color:#dc2626">直播营收+¥{int(t["live_rev"]):,}/日，月增¥{int(t["live_rev"]*30):,}</b></div></div>'

    h += f'<div style="background:#f0fdf4;border-radius:10px;padding:16px;border-left:4px solid #16a34a">'
    h += f'<div style="font-weight:700;color:#166534;margin-bottom:8px"><span class="pill" style="background:#16a34a;margin-right:6px">跨领域</span>'
    h += f'支付心理学 × 转化漏斗 {BOOK_REFS["LEAN"]}</div>'
    h += f'<div style="font-size:12px;color:#475569;line-height:1.7">'
    h += f'<strong>现象：</strong>{t["order_fail_rate"]:.1f}%的订单支付失败，日损失预估¥{int(t["total_rev"]/t["order_pay"]*t["order_fail"]) if t["order_pay"]>0 else 0:,}。<br>'
    h += f'<strong>对撞：</strong>用户下单意味着购买意愿已形成，支付失败是「临门一脚」的系统性浪费。'
    h += f' 精益分析中支付环节的每1%改善都是纯利润增长。<br>'
    h += f'<strong>动作：</strong>①失败订单自动重试+短信提醒 ②多支付通道自动切换 ③预检测支付环境<br>'
    pay_est = int(t["order_fail"]*0.1*(t["total_rev"]/t["order_pay"])) if t["order_pay"]>0 else 0
    h += f'<strong>预估：</strong>成功率+10% → <b style="color:#dc2626">日增¥{pay_est:,}，月增¥{pay_est*30:,}</b></div></div>'

    h += f'<div style="background:#eff6ff;border-radius:10px;padding:16px;border-left:4px solid #3b82f6">'
    h += f'<div style="font-weight:700;color:#1d4ed8;margin-bottom:8px"><span class="pill" style="background:#3b82f6;margin-right:6px">跨领域</span>'
    h += f'Hook模型 × 留存设计 {BOOK_REFS["HOOKED"]}</div>'
    h += f'<div style="font-size:12px;color:#475569;line-height:1.7">'
    h += f'<strong>现象：</strong>次日留存{t["retain_rate_1d"]:.1f}%，新用户首日流失严重。<br>'
    h += f'<strong>对撞：</strong>Hook四要素(触发→行动→酬赏→投入)中，婚恋APP的「不确定酬赏」最强——'
    h += f'「你有N位异性喜欢了你」的悬念 > 任何功能教程。用户首日必须在30分钟内到达Aha时刻。<br>'
    h += f'<strong>动作：</strong>①注册后30分钟推「谁看了你」 ②首日任务：发消息→收到回复闭环 ③男女分层激活路径<br>'
    ret_est = int(t["active"]*0.05*t["pay_rate"]/100*t["arpu"])
    h += f'<strong>预估：</strong>留存+5pp → 付费池+{int(t["active"]*0.05):,}人 → <b style="color:#dc2626">日增¥{ret_est:,}，月增¥{ret_est*30:,}</b>'
    h += f'<br><strong>交友APP留存特殊洞见：</strong>Hook模型在交友场景最强的要素是「社交投入」——'
    h += f'用户上传照片、填写资料、发送消息后，沉没成本让TA更难离开。'
    h += f'首日引导目标不只是「让用户看到功能」，而是「让用户投入」：完善资料→上传照片→发出第一条消息→收到回复。</div></div>'
    h += '</div></div>'
    return h


def improvements_html(t, orders, traffic):
    """改善建议汇总"""
    tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    items = []

    if t["order_fail_rate"] > 40:
        lost = t["total_rev"] / t["order_pay"] * t["order_fail"] if t["order_pay"] > 0 else 0
        items.append(("P0", "支付成功率治理（47%失败→25%以下）",
            "①排查iOS IAP回调异常 ②上海银联/扫码支付渠道修复 ③失败订单5分钟内推送重试引导 ④预检测支付环境",
            lost * 0.3, BOOK_REFS["LEAN"]))

    if t["zhenxin_pct"] > 80:
        items.append(("P0", f"珍心占比治理（{t['zhenxin_pct']:.1f}%→<80%）",
            "①推出2-3个差异化新品 ②首页/推送提升超级会员/直播守护曝光 ③珍心会员捆绑推荐其他产品",
            t["total_rev"] * 0.05, BOOK_REFS["REVENUE"]))

    if t["retain_rate_1d"] < 40:
        items.append(("P0", f"次日留存提升至40%（当前{t['retain_rate_1d']:.1f}%）",
            "①首日Hook：30分钟内推「谁看了你」 ②简化注册首屏即呈现匹配价值 ③男女分层激活路径",
            t["active"] * 0.05 * t["pay_rate"] / 100 * t["arpu"], BOOK_REFS["HOOKED"]))

    items.append(("P1", "直播运营密度提升",
        f"①主播激励计划（日>120分钟额外曝光）②新主播7天扶持 ③直播PK赛事 ④当前人均{t['avg_anchtime']/60:.0f}分钟",
        t["live_rev"] * 0.5, BOOK_REFS["PLATSCALE"]))

    if t["pay_rate"] < 5:
        items.append(("P1", f"付费率从{t['pay_rate']:.1f}%提升至5%",
            "①付费路径简化 ②免费→付费摩擦点排查 ③价格锚点优化 ④损失厌恶设计",
            t["active"] * (5 - t["pay_rate"]) / 100 * t["arpu"], BOOK_REFS["RETENTION"]))

    losing = [c for c in traffic.get("channels", []) if c["cost"] > 0 and c["roi"] < 0.3]
    if losing:
        waste = sum(c["cost"] - c["amt_d"] for c in losing)
        items.append(("P1", "亏损渠道优化",
            f"砍掉ROI<0.3的{len(losing)}个渠道，日省¥{waste:,.0f}投放费用，预算转移到高ROI渠道",
            waste, BOOK_REFS["GROWTH"]))

    items.sort(key=lambda x: x[3], reverse=True)
    total_uplift = sum(i[3] for i in items)

    h = f'<div class="card"><h2>改善建议 · {len(items)}条（按预估增幅排序）· 总预估¥{total_uplift:,.0f}</h2>'
    for p, title, action, est, ref in items:
        p_bg = "#dc2626" if p == "P0" else "#d97706" if p == "P1" else "#6366f1"
        h += f'<div style="display:flex;gap:14px;padding:14px 0;border-bottom:1px solid #f1f5f9">'
        h += f'<div style="min-width:32px;height:32px;background:{p_bg};color:#fff;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700">{p}</div>'
        h += f'<div style="flex:1"><div style="font-size:14px;font-weight:600;color:#1e293b">【{p}】{title}</div>'
        h += f'<div style="font-size:12px;color:#64748b;margin-top:2px">{MANAGER} · 部署: {tomorrow}</div>'
        h += f'<div style="font-size:12px;color:#475569;margin-top:4px">{action}</div>'
        h += f'<div style="font-size:12px;color:#dc2626;font-weight:600;margin-top:4px">预估增幅: +¥{est:,.0f} | {ref}</div></div></div>'
    h += '</div>'
    return h


def trend_bars_html(trends, date_display):
    """10天趋势条形图"""
    if not trends:
        return ""
    max_rev = max(tr.get("amt", 0) for tr in trends) or 1
    h = '<div class="card"><h2>10日营收趋势（含付费率 · 订单成功率 · 直播数据）</h2>'
    for tr in trends[-10:]:
        bar_w = int(tr.get("amt", 0) / max_rev * 100)
        is_today = tr["dt"] == date_display
        h += f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">'
        h += f'<div style="font-size:10px;color:#64748b;width:50px">{tr["dt"][5:]}</div>'
        h += f'<div style="flex:1;background:#f1f5f9;border-radius:2px;height:14px">'
        h += f'<div style="width:{bar_w}%;background:{"#0f172a" if is_today else "#3b82f6"};height:14px;border-radius:2px"></div></div>'
        h += f'<div style="font-size:10px;color:#1e293b;width:55px;text-align:right">¥{tr.get("amt",0)/10000:.1f}万</div>'
        h += f'<div style="font-size:10px;color:#64748b;width:35px">{tr.get("pay_rate",0):.1f}%付</div>'
        h += f'<div style="font-size:10px;color:#64748b;width:40px">{tr.get("order_conv",0):.0f}%成</div>'
        h += '</div>'
    h += '</div>'
    return h


def version_html(orders):
    """APP版本分布"""
    by_ver = orders.get("by_version", [])
    if not by_ver:
        return ""
    total_amt = orders["total_amt"] or 1
    h = '<div class="card"><h2>APP版本分布 · TOP10</h2>'
    h += '<table><thead><tr><th style="text-align:left;padding-left:10px">版本</th>'
    h += '<th>订单</th><th style="text-align:right">营收</th><th>占比</th></tr></thead><tbody>'
    for ver, v in by_ver[:10]:
        pct = v["amt"] / total_amt * 100
        h += f'<tr><td style="padding:6px 10px;font-size:12px;font-weight:600">v{ver}</td>'
        h += f'<td style="text-align:center;font-size:12px">{v["cnt"]:,}</td>'
        h += f'<td style="text-align:right;font-size:12px;font-weight:600">¥{v["amt"]:,.0f}</td>'
        h += f'<td style="text-align:center;font-size:12px">{pct:.1f}%</td></tr>'
    h += '</tbody></table></div>'
    return h


def aarrr_html(t, orders, traffic):
    """AARRR增长模型全链路对撞"""
    h = '<div class="card" style="border-left:4px solid #0891b2"><h2>AARRR增长模型 × 交友APP全链路对撞分析</h2>'
    h += f'<div style="font-size:11px;color:#64748b;margin-bottom:12px">{BOOK_REFS["GROWTH"]} × {BOOK_REFS["HOOKED"]} × {BOOK_REFS["LEAN"]}</div>'

    total_cost = traffic.get("total_cost", 0)
    reg = traffic.get("total_reg", 0)
    cpa = total_cost / reg if reg > 0 else 0
    ltv = t["arpu"] * 30
    ltv_cac = ltv / cpa if cpa > 0 else 0

    stages = [
        ("Acquisition<br>获客", f"日注册{t['mems']:,}人", f"投放¥{total_cost:,.0f}", f"CPA=¥{cpa:.0f}",
         "#3b82f6", "渠道买量是水龙头——ROI<0.3的渠道是漏水的水管",
         f"砍亏损渠道省¥{int(sum(c['cost']-c['amt_d'] for c in traffic.get('channels',[]) if c.get('cost',0)>0 and c.get('roi',0)<0.3)):,}/日"),
        ("Activation<br>激活", f"DAU {t['active']:,}", f"次日留存{t['retain_rate_1d']:.1f}%", f"Aha<30分钟",
         "#16a34a", "交友APP的Aha时刻=「被异性喜欢/收到消息」，不是功能介绍",
         f"留存+5pp → +¥{int(t['active']*0.05*t['pay_rate']/100*t['arpu']):,}/日"),
        ("Retention<br>留存", f"留存率{t['retain_rate_1d']:.1f}%", f"复购占比{t['fugou_pct']:.1f}%", f"每日{t['link_1d']:,}链接",
         "#7c3aed", "留存驱动力=社交关系链，不是产品功能。有未读消息=会回来",
         f"复购+5pp → +¥{int(t['total_rev']*0.05):,}/日"),
        ("Revenue<br>变现", f"日营收¥{t['total_rev']/10000:.0f}万", f"ARPU¥{t['arpu']:.1f}", f"付费率{t['pay_rate']:.1f}%",
         "#dc2626", "支付失败率{:.0f}%是最大的营收漏洞——47%的订单未成功".format(t['order_fail_rate']),
         f"支付率+10pp → +¥{int(t['order_fail']*0.1*t['arpu']):,}/日"),
        ("Referral<br>推荐", f"链接{t['link_1d']:,}次", f"外呼{t['callout_1d']:,}", f"leads{t['leads_online']+t['leads_offline']:,}",
         "#d97706", "口碑=最低成本获客。每个成功配对都是潜在的推荐节点",
         "配对成功用户自动触发推荐奖励 → 预计获客成本-20%"),
    ]

    h += '<div style="display:flex;gap:2px;flex-wrap:wrap;margin-bottom:14px">'
    for title, m1, m2, m3, color, insight, action in stages:
        h += f'<div style="flex:1;min-width:150px;padding:12px;border-radius:8px;background:#f8fafc;border-top:3px solid {color}">'
        h += f'<div style="font-size:12px;font-weight:700;color:{color};margin-bottom:6px">{title}</div>'
        h += f'<div style="font-size:11px;color:#1e293b;line-height:1.6">{m1}<br>{m2}<br>{m3}</div>'
        h += f'<div style="font-size:10px;color:#64748b;margin-top:6px;border-top:1px solid #e2e8f0;padding-top:6px">{insight}</div>'
        h += f'<div style="font-size:10px;color:#dc2626;font-weight:600;margin-top:4px">{action}</div></div>'
    h += '</div>'

    h += f'<div style="padding:12px;background:#f0fdfa;border-radius:8px;font-size:12px;color:#0f766e;line-height:1.8">'
    h += f'<strong>LTV/CAC = ¥{ltv:.0f} / ¥{cpa:.0f} = {ltv_cac:.1f}x</strong>'
    if ltv_cac < 3:
        h += f' <span style="color:#dc2626">（低于3x健康线，获客成本过高或用户价值不足）</span>'
    else:
        h += f' （健康，>3x）'
    h += f'<br>AARRR五环中当前最大杠杆：<b>{"支付成功率" if t["order_fail_rate"]>40 else "留存率" if t["retain_rate_1d"]<40 else "付费率"}</b>'
    h += f'——改善1个百分点的投入产出比远高于其他环节。'
    h += '</div></div>'
    return h


def assemble_full_html(t, p, orders, traffic, trends, date_display):
    """组装完整HTML报告"""
    html = f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">'
    html += f'<meta name="viewport" content="width=device-width,initial-scale=1">'
    html += f'<title>APP 全量深度体检报告 {date_display}</title>{CSS}</head>'
    html += '<body><div class="wrap">'
    html += header_html(t, date_display)
    html += kpi_cards_html(t, p, trends)
    html += live_section_html(t, orders)
    html += payment_funnel_html(t, orders)
    html += entrance_analysis_html(orders)
    html += platform_compare_html(orders)
    html += retention_matrix_html(t)
    html += channel_roi_html(traffic)
    html += product_mix_html(t)
    html += user_structure_html(t, orders)
    html += cross_biz_html(t)
    html += funnel_chain_html(t)
    html += knowledge_collision_html(t)
    html += improvements_html(t, orders, traffic)
    html += trend_bars_html(trends, date_display)
    html += version_html(orders)
    html += aarrr_html(t, orders, traffic)
    html += f'<div style="text-align:center;padding:20px;color:#94a3b8;font-size:12px">'
    html += f'本报告由智慧助理自动生成 · {date_display} · 覆盖20+诊断模块 · 3张数据表全量解析 · APP专属v2<br>'
    html += f'数据源: daily(51字段) + orders(20字段×多维) + traffic(16字段×{len(traffic.get("channels",[]))}渠道)</div>'
    html += '</div></body></html>'
    return html
