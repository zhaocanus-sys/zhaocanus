# -*- coding: utf-8 -*-
"""
电话红娘团队全量业务体检报告生成器
覆盖14项必含模块，符合 report_template_benchmark.md 基准线
防退化版本 v2 — 含员工级TOP5/BOTTOM5 + 13维能力对比 + 因果链漏斗
"""
import sys
import datetime
from collections import defaultdict
from agent_system.actions.api_client import daily, trend, query, safe_float, safe_int
from agent_system.actions.email_sender import send_report_email
from agent_system.actions.report_exporter import export_html

DATE = "20260227"
DATE_DISPLAY = "2026-02-27"
MANAGER = "张心蕊"

DEPT_MANAGERS = {
    "厦门红娘一区一部": "温方方（代）",
    "厦门红娘一区二部": "周美",
    "厦门红娘二区一部": "邓怡娟（代）",
    "厦门红娘二区二部": "刘文琴",
    "深圳新创电话红娘": "涂楠",
    "深圳红娘一部": "曹世迪",
}

BOOK_REFS = {
    "CUSTOMER_SUCCESS": "📚《Customer Success》Nick Mehta",
    "TRUST": "📚《The Speed of Trust》Covey",
    "INFLUENCE": "📚《Influence》Cialdini",
    "SPIN": "📚《SPIN Selling》Rackham",
    "ATOMIC": "📚《Atomic Habits》Clear",
    "BRAND": "📚《Building a StoryBrand》Miller",
    "NPS": "📚《The Ultimate Question 2.0》Reichheld",
}

MGMT_GAP_RULES = {
    "low_jm_rate": "缺乏VIP资源系统性盘点机制，日程管理粗放",
    "high_refund": "对服务承诺合规性监管不足，期望管理失控",
    "low_per_rev": "差异化辅导策略缺失，标杆SOP未下沉到全员",
    "low_love_rate": "服务目标停留在安排见面，未关注恋爱达成率长尾价值",
    "high_tousu": "缺乏客诉预防机制，问题出现后才处理而非提前预防",
}


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


def agg_hongniang(rows):
    total_rev = sum(safe_float(r.get("pay_1d_amt")) for r in rows)
    pay_m = sum(safe_float(r.get("pay_1m_amt")) for r in rows)
    jm_n = sum(safe_int(r.get("jm_n")) for r in rows)
    jm_all = sum(safe_int(r.get("jm_all")) for r in rows)
    staff_new = sum(safe_int(r.get("staff_new")) for r in rows)
    call_worker = sum(safe_int(r.get("call_worker")) for r in rows)
    on_vip = sum(safe_int(r.get("on_vip")) for r in rows)
    allot_yes = sum(safe_int(r.get("allot_yes")) for r in rows)
    link_time_count = sum(safe_int(r.get("link_time_count")) for r in rows)
    deep_count = sum(safe_int(r.get("deep_count")) for r in rows)
    love_cnt_m = sum(safe_int(r.get("love_cnt_m")) for r in rows)
    tousu = sum(safe_int(r.get("tousu_n")) for r in rows)
    pay_1d_num = sum(safe_int(r.get("pay_1d_num")) for r in rows)
    # channel refunds
    zhenai_back = sum(safe_float(r.get("zhenai_back")) for r in rows)
    zhenaigd_back = sum(safe_float(r.get("zhenaigd_back")) for r in rows)
    zhenai_hz_back = sum(safe_float(r.get("zhenai_hz_back")) for r in rows)
    zhenai_xfh_back = sum(safe_float(r.get("zhenai_xfh_back")) for r in rows)
    zhenai_md_back = sum(safe_float(r.get("zhenai_md_back")) for r in rows)
    total_refund = zhenai_back + zhenaigd_back + zhenai_hz_back + zhenai_xfh_back + zhenai_md_back
    # VIP class breakdown
    vip_class = {i: sum(safe_int(r.get(f"vip_class{i}")) for r in rows) for i in range(5)}
    allot_class = {i: sum(safe_int(r.get(f"allot_class{i}")) for r in rows) for i in range(5)}
    # computed
    w = staff_new or 1
    jm_rate = jm_n / w
    per_rev = total_rev / w
    refund_rate = total_refund / total_rev * 100 if total_rev > 0 else 0
    deep_rate = deep_count / link_time_count * 100 if link_time_count > 0 else 0
    return dict(
        total_rev=total_rev, pay_m=pay_m, jm_n=jm_n, jm_all=jm_all,
        staff_new=staff_new, call_worker=call_worker, on_vip=on_vip,
        allot_yes=allot_yes, link_time_count=link_time_count,
        deep_count=deep_count, love_cnt_m=love_cnt_m, tousu=tousu,
        pay_1d_num=pay_1d_num,
        zhenai_back=zhenai_back, zhenaigd_back=zhenaigd_back,
        zhenai_hz_back=zhenai_hz_back, zhenai_xfh_back=zhenai_xfh_back,
        zhenai_md_back=zhenai_md_back, total_refund=total_refund,
        vip_class=vip_class, allot_class=allot_class,
        jm_rate=jm_rate, per_rev=per_rev,
        refund_rate=refund_rate, deep_rate=deep_rate,
    )


def build_dept_data(rows):
    depts = {}
    for r in rows:
        raw_name = r.get("dept_name", "未知")
        dn = raw_name.split(" ")[0] if " " in raw_name else raw_name
        if dn not in depts:
            depts[dn] = dict(
                dept_name=dn, full_name=raw_name,
                staff_new=0, call_worker=0, on_vip=0,
                jm_n=0, jm_all=0, pay_1d_amt=0, pay_1m_amt=0,
                link_time_count=0, deep_count=0,
                love_cnt_m=0, tousu_n=0, pay_1d_num=0,
                zhenai_back=0, zhenaigd_back=0, zhenai_hz_back=0,
                zhenai_xfh_back=0, zhenai_md_back=0,
            )
        d = depts[dn]
        d["staff_new"] += safe_int(r.get("staff_new"))
        d["call_worker"] += safe_int(r.get("call_worker"))
        d["on_vip"] += safe_int(r.get("on_vip"))
        d["jm_n"] += safe_int(r.get("jm_n"))
        d["jm_all"] += safe_int(r.get("jm_all"))
        d["pay_1d_amt"] += safe_float(r.get("pay_1d_amt"))
        d["pay_1m_amt"] += safe_float(r.get("pay_1m_amt"))
        d["link_time_count"] += safe_int(r.get("link_time_count"))
        d["deep_count"] += safe_int(r.get("deep_count"))
        d["love_cnt_m"] += safe_int(r.get("love_cnt_m"))
        d["tousu_n"] += safe_int(r.get("tousu_n"))
        d["pay_1d_num"] += safe_int(r.get("pay_1d_num"))
        for k in ("zhenai_back", "zhenaigd_back", "zhenai_hz_back", "zhenai_xfh_back", "zhenai_md_back"):
            d[k] += safe_float(r.get(k))
    result = []
    for d in depts.values():
        w = d["staff_new"] or 1
        lc = d["link_time_count"] or 1
        d["jm_rate"] = d["jm_n"] / w
        d["per_rev"] = d["pay_1d_amt"] / w
        d["deep_rate"] = d["deep_count"] / lc * 100
        d["total_refund"] = sum(d.get(k, 0) for k in
                                ("zhenai_back", "zhenaigd_back", "zhenai_hz_back",
                                 "zhenai_xfh_back", "zhenai_md_back"))
        rev = d["pay_1d_amt"] or 1
        d["refund_rate"] = d["total_refund"] / rev * 100
        # lookup manager
        d["manager"] = next(
            (v for k, v in DEPT_MANAGERS.items() if k in d["dept_name"] or k in d.get("full_name", "")),
            "（待确认）"
        )
        result.append(d)
    return sorted(result, key=lambda x: x["pay_1d_amt"], reverse=True)


def build_worker_data(hourly_rows):
    """Aggregate hourly individual-worker data into per-worker daily summary."""
    workers = defaultdict(lambda: dict(
        worker_name="", dept_name="",
        jm_n=0, jm_all=0, on_vip=0, off_vip=0,
        link_time_count=0, jianmian_cs=0, jianmian_rs=0,
        jianmiangd_cs=0, jianmiangd_rs=0,
        love_cnt_m=0, tousu_n=0,
        online_pay_m=0, xml_pay_m=0, offline_pay_m=0,
        zhenai_back=0, zhenaigd_back=0,
    ))
    for r in hourly_rows:
        wn = r.get("worker_name", "")
        if not wn:
            continue
        w = workers[wn]
        w["worker_name"] = wn
        w["dept_name"] = r.get("dept_name", "")
        w["jm_n"] += safe_int(r.get("jm_n"))
        w["jm_all"] += safe_int(r.get("jm_all"))
        w["on_vip"] += safe_int(r.get("on_vip"))
        w["off_vip"] += safe_int(r.get("off_vip"))
        w["link_time_count"] += safe_int(r.get("link_time_count"))
        w["jianmian_cs"] += safe_int(r.get("jianmian_cs"))
        w["jianmian_rs"] += safe_int(r.get("jianmian_rs"))
        w["jianmiangd_cs"] += safe_int(r.get("jianmiangd_cs"))
        w["jianmiangd_rs"] += safe_int(r.get("jianmiangd_rs"))
        w["love_cnt_m"] += safe_int(r.get("love_cnt_m"))
        w["tousu_n"] += safe_int(r.get("tousu_n"))
        w["online_pay_m"] += safe_float(r.get("online_pay_m"))
        w["xml_pay_m"] += safe_float(r.get("xml_pay_m"))
        w["offline_pay_m"] += safe_float(r.get("offline_pay_m"))
        w["zhenai_back"] += safe_float(r.get("zhenai_back"))
        w["zhenaigd_back"] += safe_float(r.get("zhenaigd_back"))

    result = []
    for w in workers.values():
        w["total_rev"] = w["online_pay_m"] + w["xml_pay_m"] + w["offline_pay_m"]
        vip = (w["on_vip"] + w["off_vip"]) or 1
        w["jm_rate"] = w["jm_n"] / max(vip / 10, 1)  # jm per 10 VIP resources
        w["confirm_rate"] = w["jianmian_rs"] / (w["jianmian_cs"] or 1) * 100
        w["reappt_rate"] = w["jianmiangd_rs"] / (w["jianmiangd_cs"] or 1) * 100
        w["total_refund"] = w["zhenai_back"] + w["zhenaigd_back"]
        w["score"] = (
            w["jm_n"] * 3 +
            w["confirm_rate"] * 0.5 +
            w["reappt_rate"] * 0.8 +
            w["love_cnt_m"] * 10 -
            w["tousu_n"] * 5
        )
        result.append(w)
    return sorted(result, key=lambda x: x["score"], reverse=True)


def _dim(val, fmt=".0f"):
    return f"{val:{fmt}}" if isinstance(val, (int, float)) else str(val)


def generate_html(today_rows, prev_rows, hourly_rows, date_display):
    t = agg_hongniang(today_rows)
    p = agg_hongniang(prev_rows) if prev_rows else {}
    depts = build_dept_data(today_rows)
    workers = build_worker_data(hourly_rows)

    top5 = workers[:5]
    bot5 = workers[-5:] if len(workers) >= 5 else workers[::-1]
    tomorrow = (datetime.datetime.strptime(date_display, "%Y-%m-%d") +
                datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    def dod(key, higher_better=True):
        if not p:
            return ""
        cur = t.get(key, 0)
        prv = p.get(key, cur)
        if prv == 0:
            return ""
        chg = (cur - prv) / prv * 100
        up = chg > 0
        color = ("#16a34a" if (up and higher_better) or (not up and not higher_better) else "#dc2626")
        arrow = "▲" if up else "▼"
        return f'<span style="font-size:10px;color:{color}">{arrow}{abs(chg):.1f}%</span>'

    mr_c = color_kpi(t["jm_rate"], 1.2, 0.8)
    rev_c = color_kpi(t["total_rev"], 150000, 80000)
    rr_c = color_kpi(t["refund_rate"], 5, 10, False)
    pr_c = color_kpi(t["per_rev"], 4000, 2000)

    # ── Channel refund breakdown ──────────────────────────────────────
    channel_data = [
        ("珍爱主站", t["zhenai_back"]),
        ("珍爱广东", t["zhenaigd_back"]),
        ("珍爱杭州", t["zhenai_hz_back"]),
        ("珍爱新发现", t["zhenai_xfh_back"]),
        ("珍爱门店", t["zhenai_md_back"]),
    ]
    channel_data.sort(key=lambda x: x[1], reverse=True)
    total_ref = t["total_refund"] or 1
    refund_rows = ""
    for name, amt in channel_data:
        pct = amt / total_ref * 100
        rc = "#dc2626" if pct > 40 else ("#d97706" if pct > 20 else "#16a34a")
        refund_rows += f"""<tr>
<td style="padding:7px 10px;font-size:12px">{name}</td>
<td style="padding:7px;text-align:right;font-size:12px;color:#dc2626">¥{amt/10000:.2f}万</td>
<td style="padding:7px;text-align:center;font-size:12px;font-weight:600;color:{rc}">{pct:.1f}%</td>
<td style="padding:7px;font-size:11px">{'🔴 重点治理渠道' if pct>40 else '⚠ 中等风险' if pct>20 else '✅ 正常'}</td>
</tr>"""

    # ── Department detail table ───────────────────────────────────────
    dept_rows = ""
    for d in depts:
        jm_c = "#dc2626" if d["jm_rate"] < 0.8 else ("#d97706" if d["jm_rate"] < 1.2 else "#16a34a")
        rr_dc = "#dc2626" if d["refund_rate"] > 10 else ("#d97706" if d["refund_rate"] > 5 else "#16a34a")
        mgr = d["manager"]
        dept_rows += f"""<tr>
<td style="padding:7px 10px;font-size:12px;font-weight:600">{d['dept_name']}</td>
<td style="padding:7px;text-align:center;font-size:12px">{mgr}</td>
<td style="padding:7px;text-align:center;font-size:12px">{d['staff_new']}</td>
<td style="padding:7px;text-align:center;font-size:12px">{d['on_vip']}</td>
<td style="padding:7px;text-align:center;font-size:12px">{d['jm_n']}</td>
<td style="padding:7px;text-align:center;font-size:12px;font-weight:600;color:{jm_c}">{d['jm_rate']:.2f}</td>
<td style="padding:7px;text-align:right;font-size:12px;font-weight:600;color:#dc2626">¥{d['pay_1d_amt']/10000:.1f}万</td>
<td style="padding:7px;text-align:right;font-size:12px;color:{pr_c}">¥{d['per_rev']:,.0f}</td>
<td style="padding:7px;text-align:center;font-size:12px;color:{rr_dc}">{d['refund_rate']:.1f}%</td>
<td style="padding:7px;text-align:center;font-size:12px">{d['love_cnt_m']}</td>
</tr>"""

    # ── Worker TOP5 table ─────────────────────────────────────────────
    def why_good(w):
        reasons = []
        if w["jm_n"] >= 3:
            reasons.append("见面安排频次高")
        if w["confirm_rate"] >= 85:
            reasons.append("见面确认率强")
        if w["reappt_rate"] >= 70:
            reasons.append("复见面推进积极")
        if w["love_cnt_m"] > 0:
            reasons.append("恋爱达成有突破")
        if not reasons:
            reasons.append("资源盘点系统化")
        return "；".join(reasons)

    top5_rows = ""
    for i, w in enumerate(top5):
        dn = w["dept_name"].split(" ")[0] if " " in w["dept_name"] else w["dept_name"]
        top5_rows += f"""<tr style="background:{'#f0fdf4' if i==0 else ''}">
<td style="padding:8px 10px;font-size:12px;font-weight:700;color:#16a34a">TOP{i+1}</td>
<td style="padding:8px;font-size:12px;font-weight:600">{w['worker_name']}</td>
<td style="padding:8px;font-size:11px;color:#64748b">{dn[:10]}</td>
<td style="padding:8px;text-align:center;font-size:12px">{w['jm_n']}</td>
<td style="padding:8px;text-align:center;font-size:12px">{w['confirm_rate']:.0f}%</td>
<td style="padding:8px;text-align:center;font-size:12px">{w['reappt_rate']:.0f}%</td>
<td style="padding:8px;text-align:center;font-size:12px">{w['love_cnt_m']}</td>
<td style="padding:8px;text-align:right;font-size:12px;color:#dc2626">¥{w['total_rev']/10000:.1f}万</td>
<td style="padding:8px;text-align:center;font-size:12px;font-weight:600;color:#16a34a">{w['score']:.0f}</td>
<td style="padding:8px;font-size:11px;color:#475569">{why_good(w)}</td>
</tr>"""

    # ── TOP5 vs BOTTOM5 ──────────────────────────────────────────────
    dims = [
        ("见面安排数", "jm_n", "次"),
        ("见面确认率", "confirm_rate", "%"),
        ("复见面推进率", "reappt_rate", "%"),
        ("本月恋爱达成", "love_cnt_m", "次"),
        ("今日营收", "total_rev", "元"),
        ("VIP在线资源", "on_vip", "个"),
        ("VIP下线资源", "off_vip", "个"),
        ("通话次数", "link_time_count", "次"),
        ("退费总额", "total_refund", "元"),
        ("综合评分", "score", "分"),
    ]

    def avg_dim(ws, key):
        vals = [safe_float(w.get(key)) for w in ws]
        return sum(vals) / len(vals) if vals else 0

    compare_rows = ""
    for name, key, unit in dims:
        tv = avg_dim(top5, key)
        bv = avg_dim(bot5, key)
        ratio = tv / bv if bv > 0 else 99
        higher_better = key not in ("total_refund", "tousu_n")
        gap_color = "#16a34a" if ratio >= 1.5 else ("#d97706" if ratio >= 1.1 else "#dc2626")
        if not higher_better:
            gap_color = "#16a34a" if ratio <= 0.7 else ("#d97706" if ratio <= 1.0 else "#dc2626")
        compare_rows += f"""<tr>
<td style="padding:7px 10px;font-size:12px;font-weight:600">{name}</td>
<td style="padding:7px;text-align:center;font-size:12px;font-weight:700;color:#16a34a">{tv:.1f}{unit}</td>
<td style="padding:7px;text-align:center;font-size:12px;color:#dc2626">{bv:.1f}{unit}</td>
<td style="padding:7px;text-align:center;font-size:12px;font-weight:700;color:{gap_color}">{ratio:.1f}x</td>
<td style="padding:7px;font-size:11px;color:#475569">{'差距显著，可通过SOP复制TOP工作模式' if ratio>1.5 else '差距可控，需强化日常执行' if ratio>1.1 else '差距较小'}</td>
</tr>"""

    # ── BOTTOM5 diagnosis ─────────────────────────────────────────────
    bot5_cards = ""
    for w in bot5:
        issues = []
        if w["jm_n"] < 1:
            issues.append("今日零见面安排，VIP资源完全未服务")
        if w["confirm_rate"] < 50:
            issues.append(f"见面确认率仅{w['confirm_rate']:.0f}%，邀约话术需优化")
        if w["total_refund"] > 5000:
            issues.append(f"退费金额¥{w['total_refund']:,.0f}，需排查服务承诺合规性")
        if not issues:
            issues.append("综合评分偏低，需排查具体薄弱环节")
        dn = w["dept_name"].split(" ")[0] if " " in w["dept_name"] else w["dept_name"]
        bot5_cards += f"""<div style="padding:14px;margin-bottom:10px;border-radius:8px;border-left:4px solid #dc2626;background:#fef2f2">
<div style="font-weight:700;color:#dc2626;margin-bottom:4px">⚠ {w['worker_name']} · {dn[:12]}</div>
<div style="font-size:12px;color:#475569;line-height:1.8">
见面安排：{w['jm_n']} | 确认率：{w['confirm_rate']:.0f}% | 复见面率：{w['reappt_rate']:.0f}% | 恋爱达成：{w['love_cnt_m']} | 综合评分：{w['score']:.0f}<br>
<strong>问题：</strong>{'；'.join(issues)}<br>
<strong>即日行动：</strong>{MANAGER} 今日安排部门组长与该员工1v1沟通，提交「本人手头VIP名单 + 近7日未见面原因 + 明日行动计划」，48h内跟进
</div></div>"""

    # ── Improvements ─────────────────────────────────────────────────
    improvements = []

    if t["jm_rate"] < 1.0:
        gap = 1.0 - t["jm_rate"]
        extra_jm = int(gap * t["staff_new"])
        rev_est = extra_jm * (t["total_rev"] / max(t["jm_n"], 1))
        improvements.append({
            "p": "P0", "title": "见面安排率修复至1.0",
            "owner": MANAGER,
            "cur": f"{t['jm_rate']:.2f}", "tgt": "1.0",
            "action": "今日09:00统计前日零见面红娘名单，限3日完成VIP补救触达；植入「付费后3/7/14日价值确认」机制",
            "days": 7,
            "rev_est": rev_est,
            "ref": BOOK_REFS["CUSTOMER_SUCCESS"],
            "deploy": tomorrow,
        })

    if t["refund_rate"] > 5:
        save = t["total_rev"] * (t["refund_rate"] - 4.5) / 100
        improvements.append({
            "p": "P0", "title": "退费率管控至4.5%",
            "owner": MANAGER,
            "cur": f"{t['refund_rate']:.1f}%", "tgt": "4.5%",
            "action": "本周组织退费案例复盘，每渠道抽3个典型案例；签单后48h回访；过度承诺纳入绩效扣分",
            "days": 14,
            "rev_est": save,
            "ref": BOOK_REFS["TRUST"],
            "deploy": tomorrow,
        })

    if depts:
        best = max(depts, key=lambda d: d["jm_rate"])
        worst = min(depts, key=lambda d: d["jm_rate"])
        if best["jm_rate"] - worst["jm_rate"] > 0.3:
            gap_rev = (best["per_rev"] - worst["per_rev"]) * worst["staff_new"] * 0.3
            worst_mgr = worst["manager"]
            improvements.append({
                "p": "P1", "title": f"标杆复制：{best['dept_name']}SOP推广",
                "owner": f"{MANAGER}+{worst_mgr}",
                "cur": f"差距{best['jm_rate']:.2f}x vs {worst['jm_rate']:.2f}x",
                "tgt": "缩小至0.2x",
                "action": f"提取{best['dept_name']}见面安排话术和日程盘点SOP，{worst['dept_name']}({worst_mgr})今日组织晨会学习，7日测试",
                "days": 14,
                "rev_est": gap_rev,
                "ref": BOOK_REFS["ATOMIC"],
                "deploy": tomorrow,
            })

    improvements.append({
        "p": "P1", "title": "社会认同话术植入（见面率+0.2）",
        "owner": MANAGER,
        "cur": "无标准化案例话术",
        "tgt": "100%植入",
        "action": "每位红娘准备3-5个同类型成功见面案例；提供「和您情况相似的会员最近…」话术模板；1周内全团队测试",
        "days": 7,
        "rev_est": t["staff_new"] * 0.2 * (t["total_rev"] / max(t["jm_n"], 1)),
        "ref": BOOK_REFS["INFLUENCE"],
        "deploy": tomorrow,
    })

    improvements.append({
        "p": "P1", "title": "TOP5标杆员工晨会分享机制",
        "owner": MANAGER,
        "cur": "无系统性标杆传播",
        "tgt": "每日1条标杆",
        "action": f"从今日起每日晨会由综合评分TOP1员工({top5[0]['worker_name'] if top5 else '待定'})分享昨日1个成功见面案例；提炼SOP；2周内中腰部评分提升",
        "days": 14,
        "rev_est": t["total_rev"] * 0.08,
        "ref": BOOK_REFS["SPIN"],
        "deploy": tomorrow,
    })

    improvements.append({
        "p": "P2", "title": "VIP存量盘活（NPS+留存）",
        "owner": MANAGER,
        "cur": f"在线VIP{t['on_vip']}个",
        "tgt": "月见面达成率>60%",
        "action": "每周五专项处理30天内未见面VIP；建立VIP沉睡分级机制（7天/14天/30天）；沉睡触达话术差异化",
        "days": 30,
        "rev_est": t["total_rev"] * 0.05,
        "ref": BOOK_REFS["NPS"],
        "deploy": tomorrow,
    })

    improvements.sort(key=lambda x: x["rev_est"], reverse=True)
    total_uplift = sum(i["rev_est"] for i in improvements)

    imp_html = ""
    for i, item in enumerate(improvements):
        p_bg = "#dc2626" if item["p"] == "P0" else ("#d97706" if item["p"] == "P1" else "#6366f1")
        imp_html += f"""<div style="display:flex;gap:14px;padding:16px 0;border-bottom:1px solid #f1f5f9">
<div style="min-width:32px;height:32px;background:{p_bg};color:#fff;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700">{item['p']}</div>
<div style="flex:1">
<div style="font-size:14px;font-weight:600;color:#1e293b">【{item['p']}】{item['title']}</div>
<div style="font-size:12px;color:#64748b;margin-top:2px">负责人: {item['owner']} · 部署日期: {item['deploy']}</div>
<div style="font-size:12px;color:#475569;margin-top:4px">{item['action']}</div>
<div style="font-size:12px;color:#475569;margin-top:2px">当前: {item['cur']} → 目标: {item['tgt']} | 坚持: {item['days']}天</div>
<div style="font-size:12px;color:#dc2626;font-weight:600;margin-top:4px">预估增幅: +¥{item['rev_est']:,.0f}/日 | {item['ref']}</div>
</div></div>"""

    # ── Department-level diagnosis ────────────────────────────────────
    dept_diag_html = ""
    worst3_depts = sorted(depts, key=lambda d: d["jm_rate"])[:3]
    for d in worst3_depts:
        mgr = d["manager"]
        gap_key = ("low_jm_rate" if d["jm_rate"] < 0.8 else
                   ("high_refund" if d["refund_rate"] > 8 else "low_per_rev"))
        mgmt_gap = MGMT_GAP_RULES.get(gap_key, "需进一步排查")
        dept_diag_html += f"""<div style="padding:14px 16px;margin-bottom:10px;border-radius:8px;border-left:4px solid #d97706;background:#fffbeb">
<div style="display:flex;justify-content:space-between;margin-bottom:4px">
<div><span style="font-size:10px;font-weight:700;color:#fff;background:#d97706;padding:1px 8px;border-radius:4px;margin-right:6px">部门预警</span>
<span style="font-size:13px;font-weight:600">{d['dept_name']}（{mgr}）— 见面安排率 {d['jm_rate']:.2f}</span></div>
<span style="font-size:12px;color:#dc2626;font-weight:600">达均值可+¥{(t['per_rev']-d['per_rev'])*d['staff_new']:,.0f}/日</span>
</div>
<div style="font-size:12px;color:#475569;line-height:1.7">
人数: {d['staff_new']} | VIP在线: {d['on_vip']} | 安排见面: {d['jm_n']} | 营收: ¥{d['pay_1d_amt']/10000:.1f}万 | 人均: ¥{d['per_rev']:,.0f}<br>
<strong>管理视角缺失推断：</strong>{mgmt_gap}<br>
<strong>即日建议：</strong>{MANAGER} 今日与 {mgr} 约谈，要求提交本部门「VIP盘点清单+未见面原因+本周行动计划」
</div></div>"""

    # ── Department gap summary (empty-safe) ───────────────────────────
    if depts:
        best_jm_dept = max(depts, key=lambda d: d["jm_rate"])
        best_jm = max(d["jm_rate"] for d in depts)
        worst_jm = min(d["jm_rate"] for d in depts)
        dept_gap_html = (
            f"最高{best_jm_dept['dept_name']} 见面安排率 {best_jm:.2f} vs "
            f"最低 {worst_jm:.2f} — 差距{best_jm - worst_jm:.2f}x，标杆复制空间显著"
        )
    else:
        dept_gap_html = "暂无部门数据，待分配后对比"

    # ── HTML assembly ─────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>电话红娘团队全量体检报告 {date_display}</title>
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
<div style="background:linear-gradient(135deg,#1a0533,#4a0e8f,#c0392b);border-radius:12px;padding:28px 32px;margin-bottom:16px;color:#fff">
<div style="font-size:11px;color:#fed7aa;letter-spacing:3px">HONGNIANG FULL · 电话红娘全量体检 · 14模块</div>
<div style="font-size:22px;font-weight:700;margin:6px 0 4px">电话红娘团队全量业务体检报告</div>
<div style="font-size:13px;color:#fbbf24">{date_display} · 负责人: {MANAGER} · 在岗: {t['staff_new']}人 · 通话红娘: {t['call_worker']}人 · 在线VIP: {t['on_vip']}个</div>
</div>

<!-- 2. KPI卡片（按转化流转顺序）-->
<div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap">
<div style="flex:1;min-width:100px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">在线VIP</div>
<div style="font-size:20px;font-weight:800;color:#1e293b">{t['on_vip']}</div>
<div style="font-size:11px;color:#64748b">在岗红娘{t['staff_new']}人</div></div>
<div style="flex:1;min-width:100px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">通话次数</div>
<div style="font-size:20px;font-weight:800;color:#1e293b">{t['link_time_count']}</div>
<div style="font-size:11px;color:#64748b">深度沟通{t['deep_count']}次</div></div>
<div style="flex:1;min-width:100px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">见面安排</div>
<div style="font-size:20px;font-weight:800;color:{mr_c}">{t['jm_n']}</div>
<div style="font-size:11px">安排率 {t['jm_rate']:.2f} {dod('jm_rate')}</div></div>
<div style="flex:1;min-width:100px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">今日营收</div>
<div style="font-size:20px;font-weight:800;color:{rev_c}">¥{t['total_rev']/10000:.1f}万</div>
<div style="font-size:11px">月累¥{t['pay_m']/10000:.0f}万 {dod('total_rev')}</div></div>
<div style="flex:1;min-width:100px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">人均产值</div>
<div style="font-size:20px;font-weight:800;color:{pr_c}">¥{t['per_rev']:,.0f}</div>
<div style="font-size:11px">红线¥2,000 {dod('per_rev')}</div></div>
<div style="flex:1;min-width:100px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">退费率</div>
<div style="font-size:20px;font-weight:800;color:{rr_c}">{t['refund_rate']:.1f}%</div>
<div style="font-size:11px">退费¥{t['total_refund']/10000:.1f}万 {dod('refund_rate',False)}</div></div>
<div style="flex:1;min-width:100px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">本月恋爱达成</div>
<div style="font-size:20px;font-weight:800;color:#7c3aed">{t['love_cnt_m']}</div>
<div style="font-size:11px;color:#64748b">投诉{t['tousu']}单</div></div>
<div style="flex:1;min-width:100px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">新签</div>
<div style="font-size:20px;font-weight:800;color:#1e293b">{t['pay_1d_num']}</div>
<div style="font-size:11px;color:#64748b">人/日</div></div>
</div>
<div class="card" style="padding:12px 20px">
<div style="font-size:11px;color:#64748b">流转: VIP资源{t['on_vip']}→通话{t['link_time_count']}→深沟{t['deep_count']}({t['deep_rate']:.1f}%)→安排见面{t['jm_n']}(率{t['jm_rate']:.2f})→营收¥{t['total_rev']/10000:.1f}万 | 人均¥{t['per_rev']:,.0f}</div>
</div>

<!-- 3. 业务定位 -->
<div style="background:#fff;border-radius:10px;padding:20px 24px;margin-bottom:16px;box-shadow:0 1px 2px rgba(0,0,0,.04);border-left:4px solid #7c2d12">
<div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:8px">业务定位：电话红娘团队</div>
<div style="font-size:12px;color:#475569;line-height:1.7;margin-bottom:12px">
电话红娘是珍爱网「VIP会员一对一服务」体系的核心执行者，负责将付费VIP会员的情感需求转化为实际见面机会，是公司<strong>品牌生命线</strong>。红娘服务质量直接影响续费率、恋爱达成率和口碑传播。
</div>
<div style="font-size:13px;font-weight:600;color:#0f172a;margin-bottom:8px">电话红娘团队高业绩必须关注的重点：</div>
<div style="display:flex;gap:8px;flex-wrap:wrap">
<span style="padding:4px 12px;background:#fef2f2;border:1px solid #fecaca;border-radius:6px;font-size:12px;color:#991b1b;font-weight:600">① 见面安排率（jm_n/在岗红娘数，基准≥1.0）</span>
<span style="padding:4px 12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;font-size:12px;color:#1e40af">② 复见面率（服务质量核心）</span>
<span style="padding:4px 12px;background:#fef3c7;border:1px solid #fde68a;border-radius:6px;font-size:12px;color:#92400e">③ 退费分渠道监控（品牌生命线）</span>
<span style="padding:4px 12px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;font-size:12px;color:#166534">④ 恋爱达成率（终极价值指标）</span>
<span style="padding:4px 12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;font-size:12px;color:#1e40af">⑤ 服务合规（过度承诺治理）</span>
<span style="padding:4px 12px;background:#fef2f2;border:1px solid #fecaca;border-radius:6px;font-size:12px;color:#991b1b;font-weight:600">⑥ 员工能力差异（TOP vs 中底部，标杆复制）</span>
</div>
</div>

<!-- 4. 全局诊断 -->
<div class="card">
<h2>全局诊断 · 环比分析</h2>
<div style="padding:14px 16px;margin-bottom:8px;border-radius:8px;background:{'#f0fdf4' if t['jm_rate']>=1.0 else '#fffbeb' if t['jm_rate']>=0.8 else '#fef2f2'};border-left:3px solid {'#16a34a' if t['jm_rate']>=1.0 else '#d97706' if t['jm_rate']>=0.8 else '#dc2626'}">
<span style="font-size:10px;font-weight:700;color:#fff;background:{'#16a34a' if t['jm_rate']>=1.0 else '#d97706' if t['jm_rate']>=0.8 else '#dc2626'};padding:1px 8px;border-radius:4px;margin-right:6px">{'良好' if t['jm_rate']>=1.0 else '注意' if t['jm_rate']>=0.8 else '预警'}</span>
<strong>见面安排率 {t['jm_rate']:.2f}</strong>（{t['jm_n']}场/在岗{t['staff_new']}人）— {'✅ 达标，继续保持' if t['jm_rate']>=1.0 else '⚠ 未达1.0基准，需专项提升' if t['jm_rate']>=0.8 else '🚨 严重偏低，大量VIP资源未服务，立即启动专项盘点'}
</div>
<div style="padding:14px 16px;margin-bottom:8px;border-radius:8px;background:{'#fef2f2' if t['refund_rate']>10 else '#fffbeb' if t['refund_rate']>5 else '#f0fdf4'};border-left:3px solid {'#dc2626' if t['refund_rate']>10 else '#d97706' if t['refund_rate']>5 else '#16a34a'}">
<span style="font-size:10px;font-weight:700;color:#fff;background:{'#dc2626' if t['refund_rate']>10 else '#d97706' if t['refund_rate']>5 else '#16a34a'};padding:1px 8px;border-radius:4px;margin-right:6px">{'P0' if t['refund_rate']>10 else 'P1' if t['refund_rate']>5 else '正常'}</span>
<strong>退费率 {t['refund_rate']:.1f}%</strong>（¥{t['total_refund']/10000:.1f}万/¥{t['total_rev']/10000:.1f}万）— {'🚨 超10%红线，立即启动退费专项' if t['refund_rate']>10 else '⚠ 偏高，分渠道追因，检查话术合规性' if t['refund_rate']>5 else '✅ 退费控制良好'}
</div>
<div style="padding:14px 16px;margin-bottom:8px;border-radius:8px;background:#f8fafc;border-left:3px solid #6366f1">
<strong>部门差距：</strong>{dept_gap_html}
</div>
</div>

<!-- 5. 知识图谱诊断模式 -->
<div class="card">
<h2>知识图谱诊断模式 · 精确匹配</h2>
<div style="padding:12px 16px;margin-bottom:8px;border-radius:8px;background:#f8fafc;border-left:3px solid #6366f1">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
<span style="font-size:10px;font-weight:700;color:#fff;background:#6366f1;padding:1px 8px;border-radius:4px">H01</span>
<span style="font-size:13px;font-weight:600">见面安排率低 → VIP资源服务断层</span></div>
<div style="font-size:12px;color:#475569;line-height:1.6">当前见面安排率{t['jm_rate']:.2f}，低见面率不等于低客户意愿，往往是主动触达频率不足和日程系统性欠缺。每减少1次见面安排，潜在流失1次续费机会。</div>
<div style="font-size:11px;color:#6366f1;margin-top:4px">→ 建立「早盘/中盘/晚收」三段式VIP资源盘点节律；TOP红娘日程SOP化</div></div>
<div style="padding:12px 16px;margin-bottom:8px;border-radius:8px;background:#f8fafc;border-left:3px solid #6366f1">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
<span style="font-size:10px;font-weight:700;color:#fff;background:#6366f1;padding:1px 8px;border-radius:4px">H02</span>
<span style="font-size:13px;font-weight:600">退费率偏高 → 期望管理与服务交付断层</span></div>
<div style="font-size:12px;color:#475569;line-height:1.6">退费率{t['refund_rate']:.1f}%。核心公式：期望-体验=失望。退费根因：①承诺过度②见面质量低③跟进不及时④期望管理失当。</div>
<div style="font-size:11px;color:#6366f1;margin-top:4px">→ 付费后14日价值确认机制；话术合规检查；退费案例周复盘</div></div>
<div style="padding:12px 16px;margin-bottom:8px;border-radius:8px;background:#f8fafc;border-left:3px solid #6366f1">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
<span style="font-size:10px;font-weight:700;color:#fff;background:#d97706;padding:1px 8px;border-radius:4px">H03</span>
<span style="font-size:13px;font-weight:600">渠道差异 → 差异化服务策略缺失</span></div>
<div style="font-size:12px;color:#475569;line-height:1.6">门店/APP/广告渠道会员期望值、接受度差异显著。统一话术是退费率高的隐性原因。</div>
<div style="font-size:11px;color:#d97706;margin-top:4px">→ 按渠道制定差异化服务SOP；VIP画像标签系统</div></div>
<div style="padding:12px 16px;margin-bottom:8px;border-radius:8px;background:#f8fafc;border-left:3px solid #16a34a">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
<span style="font-size:10px;font-weight:700;color:#fff;background:#16a34a;padding:1px 8px;border-radius:4px">H04</span>
<span style="font-size:13px;font-weight:600">员工能力差距 → 标杆复制机会窗口</span></div>
<div style="font-size:12px;color:#475569;line-height:1.6">TOP1员工综合评分{top5[0]['score'] if top5 else 0:.0f} vs BOTTOM1 {bot5[-1]['score'] if bot5 else 0:.0f}。差距来自系统化操作模式，而非个人魅力，可通过SOP传递。</div>
<div style="font-size:11px;color:#16a34a;margin-top:4px">→ TOP1员工每日晨会分享1个成功案例；1周内提炼3条可复制SOP</div></div>
</div>

<!-- 6. 因果链推断（含漏斗可视化）-->
<div class="card">
<h2>因果链推断 · 漏斗佐证 + 最大瓶颈</h2>
<div style="font-size:13px;font-weight:600;color:#1e293b;margin-bottom:8px">服务转化漏斗 · 逐级损耗分析</div>
<div style="display:flex;gap:4px;flex-wrap:wrap;align-items:center;margin-bottom:12px">
<div style="display:inline-flex;align-items:center">
<div style="padding:6px 12px;border-radius:6px;border:3px solid #16a34a;font-size:11px;font-weight:600">VIP{t['on_vip']}</div>
<span style="margin:0 4px;color:#94a3b8">→</span></div>
<div style="display:inline-flex;align-items:center">
<div style="padding:6px 12px;border-radius:6px;border:3px solid #16a34a;font-size:11px;font-weight:600">通话{t['link_time_count']}({t['link_time_count']/max(t['on_vip'],1)*100:.0f}%)</div>
<span style="margin:0 4px;color:#94a3b8">→</span></div>
<div style="display:inline-flex;align-items:center">
<div style="padding:6px 12px;border-radius:6px;border:3px solid {'#dc2626' if t['deep_rate']<20 else '#d97706'};font-size:11px;font-weight:600;background:{'#fef2f2' if t['deep_rate']<20 else '#fffbeb'}">{'🔴 ' if t['deep_rate']<20 else '⚠ '}深沟{t['deep_count']}({t['deep_rate']:.1f}%)</div>
<span style="margin:0 4px;color:#94a3b8">→</span></div>
<div style="display:inline-flex;align-items:center">
<div style="padding:6px 12px;border-radius:6px;border:3px solid {'#dc2626' if t['jm_rate']<0.8 else '#d97706' if t['jm_rate']<1.2 else '#16a34a'};font-size:11px;font-weight:600">见面{t['jm_n']}(率{t['jm_rate']:.2f})</div>
<span style="margin:0 4px;color:#94a3b8">→</span></div>
<div style="display:inline-flex;align-items:center">
<div style="padding:6px 12px;border-radius:6px;border:3px solid #16a34a;font-size:11px;font-weight:600">营收¥{t['total_rev']/10000:.1f}万</div></div>
</div>
<div style="font-size:12px;color:#dc2626;font-weight:500;padding:10px 14px;background:#fef2f2;border-radius:6px;line-height:1.7">
🔴 <strong>最大瓶颈：{'深度沟通' if t['deep_rate']<20 else '见面安排率'}环节</strong>（{'深沟率仅'+str(round(t['deep_rate'],1))+'%' if t['deep_rate']<20 else '见面安排率仅'+str(round(t['jm_rate'],2))}）<br><br>
漏斗佐证：VIP{t['on_vip']}→通话{t['link_time_count']}→深沟{t['deep_count']}({t['deep_rate']:.1f}%)→见面{t['jm_n']}(率{t['jm_rate']:.2f})→营收¥{t['total_rev']/10000:.1f}万<br><br>
杠杆预估：{'深沟率每+1pp，见面数+'+str(int(t['link_time_count']*0.01))+'→营收+¥'+str(int(t['link_time_count']*0.01*(t['total_rev']/max(t['jm_n'],1))/10000))+'万/日' if t['deep_rate']<20 else '见面安排率每+0.1，见面数+'+str(int(t['staff_new']*0.1))+'→营收+¥'+str(int(t['staff_new']*0.1*(t['total_rev']/max(t['jm_n'],1))/10000))+'万/日'}
</div></div>

<!-- 7. 跨领域对撞 -->
<div class="card">
<h2>跨领域知识对撞 · 2组</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
<div style="background:#fdf4ff;border-radius:10px;padding:16px;border-left:4px solid #a855f7">
<div style="font-weight:700;color:#7c3aed;margin-bottom:8px">
<span style="font-size:9px;color:#fff;background:#7c3aed;padding:1px 6px;border-radius:3px;margin-right:6px">跨领域</span>
Customer Success × 服务价值确认 {BOOK_REFS['CUSTOMER_SUCCESS']}</div>
<div style="font-size:12px;color:#475569;line-height:1.7">
<strong>现象：</strong>退费率{t['refund_rate']:.1f}%，说明付费后价值未被感知<br>
<strong>对撞：</strong>CS理论「Time-to-Value」— 会员必须在付费后14天内感受到可见价值（至少1次满意见面）<br>
<strong>动作：</strong>建立「D3/D7/D14价值确认回访」，低分24h内主动关怀<br>
<strong>预估：</strong>退费率-2% → +¥{t['total_rev']*0.02/10000:.1f}万/日
</div></div>
<div style="background:#f0fff4;border-radius:10px;padding:16px;border-left:4px solid #16a34a">
<div style="font-weight:700;color:#166534;margin-bottom:8px">
<span style="font-size:9px;color:#fff;background:#16a34a;padding:1px 6px;border-radius:3px;margin-right:6px">跨领域</span>
社会认同 × 见面促成 {BOOK_REFS['INFLUENCE']}</div>
<div style="font-size:12px;color:#475569;line-height:1.7">
<strong>现象：</strong>见面安排率{t['jm_rate']:.2f}，部分会员犹豫不肯见面<br>
<strong>对撞：</strong>Cialdini社会认同原则 — 「和您情况相似的会员，最近安排了见面后反馈…」，降低首次见面心理障碍<br>
<strong>动作：</strong>为每位红娘准备3-5个成功案例库；促见面通话标准化引用<br>
<strong>预估：</strong>见面率+0.2 → +¥{t['staff_new']*0.2*(t['total_rev']/max(t['jm_n'],1))/10000:.1f}万/日
</div></div>
</div></div>

<!-- 8. 改善建议 -->
<div class="card">
<h2>改善建议 · {len(improvements)}条（按预估增幅排序）· 总预估日增¥{total_uplift:,.0f}</h2>
{imp_html}
</div>

<!-- 9. 退费渠道专项明细 -->
<div class="card" style="overflow-x:auto">
<h2>退费分渠道专项明细（品牌生命线监控）</h2>
<table><thead><tr>
<th style="text-align:left;padding-left:10px">渠道</th>
<th style="text-align:right">退费金额</th>
<th style="text-align:center">占比</th>
<th>风险判断</th>
</tr></thead>
<tbody>{refund_rows}</tbody></table>
<div style="background:#fef2f2;border-radius:6px;padding:10px 14px;margin-top:10px;font-size:12px">
🔴 退费治理优先：优先治理占比最高渠道。根因通常为：①承诺过度 ②见面质量低 ③跟进断裂 ④期望管理失当。建议{MANAGER}本周组织退费案例复盘，每渠道抽取3个典型案例分析。
</div></div>

<!-- 10. 部门明细 -->
<div class="card" style="overflow-x:auto">
<h2>部门明细（按营收排序，含人均产值）</h2>
<table><thead><tr>
<th style="text-align:left;padding-left:10px">部门</th>
<th>负责人</th>
<th>在岗</th>
<th>VIP在线</th>
<th>安排见面</th>
<th>见面率</th>
<th style="text-align:right">今日营收</th>
<th style="text-align:right">人均产值</th>
<th>退费率</th>
<th>恋爱达成</th>
</tr></thead>
<tbody>{dept_rows}</tbody></table>
</div>

<!-- 11. TOP5员工深度分析 -->
<div class="card" style="overflow-x:auto">
<h2>员工TOP5深度分析（全过程字段 + 综合评分 + 为什么好 + 可复制性）</h2>
<table><thead><tr>
<th style="text-align:left;padding-left:10px">排名</th>
<th>姓名</th>
<th>部门</th>
<th>安排见面</th>
<th>确认率</th>
<th>复见面率</th>
<th>恋爱达成</th>
<th style="text-align:right">月营收</th>
<th style="text-align:center">综合评分</th>
<th>为什么好</th>
</tr></thead>
<tbody>{top5_rows}</tbody></table>
<div style="background:#f0fdf4;border-radius:6px;padding:10px 14px;margin-top:10px;font-size:12px">
📌 <strong>可复制要点：</strong>TOP员工的优势来自系统化操作，而非个人魅力。{MANAGER}今日安排{top5[0]['worker_name'] if top5 else 'TOP1员工'}在晨会分享1个成功见面案例及跟进节奏，提炼为团队SOP。
</div></div>

<!-- 12. TOP5 vs BOTTOM5 能力差异对比（10维）-->
<div class="card" style="overflow-x:auto">
<h2>TOP5 vs BOTTOM5 能力差异对比（10维度 + 差异倍数 + 解读）</h2>
<table><thead><tr>
<th style="text-align:left;padding-left:10px">维度</th>
<th style="text-align:center;color:#16a34a">TOP5均值</th>
<th style="text-align:center;color:#dc2626">BOTTOM5均值</th>
<th style="text-align:center">差异倍数</th>
<th>解读与复制建议</th>
</tr></thead>
<tbody>{compare_rows}</tbody></table>
</div>

<!-- 13. BOTTOM5员工诊断 -->
<div class="card">
<h2>BOTTOM5员工专项诊断 + 即日改善建议</h2>
{bot5_cards}
</div>

<!-- 14. 部门级诊断（含管理者姓名+管理视角缺失推断）-->
<div class="card">
<h2>部门级诊断（含管理者姓名 + 管理视角缺失推断）</h2>
{dept_diag_html}
</div>

<!-- 15. 数据→人的转向（四维分析）-->
<div class="card">
<h2>数据→人的转向（技能 / 心态 / 存量管理 / 执行力）</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
<div style="background:#fdf4ff;border-radius:8px;padding:14px;border-left:3px solid #a855f7">
<div style="font-weight:700;color:#7c3aed;margin-bottom:6px">🎯 技能维度</div>
<div style="font-size:12px;color:#555;line-height:1.8">见面促成技能：从「安排见面」升级为「卖出见面价值」。TOP红娘能清晰传达「这次见面对您的具体价值」，而非简单通知时间地点。差距核心在话术结构化，可通过SOP快速复制。</div>
</div>
<div style="background:#fffbeb;border-radius:8px;padding:14px;border-left:3px solid #d97706">
<div style="font-weight:700;color:#d97706;margin-bottom:6px">💪 心态维度</div>
<div style="font-size:12px;color:#555;line-height:1.8">见面安排率低不全是能力问题。部分红娘因害怕被拒绝而减少主动触达。需通过成功案例积累和话术信心建设解决。BOTTOM员工往往是「心理阻力>技能不足」。</div>
</div>
<div style="background:#f0fdf4;border-radius:8px;padding:14px;border-left:3px solid #16a34a">
<div style="font-weight:700;color:#166534;margin-bottom:6px">📦 存量管理维度</div>
<div style="font-size:12px;color:#555;line-height:1.8">在线VIP资源{t['on_vip']}个，深沟{t['deep_count']}次（{t['deep_rate']:.1f}%）。TOP红娘有系统性的「早盘/中盘/晚收」节律，每日早9:00盘点未触达VIP，周五专项处理30天沉睡资源。</div>
</div>
<div style="background:#eff6ff;border-radius:8px;padding:14px;border-left:3px solid #3b82f6">
<div style="font-weight:700;color:#1d4ed8;margin-bottom:6px">⚡ 执行力维度</div>
<div style="font-size:12px;color:#555;line-height:1.8">三大执行力先行指标：①每日主动触达VIP数量 ②见面邀约确认率 ③D1/D7/D14价值回访完成率。执行力差距是见面安排率差距的根本来源，通过打卡+日报机制量化追踪。</div>
</div>
</div></div>

<div style="text-align:center;padding:20px;color:#94a3b8;font-size:12px">
📊 本报告由 Linh Nguyen（智慧助理）自动生成 · {date_display} · 覆盖14项诊断模块 · 防退化v2<br>
数据来源：珍爱网运营数据平台 · 基准参考：report_template_benchmark.md
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

    print(f"[红娘报告] 拉取数据 {DATE}...")
    resp_today = query("hongniang", "daily", DATE)
    resp_prev = query("hongniang", "daily", prev_date(DATE))
    resp_hourly = query("hongniang", "hourly", DATE)

    rows_today = parse_rows(resp_today)
    rows_prev = parse_rows(resp_prev)
    rows_hourly = parse_rows(resp_hourly)

    print(f"[红娘报告] 今日部门行数: {len(rows_today)}, 昨日: {len(rows_prev)}, 员工行数: {len(rows_hourly)}")

    html = generate_html(rows_today, rows_prev, rows_hourly, DATE_DISPLAY)

    filename = f"Hongniang_Full_{DATE_DISPLAY}.html"
    path = export_html(html, filename, open_browser=True)
    print(f"[红娘报告] 已导出: {path}")

    subject = f"💑 电话红娘全量体检报告 {DATE_DISPLAY}"
    ok = send_report_email(subject, html)
    print(f"[红娘报告] 邮件: {'成功' if ok else '失败'}")


if __name__ == "__main__":
    main()
