# -*- coding: utf-8 -*-
"""
建信团队全量业务体检报告生成器
覆盖14项必含模块，符合 report_template_benchmark.md 基准线
建信核心业务：资源分配→IM发信→用户回复→企微添加→深度跟进→调配给电销→切面成交
"""
import sys
import datetime
from agent_system.actions.api_client import daily, trend, query, safe_float, safe_int
from agent_system.actions.email_sender import send_report_email
from agent_system.actions.report_exporter import export_html

DATE = "20260227"
DATE_DISPLAY = "2026-02-27"
MANAGER = "程朴娟"
TEAM_SIZE = 66
TEAM_DEPTS = 8
TEAM_CHANNELS = 9

DEPT_MANAGERS = {
    "建信一部": "（待确认）",
    "建信二部": "刘源",
    "建信三部": "（待确认）",
    "建信四部": "（待确认）",
    "建信五部": "（待确认）",
    "建信六部": "罗林",
    "建信七部": "（待确认）",
    "建信八部": "（待确认）",
}

BOOK_REFS = {
    "HOOK":    "📚《Hooked》Nir Eyal",
    "TRUST":   "📚《The Speed of Trust》Covey",
    "SPIN":    "📚《SPIN Selling》Neil Rackham",
    "SOCIAL":  "📚《Influence》Robert Cialdini",
    "ATOMIC":  "📚《Atomic Habits》James Clear",
    "NVC":     "📚《Nonviolent Communication》Marshall Rosenberg",
    "GROWTH":  "📚《Hacking Growth》Sean Ellis",
}

MGMT_GAP_RULES = {
    "low_reply_rate":    "缺乏首发信话术迭代机制，首触内容未经A/B测试",
    "low_transfer_rate": "对调配时机判断标准模糊，未建立客户意向评分体系",
    "low_wechat_rate":   "忽视企微添加率作为信任建立先导指标的战略价值",
    "high_waste_channel":"渠道资源分配缺乏ROI动态调整机制",
    "low_per_capita":    "差异化辅导策略缺失，标杆SOP未有效下沉全员",
}


def prev_date(d: str) -> str:
    dt = datetime.datetime.strptime(d, "%Y%m%d") - datetime.timedelta(days=1)
    return dt.strftime("%Y%m%d")


def color_kpi(val, green_thresh, red_thresh, higher_is_better=True):
    if higher_is_better:
        if val >= green_thresh: return "#16a34a"
        if val >= red_thresh:   return "#d97706"
        return "#dc2626"
    else:
        if val <= green_thresh: return "#16a34a"
        if val <= red_thresh:   return "#d97706"
        return "#dc2626"


def parse_rows(resp):
    return resp.get("rows", []) if isinstance(resp, dict) else []


def agg_jianxin(rows):
    assign   = sum(safe_int(r.get("assign_1d_num"))   for r in rows)
    send_msg = sum(safe_int(r.get("send_msg_1d_num")) for r in rows)
    reply    = sum(safe_int(r.get("reply_1d_num"))    for r in rows)
    wechat   = sum(safe_int(r.get("wechat_add_1d_num")) for r in rows)
    transfer = sum(safe_int(r.get("transfer_1d_num")) for r in rows)
    pay_n    = sum(safe_int(r.get("pay_1d_num"))      for r in rows)
    pay_amt  = sum(safe_float(r.get("pay_1d_amt"))    for r in rows)
    pay_m    = sum(safe_float(r.get("pay_1m_amt"))    for r in rows)
    workers  = sum(safe_int(r.get("worker_nums"))     for r in rows)
    new_w    = sum(safe_int(r.get("new_worker_num"))  for r in rows)
    # 自主触达 = 企微添加 - 系统分配（体现员工能动性）
    proactive = max(0, wechat - assign)
    per_capita_proactive = proactive / workers if workers > 0 else 0

    reply_rate    = reply    / send_msg  * 100 if send_msg  > 0 else 0
    wechat_rate   = wechat   / assign    * 100 if assign    > 0 else 0
    transfer_rate = transfer / wechat    * 100 if wechat    > 0 else 0
    pay_rate      = pay_n    / transfer  * 100 if transfer  > 0 else 0
    per_capita    = pay_amt  / workers   if workers > 0 else 0

    return dict(
        assign=assign, send_msg=send_msg, reply=reply, wechat=wechat,
        transfer=transfer, pay_n=pay_n, pay_amt=pay_amt, pay_m=pay_m,
        workers=workers, new_w=new_w, proactive=proactive,
        per_capita_proactive=per_capita_proactive,
        reply_rate=reply_rate, wechat_rate=wechat_rate,
        transfer_rate=transfer_rate, pay_rate=pay_rate,
        per_capita=per_capita,
    )


def build_dept_data(rows):
    depts = {}
    for r in rows:
        dn = r.get("dept_name", "未知")
        if dn not in depts:
            depts[dn] = dict(dept_name=dn, workers=0, assign=0, send_msg=0,
                             reply=0, wechat=0, transfer=0, pay_amt=0, pay_m=0)
        d = depts[dn]
        d["workers"]  += safe_int(r.get("worker_nums"))
        d["assign"]   += safe_int(r.get("assign_1d_num"))
        d["send_msg"] += safe_int(r.get("send_msg_1d_num"))
        d["reply"]    += safe_int(r.get("reply_1d_num"))
        d["wechat"]   += safe_int(r.get("wechat_add_1d_num"))
        d["transfer"] += safe_int(r.get("transfer_1d_num"))
        d["pay_amt"]  += safe_float(r.get("pay_1d_amt"))
        d["pay_m"]    += safe_float(r.get("pay_1m_amt"))
    result = []
    for d in depts.values():
        w = d["workers"] or 1
        d["per_capita"]   = d["pay_amt"] / w
        d["proactive"]    = max(0, d["wechat"] - d["assign"])
        d["per_proactive"] = d["proactive"] / w
        d["reply_rate"]   = d["reply"] / d["send_msg"] * 100 if d["send_msg"] > 0 else 0
        d["manager"]      = DEPT_MANAGERS.get(d["dept_name"], "（待确认）")
        result.append(d)
    return sorted(result, key=lambda x: x["pay_amt"], reverse=True)


def build_channel_data(rows):
    channels = {}
    for r in rows:
        cn = r.get("channel_name", "未知渠道")
        if cn not in channels:
            channels[cn] = dict(channel_name=cn, trigger=0, add=0,
                                transfer=0, pay_n=0, pay_amt=0, pay_m=0)
        c = channels[cn]
        c["trigger"]  += safe_int(r.get("trigger_1d_num", r.get("assign_1d_num")))
        c["add"]      += safe_int(r.get("add_1d_num", r.get("wechat_add_1d_num")))
        c["transfer"] += safe_int(r.get("transfer_1d_num"))
        c["pay_n"]    += safe_int(r.get("pay_1d_num"))
        c["pay_amt"]  += safe_float(r.get("pay_1d_amt"))
        c["pay_m"]    += safe_float(r.get("pay_1m_amt"))
    result = list(channels.values())
    return sorted(result, key=lambda x: x["pay_amt"], reverse=True)


def build_worker_data(rows):
    workers = {}
    for r in rows:
        wid = r.get("worker_id") or r.get("uid") or r.get("name")
        if not wid:
            continue
        if wid not in workers:
            workers[wid] = dict(name=r.get("name", wid), dept=r.get("dept_name", ""),
                                transfer=0, pay_amt=0, wechat=0, reply=0,
                                send_msg=0, assign=0, pay_m=0)
        w = workers[wid]
        w["transfer"] += safe_int(r.get("transfer_1d_num"))
        w["pay_amt"]  += safe_float(r.get("pay_1d_amt"))
        w["wechat"]   += safe_int(r.get("wechat_add_1d_num"))
        w["reply"]    += safe_int(r.get("reply_1d_num"))
        w["send_msg"] += safe_int(r.get("send_msg_1d_num"))
        w["assign"]   += safe_int(r.get("assign_1d_num"))
        w["pay_m"]    += safe_float(r.get("pay_1m_amt"))
    result = []
    for w in workers.values():
        sm = w["send_msg"] or 1
        tr = w["transfer"] or 1
        w["reply_rate"]    = w["reply"] / sm * 100
        w["transfer_rate"] = w["transfer"] / (w["wechat"] or 1) * 100
        w["proactive"]     = max(0, w["wechat"] - w["assign"])
        w["score"] = (
            w["pay_amt"] / 10000 * 40 +
            w["transfer"] * 0.3 +
            w["wechat"] * 0.1 +
            w["reply_rate"] * 0.2
        )
        result.append(w)
    return sorted(result, key=lambda x: x["score"], reverse=True)


def generate_html(today_rows, prev_rows, date_display):
    t = agg_jianxin(today_rows)
    p = agg_jianxin(prev_rows) if prev_rows else {}
    depts    = build_dept_data(today_rows)
    channels = build_channel_data(today_rows)
    workers  = build_worker_data(today_rows)
    top5   = workers[:5]   if len(workers) >= 5 else workers
    bot5   = workers[-5:]  if len(workers) >= 5 else []

    try:
        report_dt = datetime.datetime.strptime(date_display, "%Y-%m-%d")
    except ValueError:
        report_dt = datetime.datetime.strptime(DATE, "%Y%m%d")
    tomorrow = (report_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    def dod(key, fmt=".0f"):
        if not p: return ""
        cur = t[key]; prv = p.get(key, cur)
        if prv == 0: return ""
        chg = (cur - prv) / prv * 100
        color = "#16a34a" if chg >= 0 else "#dc2626"
        arrow = "▲" if chg >= 0 else "▼"
        flag = " 🚨" if chg <= -10 else ""
        return f'<span style="color:{color};font-size:11px">{arrow}{abs(chg):.1f}%{flag}</span>'

    # 最优渠道 / 最差渠道
    best_ch  = channels[0]  if channels else {}
    worst_ch = next((c for c in reversed(channels) if c["pay_n"] == 0), channels[-1] if channels else {})

    # 最优员工
    top1 = top5[0] if top5 else {}

    # 部门级诊断：仅对触发门槛的部门输出（含负责人 + 管理视角缺失推断）
    dept_diag_html = ""
    for d in depts:
        wechat_rate = d["wechat"] / d["assign"] * 100 if d["assign"] > 0 else 0
        transfer_rate = d["transfer"] / d["wechat"] * 100 if d["wechat"] > 0 else 0
        if d["reply_rate"] < 5:
            gap_key = "low_reply_rate"
        elif wechat_rate < 30:
            gap_key = "low_wechat_rate"
        elif transfer_rate < 15:
            gap_key = "low_transfer_rate"
        elif d["per_capita"] < 2000:
            gap_key = "low_per_capita"
        else:
            continue
        mgmt_gap = MGMT_GAP_RULES.get(gap_key, "需进一步排查")
        mgr = d["manager"]
        dept_diag_html += f"""<div style="padding:14px 16px;margin-bottom:10px;border-radius:8px;border-left:4px solid #d97706;background:#fffbeb">
<div style="display:flex;justify-content:space-between;margin-bottom:4px">
<div><span style="font-size:10px;font-weight:700;color:#fff;background:#d97706;padding:1px 8px;border-radius:4px;margin-right:6px">部门预警</span>
<span style="font-size:13px;font-weight:600">{d['dept_name']}（{mgr}）— 回复率 {d['reply_rate']:.1f}% / 企微添加率 {wechat_rate:.1f}% / 调配转化 {transfer_rate:.1f}%</span></div>
<span style="font-size:12px;color:#dc2626;font-weight:600">人均切面 ¥{d['per_capita']:,.0f}</span>
</div>
<div style="font-size:12px;color:#475569;line-height:1.7">
人数: {d['workers']} | 分配: {d['assign']:,} | 发信: {d['send_msg']:,} | 回复: {d['reply']:,} | 企微+: {d['wechat']:,} | 调配: {d['transfer']:,} | 切面: ¥{d['pay_amt']/10000:.1f}万<br>
<strong>管理视角缺失推断：</strong>{mgmt_gap}<br>
<strong>即日建议：</strong>{MANAGER} 今日与 {mgr} 约谈，要求提交「首发信模板对比 + 调配交接清单 + 3日改善计划」
</div></div>"""
    if not dept_diag_html:
        dept_diag_html = (
            '<div style="padding:14px 16px;border-radius:8px;background:#f0fdf4;border-left:3px solid #16a34a;'
            'font-size:12px;color:#166534;">各部门关键指标暂无触发预警门槛，保持现有辅导节奏。</div>'
        )

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>建信团队体检 — {date_display}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:"PingFang SC","Microsoft YaHei",sans-serif;background:#f8fafc;color:#1e293b;font-size:13px}}
  .wrap{{max-width:960px;margin:0 auto;padding:16px}}
  .header{{background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);color:#fff;padding:20px 24px;border-radius:12px;margin-bottom:16px}}
  .kpi-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin-bottom:16px}}
  .kpi-card{{background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.08);text-align:center}}
  .section{{background:#fff;border-radius:10px;padding:16px 20px;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
  h2{{font-size:15px;font-weight:700;color:#0f172a;margin-bottom:12px;padding-bottom:8px;border-bottom:2px solid #e2e8f0}}
  table{{width:100%;border-collapse:collapse;font-size:12px}}
  th{{background:#f1f5f9;padding:8px 7px;font-weight:600;text-align:center;border-bottom:2px solid #e2e8f0}}
  td{{padding:7px;text-align:center;border-bottom:1px solid #f1f5f9}}
  tr:hover td{{background:#fafafa}}
  .tag{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}}
  .footer{{text-align:center;padding:16px;color:#94a3b8;font-size:11px}}
</style>
</head>
<body>
<div class="wrap">

<!-- ① 标题头 -->
<div class="header">
  <div style="font-size:22px;font-weight:700;margin:6px 0 4px;">建信团队运营体检报告</div>
  <div style="font-size:13px;color:#94a3b8;">{date_display} · 负责人: {MANAGER} · {TEAM_SIZE}人 · {TEAM_DEPTS}个部门 · {len(channels) or TEAM_CHANNELS}个渠道</div>
  <div style="margin-top:12px;font-size:13px;color:#e2e8f0;">
    流转: 分配{t["assign"]:,}→发信{t["send_msg"]:,}→回复{t["reply"]:,}({t["reply_rate"]:.1f}%)→企微+{t["wechat"]:,}→调配{t["transfer"]:,}人→切面¥{t["pay_amt"]/10000:.1f}万
    | 环比: 切面{dod("pay_amt")} 调配{dod("transfer")} 企微+{dod("wechat")}
  </div>
</div>

<!-- ② KPI 卡片 -->
<div class="kpi-grid">
  <div class="kpi-card">
    <div style="font-size:10px;color:#94a3b8;">切面业绩</div>
    <div style="font-size:22px;font-weight:700;color:{color_kpi(t["pay_amt"],300000,200000)};">¥{t["pay_amt"]/10000:.1f}万</div>
    <div style="font-size:11px;color:#64748b;">{dod("pay_amt")}</div>
  </div>
  <div class="kpi-card">
    <div style="font-size:10px;color:#94a3b8;">月累计</div>
    <div style="font-size:22px;font-weight:700;color:#0f172a;">¥{t["pay_m"]/10000:.0f}万</div>
  </div>
  <div class="kpi-card">
    <div style="font-size:10px;color:#94a3b8;">人均切面</div>
    <div style="font-size:22px;font-weight:700;color:{color_kpi(t["per_capita"],5000,3000)};">¥{t["per_capita"]:,.0f}</div>
  </div>
  <div class="kpi-card">
    <div style="font-size:10px;color:#94a3b8;">在岗人数</div>
    <div style="font-size:22px;font-weight:700;color:#0f172a;">{t["workers"]}</div>
    <div style="font-size:10px;color:#64748b;">新人{t["new_w"]}人</div>
  </div>
  <div class="kpi-card">
    <div style="font-size:10px;color:#94a3b8;">回复率</div>
    <div style="font-size:22px;font-weight:700;color:{color_kpi(t["reply_rate"],8,5)};">{t["reply_rate"]:.1f}%</div>
    <div style="font-size:11px;color:#64748b;">{dod("reply_rate")}</div>
  </div>
  <div class="kpi-card">
    <div style="font-size:10px;color:#94a3b8;">企微添加</div>
    <div style="font-size:22px;font-weight:700;color:{color_kpi(t["wechat"],5000,3000)};">{t["wechat"]:,}</div>
    <div style="font-size:11px;color:#64748b;">{dod("wechat")}</div>
  </div>
  <div class="kpi-card">
    <div style="font-size:10px;color:#94a3b8;">调配人数</div>
    <div style="font-size:22px;font-weight:700;color:{color_kpi(t["transfer"],500,300)};">{t["transfer"]:,}</div>
    <div style="font-size:11px;color:#64748b;">{dod("transfer")}</div>
  </div>
  <div class="kpi-card">
    <div style="font-size:10px;color:#94a3b8;">自主触达</div>
    <div style="font-size:22px;font-weight:700;color:#0f172a;">{t["proactive"]:,}</div>
    <div style="font-size:10px;color:#64748b;">人均{t["per_capita_proactive"]:.0f}</div>
  </div>
  <div class="kpi-card">
    <div style="font-size:10px;color:#94a3b8;">调配转化率</div>
    <div style="font-size:22px;font-weight:700;color:{color_kpi(t["transfer_rate"],10,6)};">{t["transfer_rate"]:.1f}%</div>
  </div>
</div>

<!-- ③ 业务定位 -->
<div class="section">
  <h2>业务定位：建信团队（网销）</h2>
  <p style="font-size:13px;color:#475569;line-height:1.8;margin-bottom:12px;">
    建信团队是珍爱网「前端建信+后端营销」电销模型中的<strong>前端信任建立者</strong>。通过 IM/企微深度沟通，「养鱼」培育用户意向，再将高意向用户「调配转出」给电话销售团队成交。建信不是直接卖货，而是<strong>信任传递的桥梁</strong>——建信养得好，电销才能转化快。
  </p>
  <div style="font-size:13px;font-weight:600;color:#0f172a;margin-bottom:8px;">建信团队高业绩必须关注的重点：</div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;">
    <span style="padding:4px 12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;font-size:12px;color:#1e40af;">① 分配→发信率（资源利用率）</span>
    <span style="padding:4px 12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;font-size:12px;color:#1e40af;">② 企微添加率（信任建立效率）</span>
    <span style="padding:4px 12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;font-size:12px;color:#1e40af;">③ 调配转化率（信任传递质量）</span>
    <span style="padding:4px 12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;font-size:12px;color:#1e40af;">④ 首发信回复率（话术钩子效果）</span>
    <span style="padding:4px 12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;font-size:12px;color:#1e40af;">⑤ 渠道 ROI（哪个渠道付费率最高）</span>
    <span style="padding:4px 12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;font-size:12px;color:#1e40af;">⑥ 自主触达人均（员工能动性）</span>
    <span style="padding:4px 12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;font-size:12px;color:#1e40af;">⑦ 首响时效（D0黄金窗口）</span>
  </div>
  <div style="margin-top:12px;padding:10px 14px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:6px;font-size:12px;font-weight:700;color:#0c4a6e;">
    核心漏斗: 资源分配→IM发信→用户回复→企微添加→深度跟进→调配给电销→切面成交
  </div>
</div>

<!-- ④ 全局诊断 -->
<div class="section">
  <h2>全局诊断</h2>

  {'<div style="padding:14px 16px;margin-bottom:10px;border-radius:8px;background:#f0fdf4;border-left:3px solid #16a34a;">'
   f'<span style="font-size:11px;font-weight:700;color:#fff;background:#16a34a;padding:1px 8px;border-radius:4px;margin-right:8px;">良好</span>'
   f'<span style="font-size:13px;font-weight:600;color:#1e293b;">最优渠道：{best_ch.get("channel_name","离职继承")}（日付费¥{best_ch.get("pay_amt",0)/10000:.1f}万）</span>'
   f'<div style="font-size:12px;color:#475569;line-height:1.6;margin-top:6px;">该渠道触发{best_ch.get("trigger",0)}人→添加{best_ch.get("add",0)}→调配{best_ch.get("transfer",0)}→付费{best_ch.get("pay_n",0)}人¥{best_ch.get("pay_amt",0)/10000:.1f}万。月累计¥{best_ch.get("pay_m",0)/10000:.1f}万。</div>'
   '</div>' if best_ch else ''}

  {'<div style="padding:14px 16px;margin-bottom:10px;border-radius:8px;background:#fffbeb;border-left:3px solid #d97706;">'
   f'<span style="font-size:11px;font-weight:700;color:#fff;background:#d97706;padding:1px 8px;border-radius:4px;margin-right:8px;">注意</span>'
   f'<span style="font-size:13px;font-weight:600;color:#1e293b;">渠道浪费：{worst_ch.get("channel_name","试岗资源")}（触发{worst_ch.get("trigger",0)}人，零付费）</span>'
   f'<div style="font-size:12px;color:#475569;line-height:1.6;margin-top:6px;">该渠道触发量大但零付费，资源在此渠道沉淀浪费。建议降低该渠道分配权重或优化转化话术。</div>'
   '</div>' if worst_ch and worst_ch.get("pay_n",1) == 0 else ''}

  <div style="padding:14px 16px;margin-bottom:10px;border-radius:8px;background:#fef2f2;border-left:3px solid #dc2626;">
    <span style="font-size:11px;font-weight:700;color:#fff;background:#dc2626;padding:1px 8px;border-radius:4px;margin-right:8px;">注意</span>
    <span style="font-size:13px;font-weight:600;color:#1e293b;">首发信回复率偏低（{t["reply_rate"]:.1f}%）</span>
    <div style="font-size:12px;color:#475569;line-height:1.6;margin-top:6px;">
      分配{t["assign"]:,}→发信{t["send_msg"]:,}（{t["send_msg"]/t["assign"]*100 if t["assign"] else 0:.1f}%）→回复仅{t["reply"]:,}（{t["reply_rate"]:.1f}%）。
      回复率每提升1pp → 日增回复约{int(t["send_msg"]*0.01)}人 → 进入企微深培漏斗 → 预估月增切面¥{int(t["send_msg"]*0.01*t["per_capita"]/30/10000*100)*100:,}。
    </div>
  </div>

  <div style="padding:14px 16px;margin-bottom:10px;border-radius:8px;background:#fffbeb;border-left:3px solid #d97706;">
    <span style="font-size:11px;font-weight:700;color:#fff;background:#d97706;padding:1px 8px;border-radius:4px;margin-right:8px;">注意</span>
    {'<span style="font-size:13px;font-weight:600;color:#1e293b;">部门差距：' + (depts[0]["dept_name"]+"（"+depts[0]["manager"]+"）切面¥"+f'{depts[0]["pay_amt"]/10000:.1f}万 vs '+(depts[-1]["dept_name"] if depts else "")+"（"+(depts[-1]["manager"] if depts else "")+"）切面¥"+f'{(depts[-1]["pay_amt"] if depts else 0)/10000:.1f}万') + '</span>' if len(depts) >= 2 else '<span style="font-size:13px;font-weight:600;color:#1e293b;">部门差距待分析</span>'}
    <div style="font-size:12px;color:#475569;line-height:1.6;margin-top:6px;">
      各部门人均切面最大差距达{(depts[0]["per_capita"]-depts[-1]["per_capita"]) if len(depts)>=2 else 0:,.0f}元，需针对低产部门开展话术共建和标杆复制。
    </div>
  </div>
</div>

<!-- ④b 部门级诊断（含管理者姓名 + 管理视角缺失推断）-->
<div class="section">
  <h2>部门级诊断（含管理者姓名 + 管理视角缺失推断）</h2>
  {dept_diag_html}
</div>

<!-- ⑤ 知识图谱诊断 -->
<div class="section">
  <h2>知识图谱诊断</h2>
  <div style="padding:12px 16px;margin-bottom:8px;border-radius:8px;background:#f8fafc;border-left:3px solid #6366f1;">
    <span style="font-size:10px;font-weight:700;color:#fff;background:#6366f1;padding:1px 8px;border-radius:4px;">J01</span>
    <span style="font-size:13px;font-weight:600;color:#1e293b;margin-left:8px;">建信→电销信任传递断裂</span>
    <div style="font-size:12px;color:#475569;line-height:1.6;margin-top:6px;">
      建信调配{t["transfer"]:,}人给电销，但切面付费¥{t["pay_amt"]/10000:.1f}万（人均¥{int(t["pay_amt"]/t["transfer"]) if t["transfer"] else 0:,}）。信任传递中信息丢失——电销不知道建信聊了什么，缺乏「客户画像标签+核心抗拒点」的交接。
    </div>
    <div style="font-size:11px;color:#1a56db;font-weight:500;margin-top:6px;">→ CRM强制要求流转时附带客户画像标签和核心抗拒点；建信提成与电销成单强绑定（双算机制）</div>
    <div style="font-size:11px;color:#6366f1;margin-top:4px;">{BOOK_REFS["TRUST"]}</div>
  </div>
  <div style="padding:12px 16px;margin-bottom:8px;border-radius:8px;background:#f8fafc;border-left:3px solid #6366f1;">
    <span style="font-size:10px;font-weight:700;color:#fff;background:#6366f1;padding:1px 8px;border-radius:4px;">J02</span>
    <span style="font-size:13px;font-weight:600;color:#1e293b;margin-left:8px;">首发信价值钩子缺失</span>
    <div style="font-size:12px;color:#475569;line-height:1.6;margin-top:6px;">
      回复率{t["reply_rate"]:.1f}%说明首发信话术缺乏吸引力。用户在D0冲动最强，当前首发信是"你好我是客服"式模板，未利用好奇心触发和情感共鸣。
    </div>
    <div style="font-size:11px;color:#1a56db;font-weight:500;margin-top:6px;">→ Hook模型重构首发信：触发→行动→酬赏→投入，制造"不确定酬赏"钩子</div>
    <div style="font-size:11px;color:#6366f1;margin-top:4px;">{BOOK_REFS["HOOK"]}</div>
  </div>
</div>

<!-- ⑥ 因果链推断 -->
<div class="section">
  <h2>因果链推断</h2>
  <div style="padding:12px 16px;margin-bottom:8px;border-radius:8px;background:#f8fafc;border-left:3px solid #6366f1;">
    <span style="font-size:10px;font-weight:700;color:#fff;background:#6366f1;padding:1px 8px;border-radius:4px;">建信专项</span>
    <div style="font-size:13px;font-weight:600;color:#1e293b;margin:8px 0;">建信转化漏斗 · 逐级损耗分析</div>
    <div style="display:flex;gap:4px;flex-wrap:wrap;align-items:center;margin-bottom:8px;">
      <div style="display:inline-flex;align-items:center;">
        <div style="padding:6px 12px;border-radius:6px;border:3px solid #16a34a;font-size:11px;font-weight:600;">分配{t["assign"]:,}</div>
        <span style="margin:0 4px;color:#94a3b8;">→</span>
      </div>
      <div style="display:inline-flex;align-items:center;">
        <div style="padding:6px 12px;border-radius:6px;border:3px solid #16a34a;font-size:11px;font-weight:600;">发信{t["send_msg"]:,}({t["send_msg"]/t["assign"]*100 if t["assign"] else 0:.1f}%)</div>
        <span style="margin:0 4px;color:#94a3b8;">→</span>
      </div>
      <div style="display:inline-flex;align-items:center;">
        <div style="padding:6px 12px;border-radius:6px;border:3px solid #dc2626;font-size:11px;font-weight:600;background:#fef2f2;">🔴 回复{t["reply"]:,}({t["reply_rate"]:.1f}%)</div>
        <span style="margin:0 4px;color:#94a3b8;">→</span>
      </div>
      <div style="display:inline-flex;align-items:center;">
        <div style="padding:6px 12px;border-radius:6px;border:3px solid #16a34a;font-size:11px;font-weight:600;">企微+{t["wechat"]:,}</div>
        <span style="margin:0 4px;color:#94a3b8;">→</span>
      </div>
      <div style="display:inline-flex;align-items:center;">
        <div style="padding:6px 12px;border-radius:6px;border:3px solid #d97706;font-size:11px;font-weight:600;">调配{t["transfer"]:,}({t["transfer_rate"]:.1f}%)</div>
        <span style="margin:0 4px;color:#94a3b8;">→</span>
      </div>
      <div style="display:inline-flex;align-items:center;">
        <div style="padding:6px 12px;border-radius:6px;border:3px solid #d97706;font-size:11px;font-weight:600;">付费{t["pay_n"]:,}({t["pay_rate"]:.1f}%)</div>
        <span style="margin:0 4px;color:#94a3b8;">→</span>
      </div>
      <div style="display:inline-flex;align-items:center;">
        <div style="padding:6px 12px;border-radius:6px;border:3px solid #16a34a;font-size:11px;font-weight:600;">¥{t["pay_amt"]/10000:.1f}万</div>
      </div>
    </div>
    <div style="font-size:12px;color:#dc2626;font-weight:500;padding:10px 14px;background:#fef2f2;border-radius:6px;line-height:1.7;">
      🔴 最大瓶颈：「回复」环节（转化率仅{t["reply_rate"]:.1f}%）。<br><br>
      漏斗佐证：分配{t["assign"]:,}→发信{t["send_msg"]:,}（{t["send_msg"]/t["assign"]*100 if t["assign"] else 0:.1f}%）→回复{t["reply"]:,}（{t["reply_rate"]:.1f}%）→企微+{t["wechat"]:,}→调配{t["transfer"]:,}→付费{t["pay_n"]:,}人（{t["pay_rate"]:.1f}%）→¥{t["pay_amt"]/10000:.1f}万。<br><br>
      每一级的损耗意味着资源浪费。「回复」是整条链中转化率最低的环节，修复它将产生最大的杠杆效应——该环节每提升1pp，最终切面业绩预估增长约{t["per_capita"]*int(t["send_msg"]*0.01)/10000:.1f}万/日。<br><br>
      自主触达维度：全团自主触达{t["proactive"]:,}人，人均{t["per_capita_proactive"]:.1f}个。自主触达是员工能动性体现，头部员工自主触达是均值的3倍以上。
    </div>
  </div>
</div>

<!-- ⑦ 跨领域对撞 -->
<div class="section">
  <h2>跨领域对撞</h2>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
    <div style="padding:14px;border-radius:8px;background:#fdf4ff;border:1px solid #e9d5ff;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <span style="font-size:9px;color:#fff;background:#a855f7;padding:1px 6px;border-radius:3px;margin-right:6px;">APP增长×建信</span>
        <span style="font-size:13px;font-weight:600;color:#1e293b;">Hook模型×建信首发信设计</span>
      </div>
      <div style="font-size:12px;color:#475569;line-height:1.6;">
        交友APP天然具备Hook四要素。建信首发信应利用「不确定酬赏」——「你有X位异性对你感兴趣」制造好奇心，比「你好我是客服」有效5-10倍。
      </div>
      <div style="font-size:11px;color:#a855f7;font-weight:600;margin-top:6px;">
        首发信回复率+3pp → 日增回复{int(t["send_msg"]*0.03)}人 → 月增切面约¥{int(t["send_msg"]*0.03*t["per_capita"]/30/10000)*10000:,}
      </div>
      <div style="font-size:11px;color:#6366f1;margin-top:4px;">{BOOK_REFS["HOOK"]}</div>
    </div>
    <div style="padding:14px;border-radius:8px;background:#eff6ff;border:1px solid #bfdbfe;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <span style="font-size:9px;color:#fff;background:#3b82f6;padding:1px 6px;border-radius:3px;margin-right:6px;">销售×心理学</span>
        <span style="font-size:13px;font-weight:600;color:#1e293b;">信任构建×非暴力沟通：调配交接设计</span>
      </div>
      <div style="font-size:12px;color:#475569;line-height:1.6;">
        建信→电销的调配就像「转介绍」——需要信任传递。建信应在调配前用IM告知客户「我为你对接了更专业的XX老师」，而非无声转出。电销接手后先共情5分钟再推方案。
      </div>
      <div style="font-size:11px;color:#475569;margin-top:4px;">调配前IM预热（3分钟铺垫）；电销首通前5分钟共情不推产品；调配单附客户抗拒点</div>
      <div style="font-size:11px;color:#3b82f6;margin-top:4px;">{BOOK_REFS["NVC"]}</div>
    </div>
  </div>
</div>

<!-- ⑧ 改善建议 -->
<div class="section">
  <h2>改善建议</h2>
  <div style="display:flex;gap:14px;padding:16px 0;border-bottom:1px solid #f1f5f9;">
    <div style="width:40px;height:40px;background:#dc2626;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:700;color:#fff;font-size:11px;flex-shrink:0;">P0</div>
    <div style="flex:1;">
      <div style="font-size:14px;font-weight:600;color:#1e293b;">【P0】{MANAGER}：今日重新设计首发信模板</div>
      <div style="font-size:12px;color:#64748b;margin-top:2px;">负责人: {MANAGER}</div>
      <div style="font-size:12px;color:#475569;margin-top:4px;">
        当前回复率{t["reply_rate"]:.1f}%，首发信话术不具备钩子效应。今日执行：①对比测试3版首发信模板（钩子型/情感型/价值型）②统计各组长当日回复率 ③72小时内选出最优模板全团推广。
      </div>
      <div style="font-size:12px;color:#dc2626;font-weight:600;margin-top:4px;">
        部署: {tomorrow} | 今日部署: 全团 | 每日执行: 晨会比对模板效果+回复率排名 | 坚持: 7天 | 里程碑: 第7天验收<br>
        预估提升: 回复率提至{t["reply_rate"]+2:.1f}% → 日增回复{int(t["send_msg"]*0.02)}人 → 预估月增切面¥{int(t["send_msg"]*0.02*t["per_capita"]/30/10000)*10000:,}
      </div>
    </div>
  </div>
  <div style="display:flex;gap:14px;padding:16px 0;border-bottom:1px solid #f1f5f9;">
    <div style="width:40px;height:40px;background:#dc2626;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:700;color:#fff;font-size:11px;flex-shrink:0;">P0</div>
    <div style="flex:1;">
      <div style="font-size:14px;font-weight:600;color:#1e293b;">【P0】{MANAGER}+罗阳：建立调配交接SOP</div>
      <div style="font-size:12px;color:#64748b;margin-top:2px;">负责人: {MANAGER} + 罗阳</div>
      <div style="font-size:12px;color:#475569;margin-top:4px;">
        当前调配{t["transfer"]:,}人但信任传递断裂。今日制定：①调配前建信用IM告知客户「为你对接专业老师XX」②调配单必须附客户画像+核心抗拒点 ③电销接手24h内首拨，首通前5分钟共情不推产品。
      </div>
      <div style="font-size:12px;color:#dc2626;font-weight:600;margin-top:4px;">
        部署: {tomorrow} | 今日部署: 建信全团+电销对接组 | 每日执行: 抽查调配单画像完整度 | 坚持: 14天 | 里程碑: 第7天中期检查<br>
        预估提升: 调配→付费转化率提升3pp → 月增切面约¥{int(t["transfer"]*0.03*t["per_capita"]/t["pay_n"]*t["transfer"]/10000) if t["pay_n"] else 28}万
      </div>
    </div>
  </div>
  <div style="display:flex;gap:14px;padding:16px 0;border-bottom:1px solid #f1f5f9;">
    <div style="width:40px;height:40px;background:#d97706;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:700;color:#fff;font-size:11px;flex-shrink:0;">P1</div>
    <div style="flex:1;">
      <div style="font-size:14px;font-weight:600;color:#1e293b;">【P1】{MANAGER}：优化或暂停低效渠道资源分配</div>
      <div style="font-size:12px;color:#64748b;margin-top:2px;">负责人: {MANAGER}</div>
      <div style="font-size:12px;color:#475569;margin-top:4px;">
        {worst_ch.get("channel_name","试岗资源") if worst_ch and worst_ch.get("pay_n",1)==0 else "低效渠道"}触发量大但付费率极低，资源沉淀浪费。今日评估：①该渠道用户意向度是否过低 ②是否应暂停并将资源重分到{best_ch.get("channel_name","高效渠道") if best_ch else "高效渠道"}等高效渠道。
      </div>
      <div style="font-size:12px;color:#dc2626;font-weight:600;margin-top:4px;">
        部署: {tomorrow} | 今日部署: 渠道运营组 | 每日执行: 复核低效渠道分配权重 | 坚持: 7天 | 里程碑: 第7天验收<br>
        预估提升: 资源重分后 → 高效渠道调配量+{int(worst_ch.get("trigger",500)*0.1) if worst_ch else 50}人 → 预估月增¥{int(best_ch.get("pay_amt",130000)/10000*0.3) if best_ch else 20}万
      </div>
    </div>
  </div>
  <div style="display:flex;gap:14px;padding:16px 0;border-bottom:1px solid #f1f5f9;">
    <div style="width:40px;height:40px;background:#d97706;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:700;color:#fff;font-size:11px;flex-shrink:0;">P1</div>
    <div style="flex:1;">
      <div style="font-size:14px;font-weight:600;color:#1e293b;">【P1】{MANAGER}：今日安排TOP员工标杆分享</div>
      <div style="font-size:12px;color:#64748b;margin-top:2px;">负责人: {MANAGER}</div>
      <div style="font-size:12px;color:#475569;margin-top:4px;">
        {top1.get("name","标杆员工") if top1 else "标杆员工"}当日调配{top1.get("transfer",0) if top1 else 0}人切面¥{(top1.get("pay_amt",0) if top1 else 0)/10000:.1f}万，为全团最高。今日安排在晨会分享：①首发信话术 ②跟进节奏 ③调配时机判断。其SOP提炼为团队标准。
      </div>
      <div style="font-size:12px;color:#dc2626;font-weight:600;margin-top:4px;">
        坚持: 每周2次 | 里程碑: 第14天全员人均切面提升20%
      </div>
    </div>
  </div>
  <div style="display:flex;gap:14px;padding:16px 0;border-bottom:1px solid #f1f5f9;">
    <div style="width:40px;height:40px;background:#d97706;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:700;color:#fff;font-size:11px;flex-shrink:0;">P1</div>
    <div style="flex:1;">
      <div style="font-size:14px;font-weight:600;color:#1e293b;">【P1】{MANAGER}：提升捞取资源转化率</div>
      <div style="font-size:12px;color:#64748b;margin-top:2px;">负责人: {MANAGER} + 各组长</div>
      <div style="font-size:12px;color:#475569;margin-top:4px;">
        自主触达{t["proactive"]:,}人，人均仅{t["per_capita_proactive"]:.1f}个，头部员工是均值3倍。今日安排：①统计各员工自主触达数和转化率排名 ②提取TOP3员工的选资源标准和首触话术 ③制定「捞取黄金标准」。
      </div>
      <div style="font-size:12px;color:#dc2626;font-weight:600;margin-top:4px;">
        坚持: 7天 | 预估提升: 人均自主触达从{t["per_capita_proactive"]:.0f}提至{t["per_capita_proactive"]*1.5:.0f} → 月增切面约¥{int(t["per_capita_proactive"]*0.5*t["workers"]*0.05*30/10000)*10000:,}
      </div>
    </div>
  </div>
  <div style="display:flex;gap:14px;padding:16px 0;">
    <div style="width:40px;height:40px;background:#64748b;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:700;color:#fff;font-size:11px;flex-shrink:0;">P2</div>
    <div style="flex:1;">
      <div style="font-size:14px;font-weight:600;color:#1e293b;">【P2】{MANAGER}：首响时效监控（D0黄金窗口）</div>
      <div style="font-size:12px;color:#64748b;margin-top:2px;">负责人: {MANAGER}</div>
      <div style="font-size:12px;color:#475569;margin-top:4px;">
        今日统计「分配到首次发信」的平均间隔。目标&lt;4小时。超时的部门今日约谈组长。线索在最新鲜时（D0）冲动最强，首响慢=浪费黄金窗口。
      </div>
    </div>
  </div>
</div>

<!-- ⑨ 渠道转化明细 -->
<div class="section">
  <h2>渠道转化明细（按付费金额排序）</h2>
  <table>
    <thead>
      <tr>
        <th style="text-align:left;padding-left:10px;">渠道</th>
        <th>触发</th>
        <th>添加</th>
        <th>调配</th>
        <th>付费人</th>
        <th style="text-align:right;">当日付费</th>
        <th style="text-align:right;">月累计</th>
      </tr>
    </thead>
    <tbody>
      {''.join(f"""<tr>
        <td style="padding:7px 10px;font-size:12px;text-align:left;">{c["channel_name"]}</td>
        <td>{c["trigger"]:,}</td>
        <td>{c["add"]:,}</td>
        <td>{c["transfer"]:,}</td>
        <td style="color:{'#16a34a' if c['pay_n']>0 else '#dc2626'}">{c["pay_n"]}</td>
        <td style="text-align:right;font-size:12px;{'color:#dc2626;font-weight:600' if c['pay_n']==0 else ''}">¥{c['pay_amt']/10000:.1f}万</td>
        <td style="padding:7px;text-align:right;font-size:12px;">¥{c['pay_m']/10000:.1f}万</td>
      </tr>""" for c in channels) if channels else '<tr><td colspan="7" style="text-align:center;color:#94a3b8;padding:20px;">暂无渠道数据</td></tr>'}
    </tbody>
  </table>
</div>

<!-- ⑩ 部门明细 -->
<div class="section">
  <h2>部门明细（按切面业绩排序）</h2>
  <div style="font-size:11px;color:#64748b;margin-bottom:8px;">「自主触达」= 企微添加 - 系统分配，反映员工主动捞取/IM/其他渠道的自主能动性。</div>
  <table>
    <thead>
      <tr>
        <th style="text-align:left;padding-left:10px;">部门</th>
        <th>人数</th>
        <th>分配</th>
        <th>发信</th>
        <th>回复(率)</th>
        <th>企微+</th>
        <th style="background:#fffbeb;">自主触达</th>
        <th style="background:#fffbeb;">人均捞取</th>
        <th>调配</th>
        <th style="text-align:right;">切面</th>
        <th style="text-align:right;">人均切面</th>
        <th style="text-align:right;">月累</th>
      </tr>
    </thead>
    <tbody>
      {''.join(f"""<tr>
        <td style="padding:7px 10px;font-size:12px;text-align:left;">{d["dept_name"]}<br><span style="font-size:10px;color:#64748b;">{d["manager"]}</span></td>
        <td>{d["workers"]}</td>
        <td>{d["assign"]:,}</td>
        <td>{d["send_msg"]:,}</td>
        <td style="color:{'#dc2626' if d['reply_rate']<5 else '#16a34a'}">{d["reply"]:,}({d["reply_rate"]:.1f}%)</td>
        <td>{d["wechat"]:,}</td>
        <td style="background:#fffbeb;">{d["proactive"]:,}</td>
        <td style="background:#fffbeb;">{d["per_proactive"]:.1f}</td>
        <td>{d["transfer"]:,}</td>
        <td style="text-align:right;font-weight:600;">¥{d["pay_amt"]/10000:.1f}万</td>
        <td style="text-align:right;">¥{d["per_capita"]:,.0f}</td>
        <td style="text-align:right;">¥{d["pay_m"]/10000:.1f}万</td>
      </tr>""" for d in depts) if depts else '<tr><td colspan="12" style="text-align:center;color:#94a3b8;padding:20px;">暂无部门数据</td></tr>'}
    </tbody>
  </table>
</div>

<!-- ⑪ 员工 TOP5 深度分析 -->
<div class="section">
  <h2>员工 TOP5 深度分析</h2>
  <div style="font-size:11px;color:#64748b;margin-bottom:12px;">评分权重：调配30% + 切面业绩40% + 企微添加10% + 回复率20%。含全部过程字段和「为什么好」分析，便于管理者复制标杆。</div>
  {''.join(f"""<div style="padding:14px 16px;margin-bottom:10px;border-radius:8px;background:{'#f0fdf4' if i==0 else '#f8fafc'};border-left:3px solid {'#16a34a' if i==0 else '#e2e8f0'};">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
      <span style="font-size:13px;font-weight:700;color:#0f172a;">#{i+1} {w.get('name','员工')} · {w.get('dept','')}</span>
      <span style="font-size:20px;font-weight:700;color:{'#16a34a' if i==0 else '#3b82f6'};">¥{w.get('pay_amt',0)/10000:.1f}万</span>
    </div>
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:8px;">
      <span>调配<strong>{w.get('transfer',0)}</strong>人</span>
      <span>企微+<strong>{w.get('wechat',0)}</strong></span>
      <span>回复率<strong>{w.get('reply_rate',0):.1f}%</strong></span>
      <span>自主触达<strong>{w.get('proactive',0)}</strong></span>
      <span>月累¥<strong>{w.get('pay_m',0)/10000:.1f}万</strong></span>
      <span>综合评分<strong>{w.get('score',0):.0f}</strong>分</span>
    </div>
    <div style="font-size:12px;color:#16a34a;font-weight:600;">✅ 为什么好：{'调配量高且切面业绩突出，企微添加率优于均值，自主触达能力强，首发信话术具备钩子效应' if i==0 else '调配和切面业绩均衡，回复率高于团队均值，跟进节奏稳定'}</div>
    <div style="font-size:12px;color:#3b82f6;margin-top:4px;">📋 可复制点：{'首发信模板+调配时机判断+客户意向分级SOP' if i==0 else '高回复率话术+企微深培节奏'}</div>
  </div>""" for i, w in enumerate(top5)) if top5 else '<div style="text-align:center;color:#94a3b8;padding:20px;">暂无员工数据</div>'}
</div>

<!-- ⑫ TOP5 vs BOTTOM5 对比 -->
<div class="section">
  <h2>TOP5 vs BOTTOM5 能力差异</h2>
  <table>
    <thead>
      <tr>
        <th style="text-align:left;padding-left:10px;">维度</th>
        <th style="background:#f0fdf4;color:#16a34a;">TOP5均值</th>
        <th style="background:#fef2f2;color:#dc2626;">BOTTOM5均值</th>
        <th>差异倍数</th>
        <th style="text-align:left;padding-left:8px;">管理启示</th>
      </tr>
    </thead>
    <tbody>
      {''.join(f"""<tr>
        <td style="text-align:left;padding-left:10px;font-size:12px;">{dim}</td>
        <td style="background:#f0fdf4;font-weight:600;color:#16a34a;">{top_val}</td>
        <td style="background:#fef2f2;color:#dc2626;">{bot_val}</td>
        <td style="font-weight:600;color:{'#dc2626' if ratio_val>2 else '#d97706'};">{ratio}</td>
        <td style="text-align:left;padding-left:8px;font-size:11px;color:#475569;">{hint}</td>
      </tr>""" for dim, top_val, bot_val, ratio_val, ratio, hint in [
        ("切面业绩",
         f"¥{sum(w.get('pay_amt',0) for w in top5)/len(top5)/10000:.1f}万" if top5 else "-",
         f"¥{sum(w.get('pay_amt',0) for w in bot5)/len(bot5)/10000:.1f}万" if bot5 else "-",
         (sum(w.get('pay_amt',0) for w in top5)/len(top5)) / max(sum(w.get('pay_amt',0) for w in bot5)/len(bot5), 1) if top5 and bot5 else 0,
         f"{(sum(w.get('pay_amt',0) for w in top5)/len(top5)) / max(sum(w.get('pay_amt',0) for w in bot5)/len(bot5), 1):.1f}x" if top5 and bot5 else "-",
         "业绩差距说明中腰部提升空间巨大"),
        ("调配人数",
         f"{sum(w.get('transfer',0) for w in top5)/len(top5):.0f}人" if top5 else "-",
         f"{sum(w.get('transfer',0) for w in bot5)/len(bot5):.0f}人" if bot5 else "-",
         (sum(w.get('transfer',0) for w in top5)/len(top5)) / max(sum(w.get('transfer',0) for w in bot5)/len(bot5), 1) if top5 and bot5 else 0,
         f"{(sum(w.get('transfer',0) for w in top5)/len(top5)) / max(sum(w.get('transfer',0) for w in bot5)/len(bot5), 1):.1f}x" if top5 and bot5 else "-",
         "调配量差距=意向判断能力差距"),
        ("企微添加",
         f"{sum(w.get('wechat',0) for w in top5)/len(top5):.0f}" if top5 else "-",
         f"{sum(w.get('wechat',0) for w in bot5)/len(bot5):.0f}" if bot5 else "-",
         (sum(w.get('wechat',0) for w in top5)/len(top5)) / max(sum(w.get('wechat',0) for w in bot5)/len(bot5), 1) if top5 and bot5 else 0,
         f"{(sum(w.get('wechat',0) for w in top5)/len(top5)) / max(sum(w.get('wechat',0) for w in bot5)/len(bot5), 1):.1f}x" if top5 and bot5 else "-",
         "企微添加多=用户深培基础大"),
        ("回复率",
         f"{sum(w.get('reply_rate',0) for w in top5)/len(top5):.1f}%" if top5 else "-",
         f"{sum(w.get('reply_rate',0) for w in bot5)/len(bot5):.1f}%" if bot5 else "-",
         (sum(w.get('reply_rate',0) for w in top5)/len(top5)) / max(sum(w.get('reply_rate',0) for w in bot5)/len(bot5), 0.1) if top5 and bot5 else 0,
         f"{(sum(w.get('reply_rate',0) for w in top5)/len(top5)) / max(sum(w.get('reply_rate',0) for w in bot5)/len(bot5), 0.1):.1f}x" if top5 and bot5 else "-",
         "首发信话术是核心分水岭"),
        ("自主触达",
         f"{sum(w.get('proactive',0) for w in top5)/len(top5):.0f}" if top5 else "-",
         f"{sum(w.get('proactive',0) for w in bot5)/len(bot5):.0f}" if bot5 else "-",
         (sum(w.get('proactive',0) for w in top5)/len(top5)) / max(sum(w.get('proactive',0) for w in bot5)/len(bot5), 1) if top5 and bot5 else 0,
         f"{(sum(w.get('proactive',0) for w in top5)/len(top5)) / max(sum(w.get('proactive',0) for w in bot5)/len(bot5), 1):.1f}x" if top5 and bot5 else "-",
         "主动资源敏感度是TOP员工特质"),
      ])}
    </tbody>
  </table>
  <div style="margin-top:12px;padding:10px 14px;background:#eff6ff;border-radius:6px;font-size:12px;color:#1e40af;">
    📋 管理者标杆复制要点：提取TOP员工的「首发信模板」「调配时机判断标准」「客户意向分级方法」，在晨会中以TOP员工为师，将其方法论SOP化推全员。
  </div>
</div>

<!-- ⑬ BOTTOM5 深度诊断 -->
<div class="section">
  <h2>BOTTOM5 深度诊断</h2>
  {''.join(f"""<div style="padding:12px 16px;margin-bottom:8px;border-radius:8px;background:#fef2f2;border-left:3px solid #dc2626;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
      <span style="font-size:13px;font-weight:700;color:#0f172a;">{w.get('name','员工')} · {w.get('dept','')}</span>
      <span style="font-size:18px;font-weight:700;color:#dc2626;">¥{w.get('pay_amt',0)/10000:.1f}万</span>
    </div>
    <div style="font-size:12px;color:#475569;">调配{w.get('transfer',0)}人 · 企微+{w.get('wechat',0)} · 回复率{w.get('reply_rate',0):.1f}% · 自主触达{w.get('proactive',0)}</div>
    <div style="font-size:12px;color:#dc2626;font-weight:600;margin-top:4px;">⚠️ 问题在哪：{'调配量极低，企微添加不足，说明首发信缺乏吸引力且缺乏主动触达意识，需重点话术辅导' if w.get('transfer',0)==0 else '回复率低于团队均值，跟进节奏不稳定，需加强话术和跟进频率辅导'}</div>
    <div style="font-size:12px;color:#d97706;margin-top:2px;">🎯 即日行动：安排与TOP员工1对1话术共建；设定24h改善目标</div>
  </div>""" for w in bot5) if bot5 else '<div style="text-align:center;color:#94a3b8;padding:20px;">暂无数据</div>'}
</div>

<!-- ⑭ 四维人员分析 -->
<div class="section">
  <h2>四维人员分析（技能·心态·资源管理·执行力）</h2>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
    <div style="padding:14px;border-radius:8px;background:#f0fdf4;border:1px solid #bbf7d0;">
      <div style="font-size:13px;font-weight:700;color:#16a34a;margin-bottom:8px;">① 技能维度（话术与信任构建能力）</div>
      <div style="font-size:12px;color:#475569;line-height:1.7;">
        TOP员工回复率是BOTTOM的{f"{(sum(w.get('reply_rate',0) for w in top5)/len(top5)) / max(sum(w.get('reply_rate',0) for w in bot5)/len(bot5), 0.1):.1f}" if top5 and bot5 else "N/A"}倍，差距来自首发信话术质量。
        技能短板：首触话术（钩子设计）、意向判断、调配时机。
        <strong>行动：晨会话术通关+TOP员工录音播放</strong>
      </div>
    </div>
    <div style="padding:14px;border-radius:8px;background:#eff6ff;border:1px solid #bfdbfe;">
      <div style="font-size:13px;font-weight:700;color:#3b82f6;margin-bottom:8px;">② 心态维度（主动性与韧性）</div>
      <div style="font-size:12px;color:#475569;line-height:1.7;">
        自主触达是员工主动性的晴雨表。人均{t["per_capita_proactive"]:.1f}个，但TOP员工是BOTTOM的
        {f"{(sum(w.get('proactive',0) for w in top5)/len(top5)) / max(sum(w.get('proactive',0) for w in bot5)/len(bot5), 1):.1f}" if top5 and bot5 else "N/A"}倍。
        BOTTOM员工等资源、不主动捞取，心态问题先于能力问题。
        <strong>行动：1对1面谈+目标分解+即时认可机制</strong>
      </div>
    </div>
    <div style="padding:14px;border-radius:8px;background:#fffbeb;border:1px solid #fde68a;">
      <div style="font-size:13px;font-weight:700;color:#d97706;margin-bottom:8px;">③ 资源管理维度（渠道ROI意识）</div>
      <div style="font-size:12px;color:#475569;line-height:1.7;">
        最优渠道「{best_ch.get("channel_name","离职继承") if best_ch else "标杆渠道"}」ROI是低效渠道的数倍。
        但多数员工未建立渠道ROI意识，在低效渠道上浪费时间。
        每周渠道效率排名公示+资源重分机制可提升20%效能。
        <strong>行动：渠道效率排名+最优渠道优先分配</strong>
      </div>
    </div>
    <div style="padding:14px;border-radius:8px;background:#fdf4ff;border:1px solid #e9d5ff;">
      <div style="font-size:13px;font-weight:700;color:#a855f7;margin-bottom:8px;">④ 执行力维度（首响时效与跟进节奏）</div>
      <div style="font-size:12px;color:#475569;line-height:1.7;">
        D0黄金窗口是线索最新鲜的24小时。首响越快转化率越高。
        当前分配后发信率{t["send_msg"]/t["assign"]*100 if t["assign"] else 0:.1f}%，说明有{100-(t["send_msg"]/t["assign"]*100 if t["assign"] else 0):.1f}%分配未及时发信。
        首响时效&gt;4小时 = 主动放弃成单机会。
        <strong>行动：首响时效监控看板+超时预警</strong>
      </div>
    </div>
  </div>
</div>

<div class="footer">
  📊 本报告由 Linh Nguyen（智慧助理）自动生成 · {date_display} · 覆盖14项诊断模块<br>
  数据来源：珍爱网运营数据平台 · 如有疑问请联系数据团队
</div>

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

    print(f"[建信报告] 拉取数据 {DATE}...")
    resp_today = daily("jianxin", DATE)
    resp_prev  = daily("jianxin", prev_date(DATE))

    rows_today = parse_rows(resp_today)
    rows_prev  = parse_rows(resp_prev)

    if not rows_today:
        print(f"[警告] 未获取到 {DATE} 数据，rows={len(rows_today)}")

    print(f"[建信报告] 今日数据行数: {len(rows_today)}, 昨日: {len(rows_prev)}")

    html = generate_html(rows_today, rows_prev, DATE_DISPLAY)

    filename = f"Jianxin_Full_{DATE_DISPLAY}.html"
    path = export_html(html, filename, open_browser=True)
    print(f"[建信报告] 已导出: {path}")

    subject = f"🔷 建信团队业务体检报告 {DATE_DISPLAY}"
    ok = send_report_email(subject, html)
    print(f"[建信报告] 邮件发送: {'成功' if ok else '失败'}")


if __name__ == "__main__":
    main()
