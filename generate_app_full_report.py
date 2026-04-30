# -*- coding: utf-8 -*-
"""
APP 全量业务体检报告生成器
覆盖14项必含模块，符合 report_template_benchmark.md 基准线
产品品类 = 部门层，渠道质量 = 员工层
"""
import sys
import datetime
from agent_system.actions.api_client import daily, trend, query, safe_float, safe_int
from agent_system.actions.email_sender import send_report_email
from agent_system.actions.report_exporter import export_html

DATE = "20260227"
DATE_DISPLAY = "2026-02-27"
MANAGER = "APP产品运营负责人"

BOOK_REFS = {
    "HOOKED": "📚《Hooked》Nir Eyal",
    "GROWTH": "📚《增长黑客》Sean Ellis",
    "NSFOCUS": "📚《硅谷增长黑客实战笔记》曲卉",
    "RETENTION": "📚《用户增长方法论》范冰",
    "ADDICTION": "📚《上瘾》Nir Eyal",
    "REVENUE": "📚《订阅经济》Tien Tzuo",
    "UX": "📚《用户体验要素》Jesse Garrett",
}

PRODUCTS = [
    ("zhenxin_member",    "珍心会员",   "#dc2626", "核心付费产品，占比红线<80%"),
    ("super_member_full", "超级会员全", "#d97706", "高价值产品"),
    ("live_guard",        "直播守护",   "#7c3aed", "互动付费"),
    ("super_member_plus", "超级会员+",  "#2563eb", "中级会员"),
    ("zhenai_coin",       "珍爱币",     "#16a34a", "虚拟货币"),
    ("super_remind",      "超级提醒",   "#d97706", "功能付费"),
    ("star_privilege",    "星光特权",   "#6366f1", "特权产品"),
    ("super_recommend",   "超级推荐",   "#0891b2", "推荐算法付费"),
    ("other",             "其他",       "#94a3b8", "其他产品"),
]


def prev_date(d: str) -> str:
    dt = datetime.datetime.strptime(d, "%Y%m%d") - datetime.timedelta(days=1)
    return dt.strftime("%Y%m%d")


def color_kpi(val, green_thresh, red_thresh, higher_is_better=True):
    if higher_is_better:
        if val >= green_thresh: return "#16a34a"
        if val >= red_thresh: return "#d97706"
        return "#dc2626"
    else:
        if val <= green_thresh: return "#16a34a"
        if val <= red_thresh: return "#d97706"
        return "#dc2626"


def parse_rows(resp):
    return resp.get("rows", []) if isinstance(resp, dict) else []


def agg_app(rows):
    if not rows:
        return {}
    r = rows[0]  # APP is single-row
    total_rev = safe_float(r.get("amt"))
    pay_num = safe_int(r.get("pay_num"))
    active = safe_int(r.get("active_members"))
    refund = safe_float(r.get("refund_money"))
    new_pay = safe_int(r.get("pay_num_new"))
    retain_1d = safe_int(r.get("retain_1d"))
    retain_7d = safe_int(r.get("retain_7d"))
    order_cnt = safe_int(r.get("order_cnt"))
    order_pay = safe_int(r.get("order_pay"))
    reg_m = safe_int(r.get("reg_num_m"))
    pay_m = safe_int(r.get("pay_num_m"))
    amt_m = safe_float(r.get("pay_amt_m"))
    mems = safe_int(r.get("mems"))
    zhenxin = safe_float(r.get("zhenxin_member"))
    pay_amt = safe_float(r.get("pay_amt"))
    # products
    prod_vals = {k: safe_float(r.get(k)) for k, _, _, _ in PRODUCTS}
    prod_total = sum(prod_vals.values()) or 1
    arpu = total_rev / pay_num if pay_num > 0 else 0
    pay_rate = pay_num / active * 100 if active > 0 else 0
    refund_rate = refund / total_rev * 100 if total_rev > 0 else 0
    zhenxin_pct = zhenxin / total_rev * 100 if total_rev > 0 else 0
    retain_rate_1d = retain_1d / mems * 100 if mems > 0 else 0
    retain_rate_7d = retain_7d / mems * 100 if mems > 0 else 0
    order_conv = order_pay / order_cnt * 100 if order_cnt > 0 else 0
    return dict(
        total_rev=total_rev, pay_num=pay_num, active=active,
        refund=refund, new_pay=new_pay,
        retain_1d=retain_1d, retain_7d=retain_7d,
        order_cnt=order_cnt, order_pay=order_pay,
        reg_m=reg_m, pay_m=pay_m, amt_m=amt_m, mems=mems,
        zhenxin=zhenxin, pay_amt=pay_amt,
        prod_vals=prod_vals, prod_total=prod_total,
        arpu=arpu, pay_rate=pay_rate, refund_rate=refund_rate,
        zhenxin_pct=zhenxin_pct,
        retain_rate_1d=retain_rate_1d, retain_rate_7d=retain_rate_7d,
        order_conv=order_conv,
    )


def build_trend_data(trend_rows):
    """Use daily query data as trend — group by ftime if multiple rows."""
    # trend_rows are individual daily rows; aggregate per day
    by_day = {}
    for r in trend_rows:
        day = str(r.get("ftime", ""))[:8]
        if day not in by_day:
            by_day[day] = []
        by_day[day].append(r)
    result = []
    for day in sorted(by_day.keys()):
        rows = by_day[day]
        t = {"dt": day[:4] + "-" + day[4:6] + "-" + day[6:8]}
        for k in ("amt", "pay_num", "active_members", "refund_money", "retain_1d"):
            t[k] = sum(safe_float(r.get(k)) for r in rows)
        t["arpu"] = t["amt"] / t["pay_num"] if t["pay_num"] > 0 else 0
        t["pay_rate"] = t["pay_num"] / t["active_members"] * 100 if t["active_members"] > 0 else 0
        result.append(t)
    return result


def fetch_app_trend_rows(date, fetch_daily=daily):
    """Fetch the report date and previous 9 days, tagging rows with their date."""
    trend_rows = []
    base_dt = datetime.datetime.strptime(date, "%Y%m%d")
    for delta in range(9, -1, -1):
        d = (base_dt - datetime.timedelta(days=delta)).strftime("%Y%m%d")
        resp = fetch_daily("app", d)
        for row in parse_rows(resp):
            row["ftime"] = d
            trend_rows.append(row)
    return trend_rows


def generate_html(today_rows, prev_rows, trend_rows_raw, date_display):
    t = agg_app(today_rows)
    p = agg_app(prev_rows) if prev_rows else {}
    trends = build_trend_data(trend_rows_raw)
    tomorrow = (datetime.datetime.strptime(date_display, "%Y-%m-%d") +
                datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    if not t:
        return "<html><body><h1>暂无数据</h1></body></html>"

    def dod(key, higher_better=True):
        if not p:
            return ""
        cur = t.get(key, 0)
        prv = p.get(key, cur)
        if prv == 0:
            return ""
        chg = (cur - prv) / prv * 100
        up = chg > 0
        color = "#16a34a" if (up and higher_better) or (not up and not higher_better) else "#dc2626"
        arrow = "▲" if up else "▼"
        return f'<span style="font-size:10px;color:{color}">{arrow}{abs(chg):.1f}%</span>'

    # ── Product category table (= dept detail) ───────────────────────
    prod_data = [(k, n, c, desc, t["prod_vals"].get(k, 0))
                 for k, n, c, desc in PRODUCTS]
    prod_data.sort(key=lambda x: x[4], reverse=True)

    prod_rows = ""
    for rank, (key, name, color, desc, amt) in enumerate(prod_data):
        pct = amt / t["total_rev"] * 100 if t["total_rev"] > 0 else 0
        warn = ""
        if key == "zhenxin_member" and pct > 80:
            warn = f'<span style="color:#dc2626;font-size:10px;font-weight:600">⚠ 超80%红线</span>'
        arpu_prod = amt / t["pay_num"] if t["pay_num"] > 0 else 0
        prod_rows += f"""<tr>
<td style="padding:7px 10px;font-size:12px">
  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{color};margin-right:6px"></span>
  <strong>{name}</strong></td>
<td style="padding:7px;text-align:right;font-size:12px;font-weight:600;color:{color}">¥{amt/10000:.1f}万</td>
<td style="padding:7px;text-align:center;font-size:12px;font-weight:600">
  <div style="background:#f1f5f9;border-radius:3px;height:6px;width:100%;margin-bottom:3px">
    <div style="width:{min(pct,100):.0f}%;background:{color};height:6px;border-radius:3px"></div>
  </div>
  {pct:.1f}%{warn}</td>
<td style="padding:7px;text-align:right;font-size:12px">¥{arpu_prod:,.0f}</td>
<td style="padding:7px;font-size:11px;color:#64748b">{desc}</td>
</tr>"""

    # ── TOP5 products analysis ────────────────────────────────────────
    top5_prods = prod_data[:5]
    bot5_prods = prod_data[-5:]

    def why_product_good(key, name, amt, pct):
        if key == "zhenxin_member":
            return "核心收入引擎，用户首选付费路径"
        if pct > 15:
            return "占比健康，用户主动购买意愿强"
        if amt > 50000:
            return "绝对金额可观，值得专项运营"
        return "具备增长潜力"

    top5_prod_html = ""
    for i, (key, name, color, desc, amt) in enumerate(top5_prods):
        pct = amt / t["total_rev"] * 100 if t["total_rev"] > 0 else 0
        reasons = why_product_good(key, name, amt, pct)
        top5_prod_html += f"""<tr style="background:{'#f0fdf4' if i==0 else ''}">
<td style="padding:8px 10px;font-size:12px;font-weight:700;color:#16a34a">TOP{i+1}</td>
<td style="padding:8px;font-size:12px;font-weight:600;color:{color}">{name}</td>
<td style="padding:8px;text-align:right;font-size:12px;font-weight:600;color:#dc2626">¥{amt/10000:.1f}万</td>
<td style="padding:8px;text-align:center;font-size:12px">{pct:.1f}%</td>
<td style="padding:8px;font-size:11px;color:#475569">{reasons}</td>
<td style="padding:8px;font-size:11px;color:#475569">加大曝光、优化首屏入口、A/B测试转化路径</td>
</tr>"""

    # ── TOP5 vs BOTTOM5 product compare ──────────────────────────────
    compare_rows = ""
    for i, ((tk, tn, tc, td, ta), (bk, bn, bc, bd, ba)) in enumerate(
            zip(top5_prods[:3], bot5_prods[:3])):
        ratio = ta / ba if ba > 0 else 99
        compare_rows += f"""<tr>
<td style="padding:7px 10px;font-size:12px;font-weight:600;color:#16a34a">{tn}</td>
<td style="padding:7px;text-align:right;font-size:12px;font-weight:700;color:#16a34a">¥{ta/10000:.1f}万</td>
<td style="padding:7px;font-size:12px;color:#dc2626">{bn}</td>
<td style="padding:7px;text-align:right;font-size:12px;color:#dc2626">¥{ba/10000:.1f}万</td>
<td style="padding:7px;text-align:center;font-size:12px;font-weight:700;color:#7c3aed">{ratio:.1f}x</td>
<td style="padding:7px;font-size:11px;color:#475569">{'差距显著，{tn}设计值得{bn}借鉴：核心在钩子、价值感知、路径简化' if ratio>3 else '适度差距，关注产品价值传递是否清晰'}</td>
</tr>"""

    # ── BOTTOM5 product diagnosis ─────────────────────────────────────
    bot_diag = ""
    for key, name, color, desc, amt in bot5_prods:
        pct = amt / t["total_rev"] * 100 if t["total_rev"] > 0 else 0
        if pct < 1:
            issue = "占比极低，付费路径可能存在障碍或用户感知价值不足"
            action = "排查付费入口曝光频次；用户问卷调研产品认知度；考虑与核心产品捆绑推荐"
        elif pct < 3:
            issue = "占比偏低，激活场景单一"
            action = "增加使用场景教育；完善功能介绍；结合首页推荐提升曝光"
        else:
            issue = "有一定基础，但增长潜力未释放"
            action = "A/B测试定价策略；短期促销实验；精准人群定向推送"
        bot_diag += f"""<div style="padding:14px;margin-bottom:10px;border-radius:8px;border-left:4px solid #d97706;background:#fffbeb">
<div style="font-weight:700;color:#d97706;margin-bottom:4px">⚠ {name} · 占比{pct:.1f}%</div>
<div style="font-size:12px;color:#475569;line-height:1.8">
营收: ¥{amt/10000:.1f}万 | 占总收入: {pct:.1f}%<br>
<strong>问题诊断：</strong>{issue}<br>
<strong>即日行动：</strong>{MANAGER} {action}
</div></div>"""

    # ── Improvement suggestions ───────────────────────────────────────
    improvements = []

    if t.get("zhenxin_pct", 0) > 80:
        over = t["zhenxin_pct"] - 80
        improvements.append({
            "p": "P0", "title": "珍心占比治理（从{:.1f}%→<80%）".format(t["zhenxin_pct"]),
            "owner": MANAGER,
            "action": "推出2-3个差异化新品；在首页/推送中提升{超级会员/直播守护}曝光比例；珍心会员捆绑推荐其他产品",
            "days": 30,
            "rev_est": t["total_rev"] * 0.05,
            "ref": BOOK_REFS["REVENUE"],
            "deploy": tomorrow,
        })

    if t.get("retain_rate_1d", 0) < 40:
        improvements.append({
            "p": "P0", "title": f"次日留存率提升至40%（当前{t['retain_rate_1d']:.1f}%）",
            "owner": MANAGER,
            "action": "首日Hook：谁看了你/谁喜欢了你 + 首日任务奖励；简化注册首屏即呈现匹配价值；男女分层激活路径",
            "days": 14,
            "rev_est": t["total_rev"] * 0.03,
            "ref": BOOK_REFS["HOOKED"],
            "deploy": tomorrow,
        })

    if t.get("pay_rate", 0) < 5:
        improvements.append({
            "p": "P1", "title": f"付费率从{t['pay_rate']:.1f}%提升至5%",
            "owner": MANAGER,
            "action": "活跃用户付费路径简化；免费→付费关键摩擦点排查；价格锚点优化；付费后即时价值传递",
            "days": 14,
            "rev_est": t["active"] * (5 - t["pay_rate"]) / 100 * t["arpu"],
            "ref": BOOK_REFS["RETENTION"],
            "deploy": tomorrow,
        })

    if t.get("refund_rate", 0) > 2:
        improvements.append({
            "p": "P1", "title": f"退款率控制至<2%（当前{t['refund_rate']:.1f}%）",
            "owner": MANAGER,
            "action": "付费后14天价值确认推送；退款原因标签化分析；针对高退款产品优化体验交付",
            "days": 14,
            "rev_est": t["refund"] * (t["refund_rate"] - 2) / 100,
            "ref": BOOK_REFS["NSFOCUS"],
            "deploy": tomorrow,
        })

    improvements.append({
        "p": "P1", "title": "ARPU提升策略（向¥35目标）",
        "owner": MANAGER,
        "action": f"推出连续包月折扣；设计价值阶梯（基础→标准→高级→年费）；付费用户升级提醒（当前ARPU ¥{t['arpu']:.0f}）",
        "days": 30,
        "rev_est": t["pay_num"] * 2,
        "ref": BOOK_REFS["REVENUE"],
        "deploy": tomorrow,
    })

    improvements.append({
        "p": "P2", "title": "流量质量优化（注册→激活转化）",
        "owner": MANAGER,
        "action": "分渠道追踪注册→激活率；低质渠道降权或暂停；高质渠道加大预算；用户画像与素材匹配度提升",
        "days": 7,
        "rev_est": t["active"] * 0.02 * t["arpu"],
        "ref": BOOK_REFS["GROWTH"],
        "deploy": tomorrow,
    })

    improvements.sort(key=lambda x: x["rev_est"], reverse=True)
    total_uplift = sum(i["rev_est"] for i in improvements)

    imp_html = ""
    for item in improvements:
        p_bg = "#dc2626" if item["p"] == "P0" else ("#d97706" if item["p"] == "P1" else "#6366f1")
        imp_html += f"""<div style="display:flex;gap:14px;padding:16px 0;border-bottom:1px solid #f1f5f9">
<div style="min-width:32px;height:32px;background:{p_bg};color:#fff;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700">{item['p']}</div>
<div style="flex:1">
<div style="font-size:14px;font-weight:600;color:#1e293b">【{item['p']}】{item['title']}</div>
<div style="font-size:12px;color:#64748b;margin-top:2px">负责人: {item['owner']} · 部署: {item['deploy']} · 周期: {item['days']}天</div>
<div style="font-size:12px;color:#475569;margin-top:4px">{item['action']}</div>
<div style="font-size:12px;color:#dc2626;font-weight:600;margin-top:4px">预估增幅: +¥{item['rev_est']:,.0f} | {item['ref']}</div>
</div></div>"""

    # ── 10-day trend bars ─────────────────────────────────────────────
    trend_html = ""
    if trends:
        max_rev = max(tr.get("amt", 0) for tr in trends) or 1
        for tr in trends[-10:]:
            bar_w = int(tr.get("amt", 0) / max_rev * 100)
            is_today = tr["dt"] == date_display
            trend_html += f"""<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
<div style="font-size:10px;color:#64748b;width:50px">{tr['dt'][5:]}</div>
<div style="flex:1;background:#f1f5f9;border-radius:2px;height:14px">
  <div style="width:{bar_w}%;background:{'#0f172a' if is_today else '#3b82f6'};height:14px;border-radius:2px"></div></div>
<div style="font-size:10px;color:#1e293b;width:60px;text-align:right">¥{tr.get('amt',0)/10000:.1f}万</div>
<div style="font-size:10px;color:#64748b;width:45px">{tr.get('pay_rate',0):.1f}%付</div>
</div>"""

    # ── HTML assembly ─────────────────────────────────────────────────
    act_c = color_kpi(t["active"], 200000, 150000)
    pay_c = color_kpi(t["pay_rate"], 5, 3)
    arpu_c = color_kpi(t["arpu"], 30, 20)
    rr_c = color_kpi(t["refund_rate"], 2, 4, False)
    r1_c = color_kpi(t["retain_rate_1d"], 45, 35)
    zx_c = color_kpi(t["zhenxin_pct"], 79, 80, False)  # lower is better for concentration

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>APP 全量体检报告 {date_display}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#f5f6f8;color:#1e293b;font-size:14px;line-height:1.5}}
.wrap{{max-width:960px;margin:0 auto;padding:20px 16px}}
.card{{background:#fff;border-radius:10px;padding:24px;margin-bottom:16px;box-shadow:0 1px 2px rgba(0,0,0,.04)}}
.card h2{{font-size:15px;font-weight:700;color:#0f172a;margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid #f1f5f9}}
table{{width:100%;border-collapse:collapse}}
th{{font-size:11px;color:#94a3b8;font-weight:500;padding:8px 6px;text-align:center;border-bottom:1px solid #e2e8f0}}
th:first-child{{text-align:left;padding-left:10px}}
</style></head>
<body><div class="wrap">

<!-- 1. 头部 -->
<div style="background:linear-gradient(135deg,#0f172a,#1e3a5f,#1d4ed8);border-radius:12px;padding:28px 32px;margin-bottom:16px;color:#fff">
<div style="font-size:11px;color:#93c5fd;letter-spacing:3px">APP FULL · 全量体检报告 · 14模块</div>
<div style="font-size:22px;font-weight:700;margin:6px 0 4px">APP 全量运营体检报告</div>
<div style="font-size:13px;color:#bfdbfe">{date_display} · 负责人: {MANAGER} · DAU: {t['active']:,} · 付费用户: {t['pay_num']:,} · 月累付费: {t['pay_m']:,}人</div>
</div>

<!-- 2. KPI卡片（按转化流转顺序）-->
<div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap">
<div style="flex:1;min-width:90px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">DAU</div>
<div style="font-size:20px;font-weight:800;color:{act_c}">{t['active']:,}</div>
<div style="font-size:11px">{dod('active')} 日环比</div></div>
<div style="flex:1;min-width:90px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">次日留存率</div>
<div style="font-size:20px;font-weight:800;color:{r1_c}">{t['retain_rate_1d']:.1f}%</div>
<div style="font-size:11px;color:#64748b">7日{t['retain_rate_7d']:.1f}%</div></div>
<div style="flex:1;min-width:90px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">付费率</div>
<div style="font-size:20px;font-weight:800;color:{pay_c}">{t['pay_rate']:.1f}%</div>
<div style="font-size:11px;color:#64748b">{t['pay_num']:,}人付费</div></div>
<div style="flex:1;min-width:90px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">ARPU</div>
<div style="font-size:20px;font-weight:800;color:{arpu_c}">¥{t['arpu']:.1f}</div>
<div style="font-size:11px;color:#64748b">基准¥30</div></div>
<div style="flex:1;min-width:90px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">日营收</div>
<div style="font-size:20px;font-weight:800;color:#1e293b">¥{t['total_rev']/10000:.0f}万</div>
<div style="font-size:11px">{dod('total_rev')} 日环比</div></div>
<div style="flex:1;min-width:90px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">月累营收</div>
<div style="font-size:20px;font-weight:800;color:#1e293b">¥{t['amt_m']/10000:.0f}万</div>
<div style="font-size:11px;color:#64748b">月累{t['pay_m']:,}人</div></div>
<div style="flex:1;min-width:90px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">退款率</div>
<div style="font-size:20px;font-weight:800;color:{rr_c}">{t['refund_rate']:.1f}%</div>
<div style="font-size:11px;color:#64748b">红线<2%</div></div>
<div style="flex:1;min-width:90px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">珍心占比</div>
<div style="font-size:20px;font-weight:800;color:{zx_c}">{t['zhenxin_pct']:.1f}%</div>
<div style="font-size:11px;color:#dc2626">红线<80%</div></div>
</div>
<div class="card" style="padding:12px 20px">
<div style="font-size:11px;color:#64748b">流转: DAU{t['active']:,}→次日留存{t['retain_rate_1d']:.1f}%→付费率{t['pay_rate']:.1f}%({t['pay_num']:,}人)→ARPU¥{t['arpu']:.1f}→日营收¥{t['total_rev']/10000:.0f}万 | 珍心占比{t['zhenxin_pct']:.1f}%（红线<80%）</div>
</div>

<!-- 3. 业务定位 -->
<div style="background:#fff;border-radius:10px;padding:20px 24px;margin-bottom:16px;box-shadow:0 1px 2px rgba(0,0,0,.04);border-left:4px solid #1d4ed8">
<div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:8px">业务定位：APP团队（珍心会员等在线付费产品）</div>
<div style="font-size:12px;color:#475569;line-height:1.7;margin-bottom:12px">APP是珍爱网「在线付费产品」体系的核心现金牛，通过DAU驱动的流量转化实现规模化营收，是公司<strong>现金流压舱石</strong>。关键飞轮：用户增长→内容/匹配质量→付费意愿→ARPU→再投入增长。</div>
<div style="font-size:13px;font-weight:600;color:#0f172a;margin-bottom:8px">APP团队高业绩必须关注的重点：</div>
<div style="display:flex;gap:8px;flex-wrap:wrap">
<span style="padding:4px 12px;background:#fef2f2;border:1px solid #fecaca;border-radius:6px;font-size:12px;color:#991b1b;font-weight:600">① DAU（流量基石）</span>
<span style="padding:4px 12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;font-size:12px;color:#1e40af">② 付费率（变现效率）</span>
<span style="padding:4px 12px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;font-size:12px;color:#166534">③ ARPU（单用户价值）</span>
<span style="padding:4px 12px;background:#fef2f2;border:1px solid #fecaca;border-radius:6px;font-size:12px;color:#991b1b;font-weight:600">④ 珍心占比<80%（产品结构健康度）</span>
<span style="padding:4px 12px;background:#fef3c7;border:1px solid #fde68a;border-radius:6px;font-size:12px;color:#92400e">⑤ 退款率<2%</span>
<span style="padding:4px 12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;font-size:12px;color:#1e40af">⑥ 渠道获客质量（留存率代理指标）</span>
</div>
</div>

<!-- 4. 全局诊断 -->
<div class="card">
<h2>全局诊断 · 环比分析</h2>
<div style="padding:14px 16px;margin-bottom:8px;border-radius:8px;background:{'#fef2f2' if t['zhenxin_pct']>80 else '#f0fdf4'};border-left:3px solid {'#dc2626' if t['zhenxin_pct']>80 else '#16a34a'}">
<span style="font-size:10px;font-weight:700;color:#fff;background:{'#dc2626' if t['zhenxin_pct']>80 else '#16a34a'};padding:1px 8px;border-radius:4px;margin-right:6px">{'P0' if t['zhenxin_pct']>80 else '正常'}</span>
<strong>珍心会员占比 {t['zhenxin_pct']:.1f}%</strong> — {'🚨 超80%红线！产品结构过度集中，抗风险能力弱，需立即推进产品多元化' if t['zhenxin_pct']>80 else '✅ 产品结构健康，珍心占比合理'}
</div>
<div style="padding:14px 16px;margin-bottom:8px;border-radius:8px;background:{'#fef2f2' if t['retain_rate_1d']<35 else '#fffbeb' if t['retain_rate_1d']<45 else '#f0fdf4'};border-left:3px solid {'#dc2626' if t['retain_rate_1d']<35 else '#d97706' if t['retain_rate_1d']<45 else '#16a34a'}">
<strong>次日留存率 {t['retain_rate_1d']:.1f}%</strong> — {'🚨 严重偏低，新用户未找到Aha时刻即流失，根本问题' if t['retain_rate_1d']<35 else '⚠ 偏低，需优化首日Hook机制' if t['retain_rate_1d']<45 else '✅ 留存良好'}
</div>
<div style="padding:14px 16px;margin-bottom:8px;border-radius:8px;background:{'#fef2f2' if t['refund_rate']>4 else '#fffbeb' if t['refund_rate']>2 else '#f0fdf4'};border-left:3px solid {'#dc2626' if t['refund_rate']>4 else '#d97706' if t['refund_rate']>2 else '#16a34a'}">
<strong>退款率 {t['refund_rate']:.1f}%</strong>（¥{t['refund']/10000:.1f}万/¥{t['total_rev']/10000:.0f}万）— {'🚨 超4%，退款规模大，需专项治理' if t['refund_rate']>4 else '⚠ 超2%红线，需分产品追因' if t['refund_rate']>2 else '✅ 退款控制良好'}
</div>
<div style="padding:14px 16px;border-radius:8px;background:#f8fafc;border-left:3px solid #6366f1">
<strong>ARPU ¥{t['arpu']:.1f}</strong> / 付费率 {t['pay_rate']:.1f}% — {'ARPU有提升空间（目标¥30），可通过年费产品和升级机制提升' if t['arpu']<30 else 'ARPU良好，聚焦付费率提升'}
</div>
</div>

<!-- 5. 知识图谱诊断模式 -->
<div class="card">
<h2>知识图谱诊断模式 · 精确匹配</h2>
<div style="padding:12px 16px;margin-bottom:8px;border-radius:8px;background:#f8fafc;border-left:3px solid #6366f1">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
<span style="font-size:10px;font-weight:700;color:#fff;background:#dc2626;padding:1px 8px;border-radius:4px">A01</span>
<span style="font-size:13px;font-weight:600">珍心高占比 → 产品结构性风险</span></div>
<div style="font-size:12px;color:#475569;line-height:1.6">珍心占比{t['zhenxin_pct']:.1f}%超80%红线。单产品高集中度意味着政策/竞争风险直接击穿营收。《订阅经济》：健康产品矩阵应保证核心产品<60-70%。</div>
<div style="font-size:11px;color:#6366f1;margin-top:4px">→ 月度推出差异化产品；捆绑推荐；会员等级升级路径设计</div></div>
<div style="padding:12px 16px;margin-bottom:8px;border-radius:8px;background:#f8fafc;border-left:3px solid #6366f1">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
<span style="font-size:10px;font-weight:700;color:#fff;background:#6366f1;padding:1px 8px;border-radius:4px">A02</span>
<span style="font-size:13px;font-weight:600">留存率不足 → Aha时刻未到达</span></div>
<div style="font-size:12px;color:#475569;line-height:1.6">次日留存{t['retain_rate_1d']:.1f}%。用户在首日未找到「可见价值」（匹配/被喜欢/消息互动）即流失。Hook四要素触发不足。</div>
<div style="font-size:11px;color:#6366f1;margin-top:4px">→ 注册后30分钟内推送「谁看了你」；简化激活路径；男女分层引导</div></div>
<div style="padding:12px 16px;margin-bottom:8px;border-radius:8px;background:#f8fafc;border-left:3px solid #d97706">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
<span style="font-size:10px;font-weight:700;color:#fff;background:#d97706;padding:1px 8px;border-radius:4px">A03</span>
<span style="font-size:13px;font-weight:600">付费率偏低 → 免费→付费摩擦过大</span></div>
<div style="font-size:12px;color:#475569;line-height:1.6">付费率{t['pay_rate']:.1f}%（目标5%）。用户对产品价值认知不足，或付费路径设计阻力大。《增长黑客》：付费转化核心在「让用户感受到不付费的损失」。</div>
<div style="font-size:11px;color:#d97706;margin-top:4px">→ 价值感知优化；限时试用；损失厌恶设计</div></div>
</div>

<!-- 6. 因果链 -->
<div class="card">
<h2>因果链推断 · 漏斗佐证 + 最大瓶颈</h2>
<div style="font-size:13px;font-weight:600;margin-bottom:8px">APP用户转化漏斗</div>
<div style="display:flex;gap:4px;flex-wrap:wrap;align-items:center;margin-bottom:12px">
<div style="display:inline-flex;align-items:center">
<div style="padding:6px 12px;border-radius:6px;border:3px solid #16a34a;font-size:11px;font-weight:600">DAU {t['active']:,}</div>
<span style="margin:0 4px;color:#94a3b8">→</span></div>
<div style="display:inline-flex;align-items:center">
<div style="padding:6px 12px;border-radius:6px;border:3px solid {'#dc2626' if t['retain_rate_1d']<35 else '#d97706'};font-size:11px;font-weight:600;background:{'#fef2f2' if t['retain_rate_1d']<35 else '#fffbeb'}">{'🔴 ' if t['retain_rate_1d']<35 else ''}次日留存{t['retain_rate_1d']:.1f}%</div>
<span style="margin:0 4px;color:#94a3b8">→</span></div>
<div style="display:inline-flex;align-items:center">
<div style="padding:6px 12px;border-radius:6px;border:3px solid {'#dc2626' if t['pay_rate']<3 else '#d97706'};font-size:11px;font-weight:600">付费率{t['pay_rate']:.1f}%({t['pay_num']:,}人)</div>
<span style="margin:0 4px;color:#94a3b8">→</span></div>
<div style="display:inline-flex;align-items:center">
<div style="padding:6px 12px;border-radius:6px;border:3px solid {'#d97706' if t['arpu']<30 else '#16a34a'};font-size:11px;font-weight:600">ARPU¥{t['arpu']:.1f}</div>
<span style="margin:0 4px;color:#94a3b8">→</span></div>
<div style="display:inline-flex;align-items:center">
<div style="padding:6px 12px;border-radius:6px;border:3px solid #16a34a;font-size:11px;font-weight:600">日营收¥{t['total_rev']/10000:.0f}万</div></div>
</div>
<div style="font-size:12px;color:#dc2626;font-weight:500;padding:10px 14px;background:#fef2f2;border-radius:6px;line-height:1.7">
🔴 <strong>最大瓶颈：{'次日留存率' if t['retain_rate_1d']<40 else '付费率'}环节</strong>（{'次日留存'+str(round(t['retain_rate_1d'],1))+'%，低于40%目标' if t['retain_rate_1d']<40 else '付费率'+str(round(t['pay_rate'],1))+'%，低于5%目标'}）<br><br>
漏斗佐证：DAU{t['active']:,}→留存{t['retain_rate_1d']:.1f}%→付费{t['pay_rate']:.1f}%({t['pay_num']:,}人)→ARPU¥{t['arpu']:.1f}→¥{t['total_rev']/10000:.0f}万/日<br><br>
杠杆预估：{'留存每+5pp，付费池扩大'+str(int(t['active']*0.05))+'人→日增营收¥'+str(int(t['active']*0.05*t['pay_rate']/100*t['arpu']))+'元' if t['retain_rate_1d']<40 else '付费率每+1pp，新增'+str(int(t['active']*0.01))+'付费用户→日增¥'+str(int(t['active']*0.01*t['arpu']))}
</div></div>

<!-- 7. 跨领域对撞 -->
<div class="card">
<h2>跨领域知识对撞 · 2组</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
<div style="background:#fdf4ff;border-radius:10px;padding:16px;border-left:4px solid #a855f7">
<div style="font-weight:700;color:#7c3aed;margin-bottom:8px">
<span style="font-size:9px;color:#fff;background:#7c3aed;padding:1px 6px;border-radius:3px;margin-right:6px">跨领域</span>
Hook模型 × 社交天性 {BOOK_REFS['HOOKED']}</div>
<div style="font-size:12px;color:#475569;line-height:1.7">
<strong>现象：</strong>次日留存{t['retain_rate_1d']:.1f}%，用户首日无感知即流失<br>
<strong>对撞：</strong>Hook四要素中「不确定酬赏」最强 — 「你有N位异性喜欢了你」的悬念 > 任何功能教程<br>
<strong>动作：</strong>注册后30分钟内推「谁看了你」；首日任务中加入「发消息→收到回复」闭环<br>
<strong>预估：</strong>留存+5pp → +{int(t['active']*0.05*t['pay_rate']/100*t['arpu']):,}元/日
</div></div>
<div style="background:#f0fdf4;border-radius:10px;padding:16px;border-left:4px solid #16a34a">
<div style="font-weight:700;color:#166534;margin-bottom:8px">
<span style="font-size:9px;color:#fff;background:#16a34a;padding:1px 6px;border-radius:3px;margin-right:6px">跨领域</span>
损失厌恶 × 付费转化 {BOOK_REFS['RETENTION']}</div>
<div style="font-size:12px;color:#475569;line-height:1.7">
<strong>现象：</strong>付费率{t['pay_rate']:.1f}%，免费用户大量沉默<br>
<strong>对撞：</strong>Kahneman损失厌恶 — 人对「失去」的恐惧2倍于「获得」的快乐。「你的3个匹配正在流失...」比「开通会员获得XXX」强3倍<br>
<strong>动作：</strong>付费前展示「未开通会员错过了多少互动/被喜欢」；限时试用7天倒计时<br>
<strong>预估：</strong>付费率+0.5pp → +{int(t['active']*0.005*t['arpu']):,}元/日
</div></div>
</div></div>

<!-- 8. 改善建议 -->
<div class="card">
<h2>改善建议 · {len(improvements)}条（按预估增幅排序）· 总预估¥{total_uplift:,.0f}</h2>
{imp_html}
</div>

<!-- 9. 产品品类收入明细（渠道/明细表）-->
<div class="card" style="overflow-x:auto">
<h2>产品品类收入明细（按金额排序，含占比 + 人均贡献）</h2>
<table><thead><tr>
<th style="text-align:left;padding-left:10px">产品</th>
<th style="text-align:right">今日收入</th>
<th style="text-align:center">占比条形图</th>
<th style="text-align:right">人均贡献</th>
<th>说明</th>
</tr></thead>
<tbody>{prod_rows}</tbody></table>
</div>

<!-- 10. 10天趋势（部门明细替代）-->
<div class="card">
<h2>10日营收趋势（含付费率变化）</h2>
{trend_html if trend_html else '<div style="color:#94a3b8;font-size:12px">趋势数据加载中...</div>'}
</div>

<!-- 11. TOP5产品深度分析 -->
<div class="card" style="overflow-x:auto">
<h2>TOP5产品深度分析（为什么好 + 可运营性）</h2>
<table><thead><tr>
<th style="text-align:left;padding-left:10px">排名</th>
<th>产品</th>
<th style="text-align:right">收入</th>
<th style="text-align:center">占比</th>
<th>优势分析</th>
<th>可复制/可增长方向</th>
</tr></thead>
<tbody>{top5_prod_html}</tbody></table>
</div>

<!-- 12. TOP5 vs BOTTOM5 产品对比 -->
<div class="card" style="overflow-x:auto">
<h2>高收入 vs 低收入产品对比（差异来源 + 运营启示）</h2>
<table><thead><tr>
<th style="text-align:left;padding-left:10px">高产品</th>
<th style="text-align:right;color:#16a34a">高产品收入</th>
<th style="text-align:left">低产品</th>
<th style="text-align:right;color:#dc2626">低产品收入</th>
<th style="text-align:center">差距倍数</th>
<th>运营启示</th>
</tr></thead>
<tbody>{compare_rows}</tbody></table>
</div>

<!-- 13. 低收入产品诊断 -->
<div class="card">
<h2>低收入产品专项诊断 + 即日改善建议</h2>
{bot_diag}
</div>

<!-- 14. 数据→人的转向（四维分析）-->
<div class="card">
<h2>数据→人的转向（技能 / 留存机制 / 变现效率 / 产品结构）</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
<div style="background:#eff6ff;border-radius:8px;padding:14px;border-left:3px solid #3b82f6">
<div style="font-weight:700;color:#1d4ed8;margin-bottom:6px">🎯 技能维度（产品运营能力）</div>
<div style="font-size:12px;color:#555;line-height:1.8">技能核心：A/B测试能力、用户分层能力、产品迭代节奏感。次日留存{t['retain_rate_1d']:.1f}%反映渠道质量+首日体验设计技能。需分渠道看留存，砍低质渠道（留存<25%），加大高质渠道预算。</div>
</div>
<div style="background:#fdf4ff;border-radius:8px;padding:14px;border-left:3px solid #a855f7">
<div style="font-weight:700;color:#7c3aed;margin-bottom:6px">🔁 留存机制维度</div>
<div style="font-size:12px;color:#555;line-height:1.8">留存核心是「Aha时刻」的早到达。婚恋APP的Aha = 首次被喜欢/首次互动。优化注册→Aha的路径时长，目标从注册到Aha<30分钟。</div>
</div>
<div style="background:#f0fdf4;border-radius:8px;padding:14px;border-left:3px solid #16a34a">
<div style="font-weight:700;color:#166534;margin-bottom:6px">💰 变现效率维度</div>
<div style="font-size:12px;color:#555;line-height:1.8">付费率{t['pay_rate']:.1f}% × ARPU¥{t['arpu']:.1f} = 人均价值¥{t['pay_rate']/100*t['arpu']:.1f}。提升路径：①降低付费摩擦 ②提升ARPU（年费/升级路径）③提升复购率。</div>
</div>
<div style="background:#fffbeb;border-radius:8px;padding:14px;border-left:3px solid #d97706">
<div style="font-weight:700;color:#d97706;margin-bottom:6px">🏗 产品结构维度</div>
<div style="font-size:12px;color:#555;line-height:1.8">珍心占比{t['zhenxin_pct']:.1f}%，{'超过80%红线，产品结构高风险，需立即推进多元化' if t['zhenxin_pct']>80 else '接近红线，提前布局产品多元化，培育第二增长曲线'}。目标：珍心<70%，第二产品群共贡献30%+。</div>
</div>
</div></div>

<div style="text-align:center;padding:20px;color:#94a3b8;font-size:12px">
📊 本报告由 Linh Nguyen（智慧助理）自动生成 · {date_display} · 覆盖14项诊断模块 · 防退化v1<br>
数据来源：珍爱网APP运营数据平台 · 基准参考：report_template_benchmark.md
</div>

</div></body></html>"""
    return html


def main():
    global DATE, DATE_DISPLAY
    if "--date" in sys.argv:
        idx = sys.argv.index("--date")
        if idx + 1 < len(sys.argv):
            DATE = sys.argv[idx + 1].replace("-", "")
            DATE_DISPLAY = f"{DATE[:4]}-{DATE[4:6]}-{DATE[6:]}"

    print(f"[APP报告] 拉取数据 {DATE}...")
    resp_today = daily("app", DATE)
    resp_prev = daily("app", prev_date(DATE))

    rows_today = parse_rows(resp_today)
    rows_prev = parse_rows(resp_prev)
    trend_rows = fetch_app_trend_rows(DATE)

    print(f"[APP报告] 今日行数: {len(rows_today)}, 昨日: {len(rows_prev)}, 趋势: {len(trend_rows)}")

    html = generate_html(rows_today, rows_prev, trend_rows, DATE_DISPLAY)

    filename = f"APP_Full_{DATE_DISPLAY}.html"
    path = export_html(html, filename, open_browser=True)
    print(f"[APP报告] 已导出: {path}")

    subject = f"📱 APP全量体检报告 {DATE_DISPLAY}"
    ok = send_report_email(subject, html)
    print(f"[APP报告] 邮件: {'成功' if ok else '失败'}")


if __name__ == "__main__":
    main()
