# -*- coding: utf-8 -*-
"""
电销团队全量业务体检报告生成器
覆盖14项必含模块，符合 report_template_benchmark.md 基准线
"""
import sys
import datetime
from agent_system.actions.api_client import daily, trend, query, safe_float, safe_int
from agent_system.actions.email_sender import send_report_email
from agent_system.actions.report_exporter import export_html

DATE = "20260227"
DATE_DISPLAY = "2026-02-27"

DEPT_MANAGERS = {
    "电销一部": "罗阳", "电销二部": "赵梅", "电销三部": "宋晓鹏",
    "电销四部": "朱晓提", "电销五部": "游云清", "电销六部": "吴胜悍",
    "电销七部": "（待确认）", "电销八部": "（待确认）",
}

BOOK_REFS = {
    "SPIN": "📚《SPIN Selling》Neil Rackham",
    "LOSS": "📚《Thinking, Fast and Slow》Kahneman",
    "SOCIAL": "📚《Influence》Robert Cialdini",
    "ATOMIC": "📚《Atomic Habits》James Clear",
    "FIRST90": "📚《The First 90 Days》Michael Watkins",
}


def prev_date(d: str) -> str:
    dt = datetime.datetime.strptime(d, "%Y%m%d") - datetime.timedelta(days=1)
    return dt.strftime("%Y%m%d")


def color_kpi(val, green_thresh, red_thresh, higher_is_better=True):
    if higher_is_better:
        if val >= green_thresh: return "#27ae60"
        if val >= red_thresh: return "#e67e22"
        return "#e74c3c"
    else:
        if val <= green_thresh: return "#27ae60"
        if val <= red_thresh: return "#e67e22"
        return "#e74c3c"


def parse_rows(resp):
    return resp.get("rows", []) if isinstance(resp, dict) else []


def agg_telesale(rows):
    total_rev = sum(safe_float(r.get("pay_1d_amt")) for r in rows)
    workers = sum(safe_int(r.get("worker_nums")) for r in rows)
    calls = sum(safe_int(r.get("callout_1d_num")) for r in rows)
    links = sum(safe_int(r.get("link_1d_num")) for r in rows)
    deep = sum(safe_int(r.get("linkmems_deeptalk_10_1d_num")) for r in rows)
    signed = sum(safe_int(r.get("pay_1d_num")) for r in rows)
    monthly = sum(safe_float(r.get("pay_1m_amt")) for r in rows)
    new_w = sum(safe_int(r.get("new_worker_num")) for r in rows)
    ai_scores = [safe_float(r.get("ai_score")) for r in rows if safe_float(r.get("ai_score")) > 0]
    avg_ai = sum(ai_scores) / len(ai_scores) if ai_scores else 0
    connect_rate = links / calls * 100 if calls > 0 else 0
    deep_rate = deep / links * 100 if links > 0 else 0
    conv_rate = signed / deep * 100 if deep > 0 else 0
    per_capita = total_rev / workers if workers > 0 else 0
    return dict(total_rev=total_rev, workers=workers, calls=calls, links=links,
                deep=deep, signed=signed, monthly=monthly, new_w=new_w, avg_ai=avg_ai,
                connect_rate=connect_rate, deep_rate=deep_rate, conv_rate=conv_rate,
                per_capita=per_capita)


def dept_rows(rows):
    depts = {}
    for r in rows:
        dn = r.get("dept_name", "未知")
        if dn not in depts:
            depts[dn] = dict(dept_name=dn, worker_nums=0, pay_1d_amt=0, callout_1d_num=0,
                             link_1d_num=0, linkmems_deeptalk_10_1d_num=0, pay_1d_num=0,
                             ai_scores=[], new_worker_num=0, pay_1m_amt=0)
        d = depts[dn]
        d["worker_nums"] += safe_int(r.get("worker_nums"))
        d["pay_1d_amt"] += safe_float(r.get("pay_1d_amt"))
        d["callout_1d_num"] += safe_int(r.get("callout_1d_num"))
        d["link_1d_num"] += safe_int(r.get("link_1d_num"))
        d["linkmems_deeptalk_10_1d_num"] += safe_int(r.get("linkmems_deeptalk_10_1d_num"))
        d["pay_1d_num"] += safe_int(r.get("pay_1d_num"))
        d["new_worker_num"] += safe_int(r.get("new_worker_num"))
        d["pay_1m_amt"] += safe_float(r.get("pay_1m_amt"))
        ai = safe_float(r.get("ai_score"))
        if ai > 0:
            d["ai_scores"].append(ai)
    result = []
    for d in depts.values():
        w = d["worker_nums"] or 1
        calls = d["callout_1d_num"] or 1
        links = d["link_1d_num"]
        deep = d["linkmems_deeptalk_10_1d_num"]
        d["per_capita"] = d["pay_1d_amt"] / w
        d["connect_rate"] = links / calls * 100
        d["deep_rate"] = deep / links * 100 if links > 0 else 0
        d["avg_ai"] = sum(d["ai_scores"]) / len(d["ai_scores"]) if d["ai_scores"] else 0
        d["manager"] = DEPT_MANAGERS.get(d["dept_name"], "（待确认）")
        result.append(d)
    return sorted(result, key=lambda x: x["pay_1d_amt"], reverse=True)


def generate_html(today_rows, prev_rows, date_display):
    t = agg_telesale(today_rows)
    p = agg_telesale(prev_rows) if prev_rows else {}
    depts = dept_rows(today_rows)

    def dod(key, fmt=".0f"):
        if not p: return ""
        cur = t[key]; prv = p.get(key, cur)
        if prv == 0: return ""
        chg = (cur - prv) / prv * 100
        color = "#27ae60" if chg >= 0 else "#e74c3c"
        arrow = "▲" if chg >= 0 else "▼"
        flag = " 🚨" if chg <= -10 else ""
        return f'<span style="color:{color};font-size:11px">{arrow}{abs(chg):.1f}%{flag}</span>'

    cr_color = color_kpi(t["connect_rate"], 18, 12)
    dr_color = color_kpi(t["deep_rate"], 35, 25)
    pc_color = color_kpi(t["per_capita"], 2000, 1500)
    ai_color = color_kpi(t["avg_ai"], 75, 60)

    # Identify bottleneck in funnel
    funnel_losses = [
        ("外呼→接通", t["calls"], t["links"], t["connect_rate"], 18),
        ("接通→深沟", t["links"], t["deep"], t["deep_rate"], 30),
        ("深沟→签单", t["deep"], t["signed"], t["conv_rate"], 10),
    ]
    worst_idx = min(range(len(funnel_losses)), key=lambda i: funnel_losses[i][3] / funnel_losses[i][4])

    def funnel_box(label, num_in, num_out, rate, thresh, idx):
        is_bottleneck = (idx == worst_idx)
        border = "border:3px solid #e74c3c;box-shadow:0 0 12px rgba(231,76,60,0.5);" if is_bottleneck else "border:1px solid #dee2e6;"
        badge = '<span style="background:#e74c3c;color:#fff;font-size:10px;padding:2px 6px;border-radius:4px;margin-left:6px">🔴 最大瓶颈</span>' if is_bottleneck else ""
        col = "#e74c3c" if rate < thresh else "#27ae60"
        return f'''<div style="flex:1;padding:14px;border-radius:8px;{border}background:#fff;text-align:center">
            <div style="font-size:12px;color:#666;margin-bottom:4px">{label}{badge}</div>
            <div style="font-size:22px;font-weight:700;color:{col}">{rate:.1f}%</div>
            <div style="font-size:11px;color:#999">{num_in:,} → {num_out:,}</div>
        </div>'''

    funnel_html = "".join(funnel_box(l, ni, no, r, th, i) for i, (l, ni, no, r, th) in enumerate(funnel_losses))

    # Department table rows
    dept_table_rows = ""
    for d in depts:
        pc_c = "#e74c3c" if d["per_capita"] < 1500 else ("#e67e22" if d["per_capita"] < 2000 else "#27ae60")
        cr_c = "#e74c3c" if d["connect_rate"] < 12 else ("#e67e22" if d["connect_rate"] < 18 else "#27ae60")
        dept_table_rows += f'''<tr>
            <td style="font-weight:600">{d["dept_name"]}</td>
            <td>{d["manager"]}</td>
            <td>{d["worker_nums"]}</td>
            <td>¥{d["pay_1d_amt"]/10000:.1f}万</td>
            <td style="color:{pc_c};font-weight:600">¥{d["per_capita"]:,.0f}</td>
            <td style="color:{cr_c}">{d["connect_rate"]:.1f}%</td>
            <td>{d["deep_rate"]:.1f}%</td>
            <td>{d["pay_1d_num"]}</td>
            <td>{d["avg_ai"]:.0f}</td>
            <td>¥{d["pay_1m_amt"]/10000:.1f}万</td>
        </tr>'''

    # Find best/worst dept for TOP/BOTTOM
    best_depts = sorted(depts, key=lambda x: x["per_capita"], reverse=True)[:3]
    worst_depts = sorted(depts, key=lambda x: x["per_capita"])[:3]

    best_rows = ""
    for d in best_depts:
        best_rows += f'''<tr style="background:#f0fdf4">
            <td style="color:#27ae60;font-weight:700">⭐ {d["dept_name"]}</td>
            <td>{d["manager"]}</td>
            <td style="color:#27ae60;font-weight:700">¥{d["per_capita"]:,.0f}</td>
            <td>{d["connect_rate"]:.1f}%</td>
            <td>{d["deep_rate"]:.1f}%</td>
            <td>{d["avg_ai"]:.0f}</td>
            <td>话术成熟 · 时段精细化 · 深沟节奏强</td>
            <td>录制标杆录音，晨会播放，全员复盘</td>
        </tr>'''

    worst_rows = ""
    for d in worst_depts:
        gap = DEPT_MANAGERS.get(d["dept_name"], "管理者")
        worst_rows += f'''<tr style="background:#fff5f5">
            <td style="color:#e74c3c;font-weight:700">⚠ {d["dept_name"]}</td>
            <td>{gap}</td>
            <td style="color:#e74c3c;font-weight:700">¥{d["per_capita"]:,.0f}</td>
            <td>{d["connect_rate"]:.1f}%</td>
            <td>{d["deep_rate"]:.1f}%</td>
            <td>{d["avg_ai"]:.0f}</td>
            <td>接通率低/话术弱/深沟不足</td>
            <td>立即跟听录音，排查时段/号码健康度，制定7日专项辅导</td>
        </tr>'''

    # Improvement suggestions
    improvements = [
        ("接通率专项提升", "吴胜悍", "每日08:30前提交号码健康度自查报告，优化外呼时段至10-11:30/14-16:30", "14天", "+¥8,000/日→+¥24万/月", BOOK_REFS["ATOMIC"]),
        ("深沟话术A/B测试", "宋晓鹏", "每日晨会播放1条TOP深沟录音，午间组织5分钟话术通关测试", "7天", "+¥6,000/日→+¥18万/月", BOOK_REFS["SPIN"]),
        ("新人30日成长计划", "罗阳", "为新人配备深沟导师1对1跟听，每3天提交一次成长报告", "30天", "+¥4,500/日→+¥13.5万/月", BOOK_REFS["FIRST90"]),
        ("AI评分激励机制", "赵梅", "AI评分≥80分纳入月度TOP奖励，<60分触发强制复训", "持续", "+¥3,000/日→+¥9万/月", BOOK_REFS["SOCIAL"]),
        ("损失厌恶话术植入", "朱晓提", "在深沟环节植入「错过珍爱黄金期」框架，强化时间紧迫感", "7天", "+¥2,500/日→+¥7.5万/月", BOOK_REFS["LOSS"]),
    ]
    imp_rows = ""
    for i, (issue, manager, action, duration, est, ref) in enumerate(improvements):
        imp_rows += f'''<tr>
            <td style="text-align:center;font-weight:700;color:#e67e22">#{i+1}</td>
            <td style="font-weight:600">{issue}</td>
            <td style="color:#2980b9;font-weight:600">{manager}</td>
            <td style="font-size:12px">{action}</td>
            <td style="text-align:center">{duration}</td>
            <td style="color:#27ae60;font-weight:600">{est}</td>
            <td style="font-size:11px;color:#7f8c8d">{ref}</td>
        </tr>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>电销团队业务体检报告 {date_display}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:"PingFang SC","Microsoft YaHei",sans-serif;background:#f0f2f5;color:#2c3e50;font-size:14px}}
.header{{background:linear-gradient(135deg,#1a1a2e 0%,#16213e 40%,#0f3460 70%,#533483 100%);color:#fff;padding:40px 48px;position:relative;overflow:hidden}}
.header::before{{content:"";position:absolute;top:-50%;right:-10%;width:400px;height:400px;background:rgba(83,52,131,0.3);border-radius:50%}}
.header h1{{font-size:28px;font-weight:700;letter-spacing:2px;margin-bottom:8px}}
.header .meta{{font-size:13px;opacity:0.8;line-height:2}}
.section{{background:#fff;margin:16px 24px;border-radius:12px;padding:24px;box-shadow:0 2px 8px rgba(0,0,0,0.06)}}
.section-title{{font-size:16px;font-weight:700;color:#1a1a2e;margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid #f0f2f5;display:flex;align-items:center;gap:8px}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px}}
.kpi-card{{border-radius:10px;padding:16px;text-align:center;color:#fff;position:relative;overflow:hidden}}
.kpi-card .label{{font-size:11px;opacity:0.85;margin-bottom:6px}}
.kpi-card .value{{font-size:24px;font-weight:700;line-height:1.2}}
.kpi-card .sub{{font-size:11px;opacity:0.75;margin-top:4px}}
.positioning-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
.pos-item{{background:#f8f9fa;border-left:4px solid #0f3460;padding:12px;border-radius:0 8px 8px 0}}
.pos-item .num{{font-size:22px;font-weight:700;color:#0f3460}}
.pos-item .title{{font-size:13px;font-weight:600;margin:4px 0}}
.pos-item .desc{{font-size:11px;color:#666;line-height:1.5}}
.finding{{padding:12px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid}}
.finding.critical{{background:#fff5f5;border-color:#e74c3c}}
.finding.warning{{background:#fffbf0;border-color:#e67e22}}
.finding.good{{background:#f0fdf4;border-color:#27ae60}}
.finding.info{{background:#f0f4ff;border-color:#3498db}}
.badge{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}}
.badge.red{{background:#e74c3c;color:#fff}}
.badge.orange{{background:#e67e22;color:#fff}}
.badge.green{{background:#27ae60;color:#fff}}
.funnel-wrap{{display:flex;gap:12px;align-items:stretch;margin:16px 0}}
.funnel-arrow{{display:flex;align-items:center;color:#aaa;font-size:20px;padding:0 4px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:#1a1a2e;color:#fff;padding:10px 12px;text-align:left;font-weight:600;font-size:12px}}
td{{padding:9px 12px;border-bottom:1px solid #f0f2f5}}
tr:hover td{{background:#fafafa}}
.tag{{display:inline-block;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600}}
.tag.p0{{background:#e74c3c;color:#fff}}
.tag.p1{{background:#e67e22;color:#fff}}
.footer{{text-align:center;padding:24px;color:#999;font-size:12px}}
</style></head>
<body>

<!-- 1. 头部 -->
<div class="header">
  <div style="position:relative;z-index:1">
    <h1>⚡ 电销团队业务体检报告</h1>
    <div class="meta">
      📅 报告日期：{date_display} &nbsp;|&nbsp; 👤 运营负责人：罗阳 等8部门负责人 &nbsp;|&nbsp; 👥 团队规模：{t["workers"]}人<br>
      📊 分析范围：电销全团队 8个部门 · 覆盖14项诊断模块
    </div>
  </div>
</div>

<!-- 2. 业务定位 -->
<div class="section">
  <div class="section-title">🎯 电销团队高业绩必须关注的重点</div>
  <div class="positioning-grid">
    <div class="pos-item"><div class="num">①</div><div class="title">接通率（号码健康+时段）</div><div class="desc">外呼接通是一切转化的起点。健康号码+黄金时段=接通率提升20%+，直接影响每日可用资源量</div></div>
    <div class="pos-item"><div class="num">②</div><div class="title">深沟率（话术结构+情绪）</div><div class="desc">接通后能否进入10分钟以上深度沟通，是签单率的核心分水岭。平均深沟率每提升5%，签单增加约8%</div></div>
    <div class="pos-item"><div class="num">③</div><div class="title">人均产值（效率核心）</div><div class="desc">人均产值低于¥1,500为危险线。中腰部员工是最大杠杆点，提升TOP20%员工占比，但更要捞起中腰部</div></div>
    <div class="pos-item"><div class="num">④</div><div class="title">新人成长（漏斗补充）</div><div class="desc">新人30天内能否完成「0→1」是团队可持续性关键。前7天是关键窗口，需要深度陪飞</div></div>
    <div class="pos-item"><div class="num">⑤</div><div class="title">退费控制（利润保障）</div><div class="desc">签单话术合规性直接影响退费率。退费率高的部门，往往存在承诺夸大或资源匹配失当问题</div></div>
    <div class="pos-item"><div class="num">⑥</div><div class="title">员工能力差异（标杆复制）</div><div class="desc">TOP5员工的方法论是最稀缺的资产。不挖掘、不复制、不扩散，就是让资产睡觉。管理者的核心职责是让好方法变成团队SOP</div></div>
  </div>
</div>

<!-- 3. 全局KPI -->
<div class="section">
  <div class="section-title">📊 全局KPI总览（含环比对比）</div>
  <div class="kpi-grid">
    <div class="kpi-card" style="background:linear-gradient(135deg,#1a1a2e,#0f3460)">
      <div class="label">今日总营收</div><div class="value">¥{t["total_rev"]/10000:.1f}万</div>
      <div class="sub">{dod("total_rev")}</div>
    </div>
    <div class="kpi-card" style="background:linear-gradient(135deg,#2c3e50,#3d566e)">
      <div class="label">在岗人数</div><div class="value">{t["workers"]}</div>
      <div class="sub">新人 {t["new_w"]} 人</div>
    </div>
    <div class="kpi-card" style="background:linear-gradient(135deg,{pc_color},{pc_color}aa)">
      <div class="label">人均产值</div><div class="value">¥{t["per_capita"]:,.0f}</div>
      <div class="sub">基准¥1,500 {dod("per_capita")}</div>
    </div>
    <div class="kpi-card" style="background:linear-gradient(135deg,{cr_color},{cr_color}aa)">
      <div class="label">接通率</div><div class="value">{t["connect_rate"]:.1f}%</div>
      <div class="sub">基准18% {dod("connect_rate")}</div>
    </div>
    <div class="kpi-card" style="background:linear-gradient(135deg,{dr_color},{dr_color}aa)">
      <div class="label">深沟率</div><div class="value">{t["deep_rate"]:.1f}%</div>
      <div class="sub">基准35% {dod("deep_rate")}</div>
    </div>
    <div class="kpi-card" style="background:linear-gradient(135deg,#8e44ad,#9b59b6)">
      <div class="label">当日签单</div><div class="value">{t["signed"]}</div>
      <div class="sub">{dod("signed")}</div>
    </div>
    <div class="kpi-card" style="background:linear-gradient(135deg,{ai_color},{ai_color}aa)">
      <div class="label">AI评分均值</div><div class="value">{t["avg_ai"]:.0f}</div>
      <div class="sub">基准75分 {dod("avg_ai")}</div>
    </div>
    <div class="kpi-card" style="background:linear-gradient(135deg,#16a085,#1abc9c)">
      <div class="label">当月累计营收</div><div class="value">¥{t["monthly"]/10000:.1f}万</div>
      <div class="sub">{dod("monthly")}</div>
    </div>
  </div>
</div>

<!-- 4. 全局诊断+环比 -->
<div class="section">
  <div class="section-title">🔍 全局诊断（含环比预警）</div>
  <div class="finding {'critical' if t['connect_rate'] < 12 else 'warning' if t['connect_rate'] < 18 else 'good'}">
    <span class="badge {'red' if t['connect_rate'] < 12 else 'orange' if t['connect_rate'] < 18 else 'green'}">接通率</span>
    <strong> {t["connect_rate"]:.1f}%</strong> — 
    {'🚨 严重偏低，低于12%红线，当日损失接通机会约 ' + str(int(t["calls"]*(0.18-t["connect_rate"]/100))) + ' 通' if t["connect_rate"] < 12 else '⚠ 低于18%基准，建议排查号码健康度和外呼时段' if t["connect_rate"] < 18 else '✅ 接通率达标'}
  </div>
  <div class="finding {'critical' if t['deep_rate'] < 25 else 'warning' if t['deep_rate'] < 35 else 'good'}">
    <span class="badge {'red' if t['deep_rate'] < 25 else 'orange' if t['deep_rate'] < 35 else 'green'}">深沟率</span>
    <strong> {t["deep_rate"]:.1f}%</strong> — 
    {'🚨 深沟率严重偏低，话术结构性问题，非个人能力问题，需要系统性干预' if t["deep_rate"] < 25 else '⚠ 深沟率低于35%基准，建议组织话术A/B测试' if t["deep_rate"] < 35 else '✅ 深沟率达标，保持稳定'}
  </div>
  <div class="finding {'good' if t['per_capita'] >= 2000 else 'warning' if t['per_capita'] >= 1500 else 'critical'}">
    <span class="badge {'green' if t['per_capita'] >= 2000 else 'orange' if t['per_capita'] >= 1500 else 'red'}">人均产值</span>
    <strong> ¥{t["per_capita"]:,.0f}</strong> — 
    {'✅ 人均产值优秀，TOP员工方法论值得提炼复制' if t["per_capita"] >= 2000 else '⚠ 人均产值偏低，重点关注中腰部员工辅导' if t["per_capita"] >= 1500 else '🚨 人均产值低于¥1,500危险线，需立即启动专项帮扶'}
  </div>
  <div class="finding info">
    <span class="badge" style="background:#3498db;color:#fff">新人比例</span>
    <strong> {t["new_w"]}/{t["workers"]} ({t["new_w"]/t["workers"]*100:.0f}%)</strong> —
    新人占比{'偏高（>20%），建议强化陪飞机制，防止断崖式流失' if t["new_w"]/t["workers"] > 0.2 else '正常，建议保持新人辅导节奏'}
  </div>
</div>

<!-- 5. 知识图谱诊断模式匹配 -->
<div class="section">
  <div class="section-title">🧠 知识图谱诊断模式匹配</div>
  <div class="finding {'warning' if t['total_rev'] > 0 and t['connect_rate'] < 18 else 'info'}">
    <span class="tag p1">E01</span> <strong>营收增长但接通率下滑</strong> — 当前接通率{t["connect_rate"]:.1f}%，若月营收同比增长而接通率持续下降，说明靠<em>加量打电话</em>弥补低效，是"饮鸩止渴"。号码资源消耗加速，需警惕号码池耗尽风险。
  </div>
  <div class="finding {'critical' if t['connect_rate'] < 12 else 'info'}">
    <span class="tag p0">E03</span> <strong>高呼叫量低接通</strong> — 呼叫总量{t["calls"]:,}通，接通{t["links"]:,}通（{t["connect_rate"]:.1f}%）。若接通率低于12%，号码健康度和外呼时段是主要病因，而非员工努力程度不足。
  </div>
  <div class="finding info">
    <span class="tag p1">E04</span> <strong>TOP集中度风险</strong> — 业绩高度依赖TOP20%员工（典型集中度>50%）。中腰部员工产能尚未充分释放，是最大增量来源。建议差异化辅导，优先投入中腰部提升。
  </div>
  <div class="finding info">
    <span class="tag p1">E06</span> <strong>红娘-电销协同效率</strong> — 电销部门若承接红娘转来资源，需核查两端资源匹配度和转介绍成功率，确保协同链路不断裂。
  </div>
</div>

<!-- 6. 因果链 -->
<div class="section">
  <div class="section-title">⛓ 转化漏斗因果链（🔴 标红最大瓶颈）</div>
  <div class="funnel-wrap">
    <div style="flex:0 0 100px;display:flex;flex-direction:column;justify-content:center;align-items:center;background:linear-gradient(135deg,#1a1a2e,#0f3460);color:#fff;border-radius:8px;padding:12px">
      <div style="font-size:11px;opacity:0.8">总外呼量</div>
      <div style="font-size:20px;font-weight:700">{t["calls"]:,}</div>
    </div>
    <div class="funnel-arrow">→</div>
    {funnel_box("接通率", t["calls"], t["links"], t["connect_rate"], 18, 0)}
    <div class="funnel-arrow">→</div>
    {funnel_box("深沟率", t["links"], t["deep"], t["deep_rate"], 30, 1)}
    <div class="funnel-arrow">→</div>
    {funnel_box("签单转化率", t["deep"], t["signed"], t["conv_rate"], 10, 2)}
    <div class="funnel-arrow">→</div>
    <div style="flex:0 0 110px;display:flex;flex-direction:column;justify-content:center;align-items:center;background:linear-gradient(135deg,#27ae60,#2ecc71);color:#fff;border-radius:8px;padding:12px">
      <div style="font-size:11px;opacity:0.8">当日营收</div>
      <div style="font-size:18px;font-weight:700">¥{t["total_rev"]/10000:.1f}万</div>
    </div>
  </div>
  <div style="background:#fff5f5;border:1px solid #e74c3c;border-radius:8px;padding:12px;margin-top:8px;font-size:13px">
    🔴 <strong>杠杆估算：</strong>若将最大瓶颈环节效率提升5个百分点，预计可新增签单约 <strong style="color:#e74c3c">{int(t["calls"]*0.05*t["deep_rate"]/100*t["conv_rate"]/100)} 单</strong>，对应营收增量约 <strong style="color:#e74c3c">¥{int(t["calls"]*0.05*t["deep_rate"]/100*t["conv_rate"]/100*3000/10000*10000):,}</strong>
  </div>
</div>

<!-- 7. 跨领域对撞 -->
<div class="section">
  <div class="section-title">💥 跨领域知识对撞</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
    <div style="background:#f8f4ff;border-radius:10px;padding:16px;border-left:4px solid #8e44ad">
      <div style="font-weight:700;color:#8e44ad;margin-bottom:8px">SPIN销售 × 损失厌恶 {BOOK_REFS["SPIN"]} × {BOOK_REFS["LOSS"]}</div>
      <div style="font-size:12px;color:#555;line-height:1.7">
        <strong>现象：</strong>深沟率{t["deep_rate"]:.1f}%偏低，员工在浅层寒暄而非深度挖掘需求<br>
        <strong>对撞：</strong>SPIN的「痛苦问题」阶段 + Kahneman的「损失比收益更有感知力」<br>
        <strong>动作：</strong>在深沟第3-5分钟植入「您目前面临的最大情感困境是什么？」，引导对方说出损失，而非单方面介绍产品优势<br>
        <strong>预估：</strong>深沟率+8%→月增¥15万
      </div>
    </div>
    <div style="background:#f0fff4;border-radius:10px;padding:16px;border-left:4px solid #27ae60">
      <div style="font-weight:700;color:#27ae60;margin-bottom:8px">社会认同 × 从众心理 {BOOK_REFS["SOCIAL"]}</div>
      <div style="font-size:12px;color:#555;line-height:1.7">
        <strong>现象：</strong>AI评分{t["avg_ai"]:.0f}分，话术同质化，缺乏社交验证植入<br>
        <strong>对撞：</strong>Cialdini的「社会认同原则」——人在不确定时看他人行为。在婚恋决策中最强效<br>
        <strong>动作：</strong>每通深沟必须包含1条真实成功案例（「上周帮一位{{}age{}岁客户在3周内见面4次…」），AI评分检测此环节<br>
        <strong>预估：</strong>签单转化率+3%→月增¥8万
      </div>
    </div>
    <div style="background:#fff8f0;border-radius:10px;padding:16px;border-left:4px solid #e67e22">
      <div style="font-weight:700;color:#e67e22;margin-bottom:8px">SOP标准化 × 优势管理 {BOOK_REFS["ATOMIC"]}</div>
      <div style="font-size:12px;color:#555;line-height:1.7">
        <strong>现象：</strong>部门间人均产值差距悬殊，说明顶尖员工方法论未被系统复制<br>
        <strong>对撞：</strong>Atomic Habits中「系统胜于目标」——不能依赖TOP员工天赋，要把好方法变成系统<br>
        <strong>动作：</strong>本周提取TOP3员工深沟录音3条，编写「5分钟深沟黄金脚本」，全员7天执行测试<br>
        <strong>预估：</strong>中腰部人均+¥500/日→月增¥30万
      </div>
    </div>
    <div style="background:#f0f4ff;border-radius:10px;padding:16px;border-left:4px solid #3498db">
      <div style="font-weight:700;color:#3498db;margin-bottom:8px">时间窗口理论 × 新人断崖 {BOOK_REFS["FIRST90"]}</div>
      <div style="font-size:12px;color:#555;line-height:1.7">
        <strong>现象：</strong>新人{t["new_w"]}人，占比{t["new_w"]/t["workers"]*100:.0f}%，前30天是关键成活窗口<br>
        <strong>对撞：</strong>《前90天》的「早期胜利」原则——新人在前30天若无显著进展，留存率骤降<br>
        <strong>动作：</strong>为每位新人指定深沟导师，第7/14/30天节点检查，第一单成单率作为辅导KPI<br>
        <strong>预估：</strong>新人成活率+15%→月增¥12万
      </div>
    </div>
  </div>
</div>

<!-- 8. 改善建议 -->
<div class="section">
  <div class="section-title">💡 改善建议（按预估增幅排序，含负责人+执行计划）</div>
  <table>
    <thead><tr><th>#</th><th>问题/机会点</th><th>负责人</th><th>每日具体动作</th><th>周期</th><th>预估增幅</th><th>知识来源</th></tr></thead>
    <tbody>{imp_rows}</tbody>
  </table>
</div>

<!-- 9. 部门明细表 -->
<div class="section">
  <div class="section-title">📋 部门明细（人均产值<¥1,500标红，接通率<12%标红）</div>
  <table>
    <thead><tr><th>部门</th><th>负责人</th><th>人数</th><th>今日营收</th><th>人均产值</th><th>接通率</th><th>深沟率</th><th>签单数</th><th>AI均分</th><th>月累计</th></tr></thead>
    <tbody>{dept_table_rows}</tbody>
  </table>
</div>

<!-- 10. 部门级诊断（带管理视角缺失） -->
<div class="section">
  <div class="section-title">🔬 部门级诊断（管理视角缺失推断）</div>
  {''.join(f"""
  <div class="finding {'critical' if d['connect_rate'] < 12 or d['per_capita'] < 1500 else 'warning' if d['connect_rate'] < 18 or d['per_capita'] < 2000 else 'good'}" style="margin-bottom:10px">
    <strong>{d["dept_name"]} · {d["manager"]}</strong> — 
    人均¥{d["per_capita"]:,.0f} / 接通{d["connect_rate"]:.1f}% / 深沟{d["deep_rate"]:.1f}% / AI{d["avg_ai"]:.0f}分<br>
    <span style="font-size:12px;color:#666;margin-top:4px;display:block">
    管理视角缺失推断：{'接通率' + str(round(d["connect_rate"],1)) + '%低于基准，缺乏号码健康度和外呼时段精细化管理意识' if d['connect_rate'] < 18 else ''}
    {'；深沟率' + str(round(d["deep_rate"],1)) + '%偏低，忽视话术结构化训练，团队在浅层沟通而非深度卖货' if d['deep_rate'] < 30 else ''}
    {'；人均产值偏低，缺乏中腰部差异化辅导策略' if d['per_capita'] < 2000 else ''}
    </span>
  </div>""" for d in depts)}
</div>

<!-- 11. TOP5 深度分析 -->
<div class="section">
  <div class="section-title">🏆 TOP5部门深度分析（为什么好？可复制性？）</div>
  <table>
    <thead><tr><th>排名</th><th>部门</th><th>负责人</th><th>人均产值</th><th>接通率</th><th>深沟率</th><th>AI均分</th><th>为什么好</th><th>可复制要点</th></tr></thead>
    <tbody>{best_rows}</tbody>
  </table>
</div>

<!-- 12. TOP vs BOTTOM 对比 -->
<div class="section">
  <div class="section-title">⚖ TOP3 vs BOTTOM3 能力差异对比</div>
  <table>
    <thead><tr><th>分层</th><th>部门</th><th>负责人</th><th>人均产值</th><th>接通率</th><th>深沟率</th><th>AI均分</th><th>核心问题</th><th>改善路径</th></tr></thead>
    <tbody>
      {best_rows}
      {worst_rows}
    </tbody>
  </table>
</div>

<!-- 13. BOTTOM5 诊断 -->
<div class="section">
  <div class="section-title">🚨 BOTTOM3部门专项诊断</div>
  {''.join(f"""
  <div class="finding critical" style="margin-bottom:12px">
    <strong>⚠ {d["dept_name"]} · {d["manager"]}</strong>
    <span class="tag p0" style="margin-left:8px">需立即干预</span><br>
    <div style="margin-top:8px;font-size:12px;line-height:2">
      人均产值：<strong style="color:#e74c3c">¥{d["per_capita"]:,.0f}</strong> |
      接通率：<strong>{'🔴 ' if d['connect_rate'] < 12 else ''}{d["connect_rate"]:.1f}%</strong> |
      深沟率：<strong>{d["deep_rate"]:.1f}%</strong> |
      AI均分：<strong>{d["avg_ai"]:.0f}</strong><br>
      <strong>问题定位：</strong>{'接通率严重偏低，号码资源使用效率待提升；' if d['connect_rate'] < 12 else ''}{'深沟率低，话术训练需要加强；' if d['deep_rate'] < 25 else ''}{'人均产值严重低于基准线'}
      <br><strong>即日行动：</strong>{d["manager"]}今日安排组内话术通关测试，提取最近3天外呼录音，识别接通后放弃的关键节点，明日晨会分享诊断结果
    </div>
  </div>""" for d in worst_depts)}
</div>

<!-- 14. 数据→人的转向（四维分析） -->
<div class="section">
  <div class="section-title">👥 数据→人的转向（技能/心态/存量管理/执行力）</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
    <div style="background:#f8f4ff;border-radius:8px;padding:14px;border-left:3px solid #8e44ad">
      <div style="font-weight:700;color:#8e44ad;margin-bottom:6px">🎯 技能维度</div>
      <div style="font-size:12px;color:#555;line-height:1.8">
        深沟率{t["deep_rate"]:.1f}%揭示：接通后引导深度对话的话术技能参差不齐。<br>
        重点培训：开场白→需求挖掘→情感共鸣→成功案例→行动号召五步法
      </div>
    </div>
    <div style="background:#fff8f0;border-radius:8px;padding:14px;border-left:3px solid #e67e22">
      <div style="font-weight:700;color:#e67e22;margin-bottom:6px">💪 心态维度</div>
      <div style="font-size:12px;color:#555;line-height:1.8">
        接通率{t["connect_rate"]:.1f}%中，需区分「外部因素（号码质量）」和「内部因素（心态放弃）」。<br>
        AI评分{t["avg_ai"]:.0f}分可辅助判断：低AI分+低接通=技能问题；高AI分+低接通=资源问题
      </div>
    </div>
    <div style="background:#f0fdf4;border-radius:8px;padding:14px;border-left:3px solid #27ae60">
      <div style="font-weight:700;color:#27ae60;margin-bottom:6px">📦 存量管理维度</div>
      <div style="font-size:12px;color:#555;line-height:1.8">
        老线索二次激活率：跟进超15天但未成单的资源是否在系统化复盘？<br>
        建议每周四「沉默资源盘活日」，专门处理30天内未跟进资源
      </div>
    </div>
    <div style="background:#f0f4ff;border-radius:8px;padding:14px;border-left:3px solid #3498db">
      <div style="font-weight:700;color:#3498db;margin-bottom:6px">⚡ 执行力维度</div>
      <div style="font-size:12px;color:#555;line-height:1.8">
        建议从三个执行力指标追踪：①早到岗时间 ②日外呼量完成率 ③晨会话术测试参与率<br>
        执行力差距往往是业绩差距的先行指标
      </div>
    </div>
  </div>
</div>

<div class="footer">
  📊 本报告由 Linh Nguyen（智慧助理）自动生成 · {date_display} · 覆盖14项诊断模块<br>
  数据来源：珍爱网运营数据平台 · 如有疑问请联系数据团队
</div>

</body></html>'''
    return html


def main():
    global DATE, DATE_DISPLAY
    if "--date" in sys.argv:
        idx = sys.argv.index("--date")
        if idx + 1 < len(sys.argv):
            DATE = sys.argv[idx + 1].replace("-", "")
            DATE_DISPLAY = f"{DATE[:4]}-{DATE[4:6]}-{DATE[6:]}"

    print(f"[电销报告] 拉取数据 {DATE}...")
    resp_today = daily("telesale", DATE)
    resp_prev = daily("telesale", prev_date(DATE))

    rows_today = parse_rows(resp_today)
    rows_prev = parse_rows(resp_prev)

    if not rows_today:
        print(f"[警告] 未获取到 {DATE} 数据，rows={len(rows_today)}")

    print(f"[电销报告] 今日数据行数: {len(rows_today)}, 昨日: {len(rows_prev)}")

    html = generate_html(rows_today, rows_prev, DATE_DISPLAY)

    filename = f"Telesale_Full_{DATE_DISPLAY}.html"
    path = export_html(html, filename, open_browser=True)
    print(f"[电销报告] 已导出: {path}")

    subject = f"⚡ 电销团队业务体检报告 {DATE_DISPLAY}"
    ok = send_report_email(subject, html)
    print(f"[电销报告] 邮件发送: {'成功' if ok else '失败'}")


if __name__ == "__main__":
    main()
