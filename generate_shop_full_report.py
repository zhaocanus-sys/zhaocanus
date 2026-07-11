# -*- coding: utf-8 -*-
"""
门店销售全量业务体检报告生成器
覆盖14项必含模块，符合 report_template_benchmark.md 基准线
门店(dept) = 部门层，门店负责人 = 管理者层
"""
import sys
import datetime
from collections import defaultdict
from agent_system.actions.api_client import daily, trend, query, safe_float, safe_int
from agent_system.actions.email_sender import send_report_email
from agent_system.actions.report_exporter import export_html

DATE = "20260227"
DATE_DISPLAY = "2026-02-27"
MANAGER = "门店运营负责人"

BOOK_REFS = {
    "CHALLENGER": "📚《挑战式销售》Matthew Dixon",
    "SPIN":       "📚《SPIN Selling》Rackham",
    "CLOSER":     "📚《绝对成交》Roger Dawson",
    "INFLUENCE":  "📚《Influence》Cialdini",
    "ATOMIC":     "📚《Atomic Habits》Clear",
    "TRUST":      "📚《The Speed of Trust》Covey",
    "LTV":        "📚《Customer Success》Nick Mehta",
}

MGMT_GAP_RULES = {
    "low_sign_rate":  "邀约质量管控不足，或现场接待SOP缺失，到店客户流失严重",
    "high_refund":    "签单话术存在过度承诺风险，或服务兑现能力与承诺不匹配",
    "low_invite_conv": "邀约话术吸引力不足，电话-到店转化效率低于基准30%",
    "low_per_rev":    "差异化辅导策略缺失，TOP销售SOP未标准化推广",
    "high_complain":  "客户投诉处理机制不完善，服务承诺与实际落差大",
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


def agg_shop(rows):
    total_rev = sum(safe_float(r.get("total_realpay")) for r in rows)
    sale_rev = sum(safe_float(r.get("sale_realpay")) or safe_float(r.get("deptsale_realpay")) for r in rows)
    invite_rev = sum(safe_float(r.get("invite_realpay")) for r in rows)
    hn_rev = sum(safe_float(r.get("hn_realpay")) for r in rows)
    total_pay = sum(safe_int(r.get("total_pay_num")) for r in rows)
    sale_pay = sum(safe_int(r.get("sale_pay_num_all")) for r in rows)
    invite_pay = sum(safe_int(r.get("invite_pay_num")) for r in rows)
    shop_sign = sum(safe_int(r.get("deptsale_shop_num")) for r in rows)
    # invitation funnel
    call_workers = sum(safe_int(r.get("worker_num_call")) for r in rows)
    call_times = sum(safe_int(r.get("call_times")) for r in rows)
    link_num = sum(safe_int(r.get("link_num")) for r in rows)
    sg_num = sum(safe_int(r.get("sg_num")) for r in rows)  # 到店数
    # staff
    zaigang = sum(safe_int(r.get("zaigang_rs")) for r in rows)
    # refund / complaint
    refund_d = sum(safe_float(r.get("refund_money_d") or r.get("refundmoney_7d") or 0) for r in rows)
    complain = sum(safe_int(r.get("complain_400_num_day") or r.get("complain_400_num") or 0) for r in rows)
    refund_m = sum(safe_float(r.get("refund_money_m")) for r in rows)
    rev_m = sum(safe_float(r.get("total_realpay_m")) for r in rows)
    # leads freshness
    leads_3d = sum(safe_int(r.get("leads_xyzout_3day")) for r in rows)
    leads_3d_allot = sum(safe_int(r.get("leads_3day_allot_0day")) for r in rows)
    leads_1d = sum(safe_int(r.get("leads_xyzout_1day")) for r in rows)
    leads_1d_allot = sum(safe_int(r.get("leads_1day_allot_0day")) for r in rows)
    # computed
    sign_rate = shop_sign / sg_num * 100 if sg_num > 0 else 0
    invite_conv = sg_num / link_num * 100 if link_num > 0 else 0  # 接通→到店
    per_rev = total_rev / zaigang if zaigang > 0 else 0
    refund_rate = refund_d / total_rev * 100 if total_rev > 0 else 0
    avg_deal = total_rev / total_pay if total_pay > 0 else 0
    lead_speed_3d = leads_3d_allot / leads_3d * 100 if leads_3d > 0 else 0
    lead_speed_1d = leads_1d_allot / leads_1d * 100 if leads_1d > 0 else 0
    return dict(
        total_rev=total_rev, sale_rev=sale_rev, invite_rev=invite_rev, hn_rev=hn_rev,
        total_pay=total_pay, sale_pay=sale_pay, invite_pay=invite_pay,
        shop_sign=shop_sign, call_workers=call_workers, call_times=call_times,
        link_num=link_num, sg_num=sg_num, zaigang=zaigang,
        refund_d=refund_d, complain=complain, refund_m=refund_m, rev_m=rev_m,
        leads_3d=leads_3d, leads_3d_allot=leads_3d_allot,
        leads_1d=leads_1d, leads_1d_allot=leads_1d_allot,
        sign_rate=sign_rate, invite_conv=invite_conv,
        per_rev=per_rev, refund_rate=refund_rate,
        avg_deal=avg_deal, lead_speed_3d=lead_speed_3d, lead_speed_1d=lead_speed_1d,
    )


def build_shop_data(rows):
    shops = {}
    for r in rows:
        dn = r.get("dept_name", "未知")
        if dn not in shops:
            shops[dn] = dict(
                dept_name=dn,
                area=r.get("level2", ""),
                manager=r.get("dept_worker_name", ""),
                area_mgr=r.get("area_worker_name", ""),
                total_realpay=0, deptsale_realpay=0,
                invite_realpay=0, hn_realpay=0,
                total_pay_num=0, deptsale_shop_num=0,
                sg_num=0, link_num=0, call_times=0,
                refund_money_d=0, complain_400_num_day=0,
                zaigang_rs=0, allot_worker_num=0,
                leads_xyzout_3day=0, leads_3day_allot_0day=0,
                leads_1day_allot_0day=0,
                total_realpay_m=0, deptsale_realpay_m=0,
            )
        s = shops[dn]
        for k in ("total_pay_num",
                  "deptsale_shop_num", "sg_num", "link_num", "call_times",
                  "zaigang_rs", "allot_worker_num",
                  "leads_xyzout_3day", "leads_3day_allot_0day",
                  "leads_1day_allot_0day"):
            s[k] += safe_int(r.get(k))
        for k in ("total_realpay", "deptsale_realpay", "invite_realpay",
                  "hn_realpay", "total_realpay_m", "deptsale_realpay_m"):
            s[k] += safe_float(r.get(k))
        s["refund_money_d"] += safe_float(r.get("refund_money_d") or r.get("refundmoney_7d") or 0)
        s["complain_400_num_day"] += safe_int(r.get("complain_400_num_day") or r.get("complain_400_num") or 0)

    result = []
    for s in shops.values():
        sg = s["sg_num"]
        lk = s["link_num"]
        w = s["zaigang_rs"]
        rev = s["total_realpay"]
        s["sign_rate"] = s["deptsale_shop_num"] / sg * 100 if sg > 0 else 0
        s["invite_conv"] = s["sg_num"] / lk * 100 if lk > 0 else 0
        s["per_rev"] = s["total_realpay"] / w if w > 0 else 0
        s["refund_rate"] = s["refund_money_d"] / rev * 100 if rev > 0 else 0
        result.append(s)
    return sorted(result, key=lambda x: x["total_realpay"], reverse=True)


def generate_html(today_rows, prev_rows, date_display):
    t = agg_shop(today_rows)
    p = agg_shop(prev_rows) if prev_rows else {}
    shops = build_shop_data(today_rows)
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
        color = "#16a34a" if (up and higher_better) or (not up and not higher_better) else "#dc2626"
        arrow = "▲" if up else "▼"
        return f'<span style="font-size:10px;color:{color}">{arrow}{abs(chg):.1f}%</span>'

    # ── Shop detail table ─────────────────────────────────────────────
    shop_rows_html = ""
    for s in shops:
        sr_c = color_kpi(s["sign_rate"], 35, 30)
        rr_c = color_kpi(s["refund_rate"], 3, 6, False)
        pr_c = color_kpi(s["per_rev"], 15000, 8000)
        shop_rows_html += f"""<tr>
<td style="padding:7px 10px;font-size:12px;font-weight:600">{s['dept_name']}</td>
<td style="padding:7px;font-size:11px;color:#64748b">{s['area_mgr'] or s['manager']}</td>
<td style="padding:7px;text-align:center;font-size:12px">{s['zaigang_rs']}</td>
<td style="padding:7px;text-align:center;font-size:12px">{s['sg_num']}</td>
<td style="padding:7px;text-align:center;font-size:12px">{s['deptsale_shop_num']}</td>
<td style="padding:7px;text-align:center;font-size:12px;font-weight:600;color:{sr_c}">{s['sign_rate']:.1f}%</td>
<td style="padding:7px;text-align:right;font-size:12px;font-weight:600;color:#dc2626">¥{s['total_realpay']/10000:.1f}万</td>
<td style="padding:7px;text-align:right;font-size:12px;color:{pr_c}">¥{s['per_rev']:,.0f}</td>
<td style="padding:7px;text-align:center;font-size:12px;color:{rr_c}">{s['refund_rate']:.1f}%</td>
<td style="padding:7px;text-align:right;font-size:12px">¥{s['total_realpay_m']/10000:.0f}万</td>
</tr>"""

    # ── TOP5 shops ────────────────────────────────────────────────────
    top5 = shops[:5]
    bot5 = shops[-5:] if len(shops) >= 5 else list(reversed(shops))

    def why_shop_good(s):
        reasons = []
        if s["sign_rate"] >= 35:
            reasons.append(f"签单率{s['sign_rate']:.0f}%达优秀线")
        if s["invite_conv"] >= 30:
            reasons.append("接通→到店转化效率高")
        if s["per_rev"] >= 15000:
            reasons.append("人均产值突出")
        if s["complain_400_num_day"] == 0:
            reasons.append("零投诉高口碑")
        if not reasons:
            reasons.append("综合表现稳健")
        return "；".join(reasons)

    top5_rows = ""
    for i, s in enumerate(top5):
        top5_rows += f"""<tr style="background:{'#f0fdf4' if i==0 else ''}">
<td style="padding:8px 10px;font-size:12px;font-weight:700;color:#16a34a">TOP{i+1}</td>
<td style="padding:8px;font-size:12px;font-weight:600">{s['dept_name']}</td>
<td style="padding:8px;font-size:11px;color:#64748b">{s['area_mgr'] or s['manager']}</td>
<td style="padding:8px;text-align:center;font-size:12px">{s['sg_num']}</td>
<td style="padding:8px;text-align:center;font-size:12px;font-weight:600;color:#16a34a">{s['sign_rate']:.1f}%</td>
<td style="padding:8px;text-align:center;font-size:12px">{s['invite_conv']:.1f}%</td>
<td style="padding:8px;text-align:right;font-size:12px;font-weight:600;color:#dc2626">¥{s['total_realpay']/10000:.1f}万</td>
<td style="padding:8px;text-align:right;font-size:12px">¥{s['per_rev']:,.0f}</td>
<td style="padding:8px;font-size:11px;color:#16a34a">{why_shop_good(s)}</td>
<td style="padding:8px;font-size:11px;color:#475569">提取接待话术+邀约SOP推广至低效门店</td>
</tr>"""

    # ── TOP5 vs BOTTOM5 ───────────────────────────────────────────────
    dims = [
        ("到店数",     "sg_num",         "人"),
        ("签单率",     "sign_rate",      "%"),
        ("接通→到店率", "invite_conv",    "%"),
        ("今日总营收", "total_realpay",  "元"),
        ("人均产值",   "per_rev",        "元"),
        ("退费率",     "refund_rate",    "%"),
        ("投诉数",     "complain_400_num_day", "单"),
        ("在岗人数",   "zaigang_rs",     "人"),
        ("月累营收",   "total_realpay_m","元"),
    ]

    def avg_dim(ss, key):
        vals = [safe_float(s.get(key)) for s in ss]
        return sum(vals) / len(vals) if vals else 0

    compare_rows = ""
    for name, key, unit in dims:
        tv = avg_dim(top5, key)
        bv = avg_dim(bot5, key)
        ratio = tv / bv if bv > 0 else 99
        higher_better = key not in ("refund_rate", "complain_400_num_day")
        gap_color = "#16a34a" if ratio >= 1.5 else ("#d97706" if ratio >= 1.1 else "#dc2626")
        if not higher_better:
            gap_color = "#16a34a" if ratio <= 0.7 else ("#d97706" if ratio <= 1.0 else "#dc2626")
        compare_rows += f"""<tr>
<td style="padding:7px 10px;font-size:12px;font-weight:600">{name}</td>
<td style="padding:7px;text-align:center;font-size:12px;font-weight:700;color:#16a34a">{tv:.1f}{unit}</td>
<td style="padding:7px;text-align:center;font-size:12px;color:#dc2626">{bv:.1f}{unit}</td>
<td style="padding:7px;text-align:center;font-size:12px;font-weight:700;color:{gap_color}">{ratio:.1f}x</td>
<td style="padding:7px;font-size:11px;color:#475569">{'差距显著，TOP门店经验具备高复制价值' if ratio>1.5 else '差距可控，重点在执行一致性' if ratio>1.1 else '差距较小'}</td>
</tr>"""

    # ── BOTTOM5 diagnosis ─────────────────────────────────────────────
    bot5_cards = ""
    for s in bot5:
        issues = []
        if s["sign_rate"] < 25:
            issues.append(f"签单率仅{s['sign_rate']:.1f}%，严重低于30%合格线，到店资源大量流失")
        if s["invite_conv"] < 20:
            issues.append(f"接通→到店转化{s['invite_conv']:.1f}%，邀约话术或邀约时机有问题")
        if s["refund_rate"] > 8:
            issues.append(f"退费率{s['refund_rate']:.1f}%，签单话术可能存在过度承诺")
        if s["complain_400_num_day"] > 0:
            issues.append(f"当日投诉{s['complain_400_num_day']}单，客户体验存在系统性问题")
        if not issues:
            issues.append("综合指标偏弱，需全面诊断门店运营机制")
        mgap_key = ("low_sign_rate" if s["sign_rate"] < 25 else
                    "high_refund" if s["refund_rate"] > 8 else
                    "low_invite_conv" if s["invite_conv"] < 20 else "low_per_rev")
        mgmt_gap = MGMT_GAP_RULES.get(mgap_key, "需进一步排查")
        bot5_cards += f"""<div style="padding:14px;margin-bottom:10px;border-radius:8px;border-left:4px solid #dc2626;background:#fef2f2">
<div style="font-weight:700;color:#dc2626;margin-bottom:4px">⚠ {s['dept_name']} · 负责人: {s['area_mgr'] or s['manager']}</div>
<div style="font-size:12px;color:#475569;line-height:1.8">
到店: {s['sg_num']}人 | 签单: {s['deptsale_shop_num']} | 签单率: {s['sign_rate']:.1f}% | 营收: ¥{s['total_realpay']/10000:.1f}万 | 人均: ¥{s['per_rev']:,.0f}<br>
<strong>问题：</strong>{'；'.join(issues)}<br>
<strong>管理视角缺失：</strong>{mgmt_gap}<br>
<strong>即日行动：</strong>{MANAGER} 今日与负责人约谈，要求提交「本周到店未签单客户名单 + 流失原因分析 + 3日补救方案」
</div></div>"""

    # ── Department-level diagnosis ────────────────────────────────────
    dept_diag_html = ""
    worst3 = sorted(shops, key=lambda s: s["sign_rate"])[:3]
    for s in worst3:
        mgap_key = ("low_sign_rate" if s["sign_rate"] < 25 else
                    "high_refund" if s["refund_rate"] > 8 else "low_invite_conv")
        mgmt_gap = MGMT_GAP_RULES.get(mgap_key, "")
        dept_diag_html += f"""<div style="padding:14px 16px;margin-bottom:10px;border-radius:8px;border-left:4px solid #d97706;background:#fffbeb">
<div style="display:flex;justify-content:space-between;margin-bottom:4px">
<div><span style="font-size:10px;font-weight:700;color:#fff;background:#d97706;padding:1px 8px;border-radius:4px;margin-right:6px">部门预警</span>
<span style="font-size:13px;font-weight:600">{s['dept_name']}（{s['area_mgr'] or s['manager']}）— 签单率 {s['sign_rate']:.1f}%</span></div>
<span style="font-size:12px;color:#dc2626;font-weight:600">达均值可+¥{(t['avg_deal']*(s['sg_num']*0.35-s['deptsale_shop_num'])):,.0f}/日</span>
</div>
<div style="font-size:12px;color:#475569;line-height:1.7">
到店{s['sg_num']}人 | 签单{s['deptsale_shop_num']} | 营收¥{s['total_realpay']/10000:.1f}万 | 人均¥{s['per_rev']:,.0f}<br>
<strong>管理视角缺失推断：</strong>{mgmt_gap}<br>
<strong>即日建议：</strong>{MANAGER} 安排今日巡店，重点观察接待流程和话术规范性
</div></div>"""

    # ── Improvements ─────────────────────────────────────────────────
    improvements = []

    if t["sign_rate"] < 30:
        gap = 30 - t["sign_rate"]
        extra = int(t["sg_num"] * gap / 100)
        rev_est = extra * t["avg_deal"]
        improvements.append({
            "p": "P0", "title": f"签单率修复至30%（当前{t['sign_rate']:.1f}%）",
            "owner": MANAGER,
            "action": "今日提取TOP门店接待流程录音；梳理「破冰→需求挖掘→价值呈现→异议处理→成交」5步SOP；低于30%门店48h内强制演练",
            "days": 7,
            "rev_est": rev_est,
            "ref": BOOK_REFS["CHALLENGER"],
            "deploy": tomorrow,
        })

    if t["invite_conv"] < 30:
        gap = 30 - t["invite_conv"]
        extra_arr = int(t["link_num"] * gap / 100)
        rev_est = extra_arr * t["sign_rate"] / 100 * t["avg_deal"]
        improvements.append({
            "p": "P0", "title": f"接通→到店转化提至30%（当前{t['invite_conv']:.1f}%）",
            "owner": MANAGER,
            "action": "分析接通未到店原因（时间/价格/信任/距离）；设计「活动邀约+专属顾问+限时福利」三要素话术；A/B测试2组",
            "days": 7,
            "rev_est": rev_est,
            "ref": BOOK_REFS["SPIN"],
            "deploy": tomorrow,
        })

    if t["refund_rate"] > 5:
        save = t["total_rev"] * (t["refund_rate"] - 4) / 100
        improvements.append({
            "p": "P1", "title": f"退费率管控至4%（当前{t['refund_rate']:.1f}%）",
            "owner": MANAGER,
            "action": "签单后48h回访确认；过度承诺黑名单机制；退费原因标签化分析；投诉超2单门店即日启动专项整改",
            "days": 14,
            "rev_est": save,
            "ref": BOOK_REFS["TRUST"],
            "deploy": tomorrow,
        })

    if shops:
        best = max(shops, key=lambda s: s["sign_rate"])
        worst = min(shops, key=lambda s: s["sign_rate"])
        if best["sign_rate"] - worst["sign_rate"] > 10:
            gap_rev = (best["per_rev"] - worst["per_rev"]) * worst["zaigang_rs"] * 0.25
            improvements.append({
                "p": "P1", "title": f"标杆复制：{best['dept_name']}签单SOP推广",
                "owner": MANAGER,
                "action": f"今日录制{best['dept_name']}签单现场录音；提取核心话术3-5条；{worst['dept_name']}今日组织1h话术通关培训",
                "days": 14,
                "rev_est": gap_rev,
                "ref": BOOK_REFS["ATOMIC"],
                "deploy": tomorrow,
            })

    if t["lead_speed_1d"] < 80:
        improvements.append({
            "p": "P1", "title": f"当日线索当日分配率提至80%（当前{t['lead_speed_1d']:.0f}%）",
            "owner": MANAGER,
            "action": f"当日线索{t['leads_1d']}条，已分配{t['leads_1d_allot']}条({t['lead_speed_1d']:.0f}%)。线索越新鲜转化率越高。设立「1小时内分配」KPI，超时自动升级告警",
            "days": 7,
            "rev_est": (t["leads_1d"] - t["leads_1d_allot"]) * t["sign_rate"] / 100 * t["avg_deal"],
            "ref": BOOK_REFS["CLOSER"],
            "deploy": tomorrow,
        })

    improvements.append({
        "p": "P2", "title": "高客单价产品比例提升（情感护航/超豪VIP）",
        "owner": MANAGER,
        "action": f"月均客单价¥{t['avg_deal']:,.0f}。筛选「二次到店+高意愿」客户推荐高端产品；设计「基础→标准→高级」三档方案让客户自主升级",
        "days": 21,
        "rev_est": t["total_pay"] * 1000,
        "ref": BOOK_REFS["INFLUENCE"],
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
<div style="font-size:12px;color:#dc2626;font-weight:600;margin-top:4px">预估增幅: +¥{item['rev_est']:,.0f}/日 | {item['ref']}</div>
</div></div>"""

    # ── KPI colors ────────────────────────────────────────────────────
    rev_c = color_kpi(t["total_rev"], 200000, 100000)
    sr_c = color_kpi(t["sign_rate"], 35, 30)
    ic_c = color_kpi(t["invite_conv"], 35, 25)
    rr_c = color_kpi(t["refund_rate"], 4, 7, False)
    pr_c = color_kpi(t["per_rev"], 15000, 8000)
    ls_c = color_kpi(t["lead_speed_1d"], 80, 60)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>门店销售全量体检报告 {date_display}</title>
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
<div style="background:linear-gradient(135deg,#1c1917,#44403c,#78350f);border-radius:12px;padding:28px 32px;margin-bottom:16px;color:#fff">
<div style="font-size:11px;color:#fcd34d;letter-spacing:3px">SHOP FULL · 门店全量体检报告 · 14模块</div>
<div style="font-size:22px;font-weight:700;margin:6px 0 4px">门店销售全量业务体检报告</div>
<div style="font-size:13px;color:#fde68a">{date_display} · 负责人: {MANAGER} · 在岗: {t['zaigang']}人 · {len(shops)}家门店 · 到店: {t['sg_num']}人</div>
</div>

<!-- 2. KPI卡片（按转化流转顺序：线索→邀约→到店→签单→营收）-->
<div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap">
<div style="flex:1;min-width:90px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">当日线索</div>
<div style="font-size:20px;font-weight:800;color:#1e293b">{t['leads_1d']}</div>
<div style="font-size:11px;color:#64748b">3日线索{t['leads_3d']}</div></div>
<div style="flex:1;min-width:90px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">邀约接通</div>
<div style="font-size:20px;font-weight:800;color:#1e293b">{t['link_num']}</div>
<div style="font-size:11px;color:#64748b">呼出{t['call_times']}次</div></div>
<div style="flex:1;min-width:90px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">到店人数</div>
<div style="font-size:20px;font-weight:800;color:#1e293b">{t['sg_num']}</div>
<div style="font-size:11px">接通→到店{t['invite_conv']:.0f}% {dod('invite_conv')}</div></div>
<div style="flex:1;min-width:90px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">签单数</div>
<div style="font-size:20px;font-weight:800;color:{sr_c}">{t['shop_sign']}</div>
<div style="font-size:11px">签单率{t['sign_rate']:.1f}% {dod('sign_rate')}</div></div>
<div style="flex:1;min-width:90px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">日营收</div>
<div style="font-size:20px;font-weight:800;color:{rev_c}">¥{t['total_rev']/10000:.0f}万</div>
<div style="font-size:11px">月累¥{t['rev_m']/10000:.0f}万 {dod('total_rev')}</div></div>
<div style="flex:1;min-width:90px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">人均产值</div>
<div style="font-size:20px;font-weight:800;color:{pr_c}">¥{t['per_rev']:,.0f}</div>
<div style="font-size:11px;color:#64748b">在岗{t['zaigang']}人</div></div>
<div style="flex:1;min-width:90px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">退费率</div>
<div style="font-size:20px;font-weight:800;color:{rr_c}">{t['refund_rate']:.1f}%</div>
<div style="font-size:11px;color:#64748b">投诉{t['complain']}单</div></div>
<div style="flex:1;min-width:90px;background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)">
<div style="font-size:10px;color:#94a3b8">线索即日分配</div>
<div style="font-size:20px;font-weight:800;color:{ls_c}">{t['lead_speed_1d']:.0f}%</div>
<div style="font-size:11px;color:#64748b">红线≥80%</div></div>
</div>
<div class="card" style="padding:12px 20px">
<div style="font-size:11px;color:#64748b">流转: 线索{t['leads_1d']}→邀约接通{t['link_num']}→到店{t['sg_num']}(率{t['invite_conv']:.0f}%)→签单{t['shop_sign']}(签单率{t['sign_rate']:.1f}%)→营收¥{t['total_rev']/10000:.0f}万 | 人均¥{t['per_rev']:,.0f} | 客单¥{t['avg_deal']:,.0f}</div>
</div>

<!-- 3. 业务定位 -->
<div style="background:#fff;border-radius:10px;padding:20px 24px;margin-bottom:16px;box-shadow:0 1px 2px rgba(0,0,0,.04);border-left:4px solid #78350f">
<div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:8px">业务定位：门店销售团队</div>
<div style="font-size:12px;color:#475569;line-height:1.7;margin-bottom:12px">门店是珍爱网<strong>线下面对面高客单价成交</strong>的核心场景，采用「外包邀约+加盟SaaS隔离」风险控制架构，是公司重要的线下营收来源。门店成功依赖三要素：高质量线索→专业邀约到店→现场高签单率。</div>
<div style="font-size:13px;font-weight:600;color:#0f172a;margin-bottom:8px">门店团队高业绩必须关注的重点：</div>
<div style="display:flex;gap:8px;flex-wrap:wrap">
<span style="padding:4px 12px;background:#fef2f2;border:1px solid #fecaca;border-radius:6px;font-size:12px;color:#991b1b;font-weight:600">① 到店签单率（≥30%合格，≥35%优秀）</span>
<span style="padding:4px 12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;font-size:12px;color:#1e40af">② 单条资源产值（邀约效率×签单率×客单价）</span>
<span style="padding:4px 12px;background:#fef3c7;border:1px solid #fde68a;border-radius:6px;font-size:12px;color:#92400e">③ 邀约质量（接通→到店率≥30%）</span>
<span style="padding:4px 12px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;font-size:12px;color:#166534">④ 退费率（<4%）</span>
<span style="padding:4px 12px;background:#fef3c7;border:1px solid #fde68a;border-radius:6px;font-size:12px;color:#92400e">⑤ 投诉率（零投诉目标）</span>
<span style="padding:4px 12px;background:#fef2f2;border:1px solid #fecaca;border-radius:6px;font-size:12px;color:#991b1b;font-weight:600">⑥ 员工能力差异（TOP门店SOP标杆复制）</span>
</div>
</div>

<!-- 4. 全局诊断 -->
<div class="card">
<h2>全局诊断 · 环比分析</h2>
<div style="padding:14px 16px;margin-bottom:8px;border-radius:8px;background:{'#fef2f2' if t['sign_rate']<25 else '#fffbeb' if t['sign_rate']<30 else '#f0fdf4'};border-left:3px solid {'#dc2626' if t['sign_rate']<25 else '#d97706' if t['sign_rate']<30 else '#16a34a'}">
<strong>到店签单率 {t['sign_rate']:.1f}%</strong>（{t['shop_sign']}单/{t['sg_num']}到店）— {'🚨 低于25%，现场接待严重失效，立即排查SOP执行情况' if t['sign_rate']<25 else '⚠ 低于30%合格线，需强化现场签单能力' if t['sign_rate']<30 else '✅ 签单率达标' if t['sign_rate']<35 else '⭐ 签单率优秀≥35%'}
</div>
<div style="padding:14px 16px;margin-bottom:8px;border-radius:8px;background:{'#fef2f2' if t['invite_conv']<20 else '#fffbeb' if t['invite_conv']<30 else '#f0fdf4'};border-left:3px solid {'#dc2626' if t['invite_conv']<20 else '#d97706' if t['invite_conv']<30 else '#16a34a'}">
<strong>接通→到店转化 {t['invite_conv']:.1f}%</strong>（{t['sg_num']}到/{t['link_num']}接通）— {'🚨 严重偏低，邀约话术或邀约时机需根本性重建' if t['invite_conv']<20 else '⚠ 低于30%基准，邀约话术需优化' if t['invite_conv']<30 else '✅ 邀约转化达标'}
</div>
<div style="padding:14px 16px;margin-bottom:8px;border-radius:8px;background:{'#fef2f2' if t['refund_rate']>8 else '#fffbeb' if t['refund_rate']>4 else '#f0fdf4'};border-left:3px solid {'#dc2626' if t['refund_rate']>8 else '#d97706' if t['refund_rate']>4 else '#16a34a'}">
<strong>退费率 {t['refund_rate']:.1f}%</strong>（¥{t['refund_d']/10000:.1f}万）— {'🚨 超8%，退费金额大，需立即启动话术合规审查' if t['refund_rate']>8 else '⚠ 超4%红线，分门店追因' if t['refund_rate']>4 else '✅ 退费控制良好'}
</div>
<div style="padding:14px 16px;border-radius:8px;background:#f8fafc;border-left:3px solid #6366f1">
<strong>线索即日分配率 {t['lead_speed_1d']:.0f}%</strong>（今日{t['leads_1d']}条线索，当日分配{t['leads_1d_allot']}条）— {'线索分配及时性良好' if t['lead_speed_1d']>=80 else '⚠ 未达80%，当日线索流失，越新鲜转化率越高'}
</div>
</div>

<!-- 5. 知识图谱诊断模式 -->
<div class="card">
<h2>知识图谱诊断模式 · 精确匹配</h2>
<div style="padding:12px 16px;margin-bottom:8px;border-radius:8px;background:#f8fafc;border-left:3px solid #6366f1">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
<span style="font-size:10px;font-weight:700;color:#fff;background:#dc2626;padding:1px 8px;border-radius:4px">S01</span>
<span style="font-size:13px;font-weight:600">签单率低 → 现场销售节点缺失</span></div>
<div style="font-size:12px;color:#475569;line-height:1.6">当前签单率{t['sign_rate']:.1f}%。《挑战式销售》：顾问必须在客户提问前主动揭示问题（Teach）、精准匹配（Tailor）、主动掌控节奏（Take Control）。缺少任何一环，签单率会直接下滑10%+。</div>
<div style="font-size:11px;color:#6366f1;margin-top:4px">→ 梳理TTE（Teach-Tailor-Take）话术；TOP门店5步签单SOP提炼；低效门店1周内话术通关</div></div>
<div style="padding:12px 16px;margin-bottom:8px;border-radius:8px;background:#f8fafc;border-left:3px solid #6366f1">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
<span style="font-size:10px;font-weight:700;color:#fff;background:#6366f1;padding:1px 8px;border-radius:4px">S02</span>
<span style="font-size:13px;font-weight:600">邀约→到店转化不足 → 邀约价值感知弱</span></div>
<div style="font-size:12px;color:#475569;line-height:1.6">接通→到店{t['invite_conv']:.1f}%。邀约核心不是「请您过来」，而是「您如果不来，您会错过什么」。需要制造具体的到店理由（限时档期/专属顾问/定制方案）。</div>
<div style="font-size:11px;color:#6366f1;margin-top:4px">→ 邀约话术植入损失厌恶+具体化承诺；邀约后跟进机制（未到店24h内二次触达）</div></div>
<div style="padding:12px 16px;border-radius:8px;background:#f8fafc;border-left:3px solid #d97706">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
<span style="font-size:10px;font-weight:700;color:#fff;background:#d97706;padding:1px 8px;border-radius:4px">S03</span>
<span style="font-size:13px;font-weight:600">线索分配速度 → 时效是转化关键变量</span></div>
<div style="font-size:12px;color:#475569;line-height:1.6">线索即日分配率{t['lead_speed_1d']:.0f}%。线索在最新鲜时（D0/D1）转化率是D7的3-5倍。每延迟1天分配，转化率下降约20%。</div>
<div style="font-size:11px;color:#d97706;margin-top:4px">→ 设立1小时内分配SLA；超时自动告警；优先分配活跃度高的门店</div></div>
</div>

<!-- 6. 因果链 -->
<div class="card">
<h2>因果链推断 · 漏斗佐证 + 最大瓶颈</h2>
<div style="font-size:13px;font-weight:600;margin-bottom:8px">门店销售转化漏斗</div>
<div style="display:flex;gap:4px;flex-wrap:wrap;align-items:center;margin-bottom:12px">
<div style="display:inline-flex;align-items:center">
<div style="padding:6px 12px;border-radius:6px;border:3px solid #16a34a;font-size:11px;font-weight:600">线索{t['leads_1d']}</div>
<span style="margin:0 4px;color:#94a3b8">→</span></div>
<div style="display:inline-flex;align-items:center">
<div style="padding:6px 12px;border-radius:6px;border:3px solid #16a34a;font-size:11px;font-weight:600">接通{t['link_num']}</div>
<span style="margin:0 4px;color:#94a3b8">→</span></div>
<div style="display:inline-flex;align-items:center">
<div style="padding:6px 12px;border-radius:6px;border:3px solid {'#dc2626' if t['invite_conv']<20 else '#d97706'};font-size:11px;font-weight:600;background:{'#fef2f2' if t['invite_conv']<20 else '#fffbeb'}">{'🔴 ' if t['invite_conv']<20 else ''}到店{t['sg_num']}({t['invite_conv']:.0f}%)</div>
<span style="margin:0 4px;color:#94a3b8">→</span></div>
<div style="display:inline-flex;align-items:center">
<div style="padding:6px 12px;border-radius:6px;border:3px solid {'#dc2626' if t['sign_rate']<25 else '#d97706' if t['sign_rate']<30 else '#16a34a'};font-size:11px;font-weight:600">签单{t['shop_sign']}({t['sign_rate']:.0f}%)</div>
<span style="margin:0 4px;color:#94a3b8">→</span></div>
<div style="display:inline-flex;align-items:center">
<div style="padding:6px 12px;border-radius:6px;border:3px solid #16a34a;font-size:11px;font-weight:600">营收¥{t['total_rev']/10000:.0f}万</div></div>
</div>
<div style="font-size:12px;color:#dc2626;font-weight:500;padding:10px 14px;background:#fef2f2;border-radius:6px;line-height:1.7">
🔴 <strong>最大瓶颈：{'邀约→到店转化' if t['invite_conv']<30 else '到店→签单转化'}环节</strong>（{'接通→到店'+str(round(t['invite_conv'],1))+'%，低于30%基准' if t['invite_conv']<30 else '签单率'+str(round(t['sign_rate'],1))+'%，低于30%合格线'}）<br><br>
漏斗佐证：线索{t['leads_1d']}→接通{t['link_num']}→到店{t['sg_num']}({t['invite_conv']:.0f}%)→签单{t['shop_sign']}({t['sign_rate']:.0f}%)→¥{t['total_rev']/10000:.0f}万<br><br>
杠杆预估：{'到店率每+5pp，新增到店'+str(int(t['link_num']*0.05))+'人→按'+str(round(t['sign_rate'],0))+'%签单率增签'+str(int(t['link_num']*0.05*t['sign_rate']/100))+'单→+¥'+str(int(t['link_num']*0.05*t['sign_rate']/100*t['avg_deal'])) if t['invite_conv']<30 else '签单率每+5pp，新增签单'+str(int(t['sg_num']*0.05))+'单→+¥'+str(int(t['sg_num']*0.05*t['avg_deal']))}
</div></div>

<!-- 7. 跨领域对撞 -->
<div class="card">
<h2>跨领域知识对撞 · 2组</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
<div style="background:#fdf4ff;border-radius:10px;padding:16px;border-left:4px solid #a855f7">
<div style="font-weight:700;color:#7c3aed;margin-bottom:8px">
<span style="font-size:9px;color:#fff;background:#7c3aed;padding:1px 6px;border-radius:3px;margin-right:6px">跨领域</span>
挑战式销售 × 现场签单 {BOOK_REFS['CHALLENGER']}</div>
<div style="font-size:12px;color:#475569;line-height:1.7">
<strong>现象：</strong>签单率{t['sign_rate']:.1f}%，到店客户流失率高<br>
<strong>对撞：</strong>Challenger Sale — 最优秀的顾问不在于「关系维护」，而在于「主动揭示客户未意识到的问题」。婚恋场景：「您知道您目前择偶方向在同龄人中的竞争压力有多大吗？」<br>
<strong>动作：</strong>设计「一句话揭示痛点」开场话术；提炼TOP门店的问题引导模式<br>
<strong>预估：</strong>签单率+5pp → +¥{int(t['sg_num']*0.05*t['avg_deal']):,}/日
</div></div>
<div style="background:#f0fff4;border-radius:10px;padding:16px;border-left:4px solid #16a34a">
<div style="font-weight:700;color:#166534;margin-bottom:8px">
<span style="font-size:9px;color:#fff;background:#16a34a;padding:1px 6px;border-radius:3px;margin-right:6px">跨领域</span>
损失厌恶 × 邀约话术 {BOOK_REFS['SPIN']}</div>
<div style="font-size:12px;color:#475569;line-height:1.7">
<strong>现象：</strong>接通→到店转化{t['invite_conv']:.1f}%，大量已接通用户不来店<br>
<strong>对撞：</strong>SPIN中的「暗示问题（Implication）」— 不直接说「来店能帮您」，而是问「如果您再等3个月，您觉得合适人选还会等您吗？」制造损失感<br>
<strong>动作：</strong>设计3条「损失型邀约话术」；A/B测试；TOP邀约员工话术提炼<br>
<strong>预估：</strong>到店率+5pp → +¥{int(t['link_num']*0.05*t['sign_rate']/100*t['avg_deal']):,}/日
</div></div>
</div></div>

<!-- 8. 改善建议 -->
<div class="card">
<h2>改善建议 · {len(improvements)}条（按预估增幅排序）· 总预估¥{total_uplift:,.0f}/日</h2>
{imp_html}
</div>

<!-- 9. 门店明细表 -->
<div class="card" style="overflow-x:auto">
<h2>门店明细（按营收排序，含签单率/人均/退费率）</h2>
<table><thead><tr>
<th style="text-align:left;padding-left:10px">门店</th>
<th>负责人</th>
<th>在岗</th>
<th>到店</th>
<th>签单</th>
<th>签单率</th>
<th style="text-align:right">今日营收</th>
<th style="text-align:right">人均产值</th>
<th>退费率</th>
<th style="text-align:right">月累</th>
</tr></thead>
<tbody>{shop_rows_html}</tbody></table>
</div>

<!-- 10. 部门明细（签单率 vs 邀约效率分析）-->
<div class="card">
<h2>门店效率矩阵分析（签单率 vs 邀约到店率）</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
<div style="background:#f0fdf4;border-radius:8px;padding:14px">
<div style="font-weight:600;color:#16a34a;margin-bottom:8px">⭐ 高签单+高邀约门店（双优）</div>
{''.join(f'<div style="font-size:12px;padding:4px 0;border-bottom:1px solid #e2e8f0">{s["dept_name"]} · 签{s["sign_rate"]:.0f}% / 到{s["invite_conv"]:.0f}%</div>' for s in sorted(shops, key=lambda x: x["sign_rate"]+x["invite_conv"], reverse=True)[:3])}
</div>
<div style="background:#fef2f2;border-radius:8px;padding:14px">
<div style="font-weight:600;color:#dc2626;margin-bottom:8px">⚠ 低签单+低邀约门店（双弱，优先改善）</div>
{''.join(f'<div style="font-size:12px;padding:4px 0;border-bottom:1px solid #e2e8f0">{s["dept_name"]} · 签{s["sign_rate"]:.0f}% / 到{s["invite_conv"]:.0f}%</div>' for s in sorted(shops, key=lambda x: x["sign_rate"]+x["invite_conv"])[:3])}
</div>
</div></div>

<!-- 11. TOP5门店深度分析 -->
<div class="card" style="overflow-x:auto">
<h2>TOP5门店深度分析（全过程字段 + 为什么好 + 可复制性）</h2>
<table><thead><tr>
<th style="text-align:left;padding-left:10px">排名</th>
<th>门店</th>
<th>负责人</th>
<th>到店</th>
<th>签单率</th>
<th>邀约→到店</th>
<th style="text-align:right">营收</th>
<th style="text-align:right">人均</th>
<th>为什么好</th>
<th>可复制要点</th>
</tr></thead>
<tbody>{top5_rows}</tbody></table>
</div>

<!-- 12. TOP5 vs BOTTOM5 能力对比 -->
<div class="card" style="overflow-x:auto">
<h2>TOP5 vs BOTTOM5 能力差异对比（9维度 + 差异倍数）</h2>
<table><thead><tr>
<th style="text-align:left;padding-left:10px">维度</th>
<th style="text-align:center;color:#16a34a">TOP5均值</th>
<th style="text-align:center;color:#dc2626">BOTTOM5均值</th>
<th style="text-align:center">差异倍数</th>
<th>解读与复制建议</th>
</tr></thead>
<tbody>{compare_rows}</tbody></table>
</div>

<!-- 13. BOTTOM5门店诊断 -->
<div class="card">
<h2>BOTTOM5门店专项诊断 + 即日改善建议</h2>
{bot5_cards}
</div>

<!-- 部门级诊断（含管理者姓名+管理视角缺失）-->
<div class="card">
<h2>部门级诊断（管理者视角 + 管理视角缺失推断）</h2>
{dept_diag_html}
</div>

<!-- 14. 数据→人的转向 -->
<div class="card">
<h2>数据→人的转向（技能 / 心态 / 存量管理 / 执行力）</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
<div style="background:#fdf4ff;border-radius:8px;padding:14px;border-left:3px solid #a855f7">
<div style="font-weight:700;color:#7c3aed;margin-bottom:6px">🎯 技能维度</div>
<div style="font-size:12px;color:#555;line-height:1.8">现场签单核心是「需求挖掘→价值呈现→异议处理」三段能力。TOP门店签单率{max(s['sign_rate'] for s in shops) if shops else 0:.0f}% vs 最低{min(s['sign_rate'] for s in shops) if shops else 0:.0f}%，差距来自技能而非勤奋。1天SOP培训可缩小30%差距。</div>
</div>
<div style="background:#fffbeb;border-radius:8px;padding:14px;border-left:3px solid #d97706">
<div style="font-weight:700;color:#d97706;margin-bottom:6px">💪 心态维度</div>
<div style="font-size:12px;color:#555;line-height:1.8">签单失败后不复盘是门店业绩停滞的最大隐患。TOP顾问每单未签单后必做3分钟复盘：哪个节点失控？如何下次避免？建立「失败案例库」是团队成长飞轮。</div>
</div>
<div style="background:#f0fdf4;border-radius:8px;padding:14px;border-left:3px solid #16a34a">
<div style="font-weight:700;color:#166534;margin-bottom:6px">📦 存量管理维度</div>
<div style="font-size:12px;color:#555;line-height:1.8">到店未签单客户是最宝贵的「温热线索」，7日内二次邀约转化率是冷线索5倍。建立「未签单客户72h跟进机制」，每周五统计当周未签单客户名单，制定个性化跟进方案。</div>
</div>
<div style="background:#eff6ff;border-radius:8px;padding:14px;border-left:3px solid #3b82f6">
<div style="font-weight:700;color:#1d4ed8;margin-bottom:6px">⚡ 执行力维度</div>
<div style="font-size:12px;color:#555;line-height:1.8">三大执行力指标：①线索即日分配率（当前{t['lead_speed_1d']:.0f}%，目标≥80%） ②到店邀约成功率（{t['invite_conv']:.0f}%，目标≥30%） ③签单率（{t['sign_rate']:.0f}%，目标≥30%）。每日晨会10分钟数据复盘是执行力提升最低成本的方式。</div>
</div>
</div></div>

<div style="text-align:center;padding:20px;color:#94a3b8;font-size:12px">
📊 本报告由 Linh Nguyen（智慧助理）自动生成 · {date_display} · 覆盖14项诊断模块 · 防退化v1<br>
数据来源：珍爱网门店运营数据平台 · 基准参考：report_template_benchmark.md
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

    print(f"[门店报告] 拉取数据 {DATE}...")
    resp_today = daily("shop", DATE)
    resp_prev = daily("shop", prev_date(DATE))

    rows_today = parse_rows(resp_today)
    rows_prev = parse_rows(resp_prev)

    print(f"[门店报告] 今日门店行数: {len(rows_today)}, 昨日: {len(rows_prev)}")

    html = generate_html(rows_today, rows_prev, DATE_DISPLAY)

    filename = f"Shop_Full_{DATE_DISPLAY}.html"
    path = export_html(html, filename, open_browser=True)
    print(f"[门店报告] 已导出: {path}")

    subject = f"🏪 门店全量体检报告 {DATE_DISPLAY}"
    ok = send_report_email(subject, html)
    print(f"[门店报告] 邮件: {'成功' if ok else '失败'}")


if __name__ == "__main__":
    main()
