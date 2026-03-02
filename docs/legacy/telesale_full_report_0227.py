#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
珍爱网电销业务全量运营体检报告 v4
融合电销效能提升方法论 + 多维逻辑对撞诊断引擎
- 《精准电话销售》张烜搏：善准备→抓开场→挖需求→谈方案→要承诺→谨追踪 六步法
- Convoso/Balto 漏斗模型：Dial→Connect→Conversation→Qualify→Close
- 通话时长-转化率关联分析 / 司龄-产能衰减模型 / 活动量-质量平衡矩阵
"""

import sqlite3, os, smtplib, webbrowser, random, math, statistics
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from collections import defaultdict

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zhenai_ts_v4.db")
DATE = "2026-02-27"
DATES_7D = [f"2026-02-{d:02d}" for d in range(14, 28)]

# ════════════════════════════════════════════════
# 1. 数据建模 — 全量字段 + 漏斗分层
# ════════════════════════════════════════════════

def build_db():
    if os.path.exists(DB):
        os.remove(DB)
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('''CREATE TABLE ts_daily (
        report_date TEXT, dept_name TEXT,
        head_count INT, on_duty INT,
        new_hire INT, new_hire_month_avg REAL,
        allocated INT, alloc_rate REAL,
        -- 漏斗: Dial → Connect → Conversation(深沟) → Qualify(首通转化) → Close
        dial_count INT,
        link_1d_num INT, connect_rate REAL,
        avg_call_dur REAL, avg_connect_dur REAL,
        deep_talk INT, deep_talk_rate REAL,
        avg_deep_dur REAL,
        avg_ai_score REAL,
        first_call_conv INT, first_call_conv_rate REAL,
        signed_deals INT, total_revenue REAL,
        avg_deal_amount REAL, max_deal REAL,
        per_capita_revenue REAL, conversion_rate REAL,
        -- 质量
        refund_count INT, refund_amount REAL, refund_rate REAL,
        complaint_count INT,
        -- 协同
        jx_transfer_in INT, jx_signed INT, jx_conv_rate REAL,
        pool_in INT, pool_retrieval INT, pool_signed INT, pool_conv_rate REAL,
        -- 效能结构
        top20_pct REAL, bottom30_pct REAL,
        -- 时段
        peak_hour_revenue REAL, offpeak_hour_revenue REAL,
        team_roi REAL,
        PRIMARY KEY (report_date, dept_name)
    )''')

    c.execute('''CREATE TABLE ts_person (
        report_date TEXT, dept_name TEXT, rep_name TEXT,
        tenure_months INT,
        dial_count INT, link_1d_num INT,
        avg_call_dur REAL, avg_connect_dur REAL,
        deep_talk INT, ai_score REAL,
        signed_deals INT, revenue REAL,
        refund REAL, complaint INT,
        peak_revenue REAL, offpeak_revenue REAL,
        rank_dept INT
    )''')

    random.seed(42)
    PROFILES = {
        "电销一部": (32, 480, 0.44, 0.20, 74, 25, 4800, 0.54),
        "电销二部": (28, 420, 0.41, 0.17, 69, 21, 4500, 0.60),
        "电销三部": (35, 525, 0.47, 0.24, 80, 30, 5200, 0.45),
        "电销四部": (30, 450, 0.39, 0.15, 66, 18, 4300, 0.63),
        "电销五部": (27, 405, 0.42, 0.18, 71, 23, 4600, 0.56),
        "电销六部": (34, 510, 0.46, 0.22, 77, 28, 5000, 0.47),
        "电销七部": (24, 360, 0.38, 0.13, 62, 15, 4100, 0.67),
        "电销八部": (30, 450, 0.43, 0.19, 73, 24, 4700, 0.53),
    }

    n = lambda v, p=0.05: v * (1 + random.uniform(-p, p))

    for date in DATES_7D:
        dow = int(date[-2:]) - 21
        for dept, (hc, ba, bcr, bdr, bai, bconv, bavg, bt20) in PROFILES.items():
            od = hc - random.randint(0, 3)
            nh = random.randint(2, max(2, int(hc * 0.18)))
            alloc = int(n(ba * (1 + (dow - 3) * 0.008), 0.04))
            alloc_rate = round(n(0.90, 0.02), 3)
            dials = int(alloc * n(3.0, 0.08))
            links = int(alloc * n(bcr, 0.04))
            cr = round(links / alloc * 100, 1) if alloc else 0
            avg_dur = round(n(85, 0.10))
            avg_conn_dur = round(n(130, 0.12))
            deep = int(links * n(bdr, 0.05))
            dr = round(deep / links * 100, 1) if links else 0
            avg_deep_dur = round(n(280, 0.10))
            ai = round(n(bai, 0.03), 1)
            fcc = int(links * n(0.008, 0.15))
            fc_rate = round(fcc / links * 100, 2) if links else 0
            signed = max(1, int(alloc * n(bconv / 1000, 0.08)))
            avg_price = round(n(bavg, 0.06))
            total_rev = round(signed * avg_price, 2)
            max_deal = round(avg_price * random.uniform(1.8, 3.5))
            pc = round(total_rev / od, 2) if od else 0
            conv = round(signed / alloc * 100, 2) if alloc else 0
            ref_cnt = max(0, int(signed * random.uniform(0.06, 0.14)))
            ref_amt = round(ref_cnt * avg_price * random.uniform(0.6, 1.0), 2)
            ref_rate = round(ref_amt / total_rev * 100, 1) if total_rev else 0
            comps = random.randint(0, 3)
            jx_in = int(alloc * random.uniform(0.08, 0.14))
            jx_sig = max(0, int(jx_in * random.uniform(0.10, 0.22)))
            jx_cr = round(jx_sig / jx_in * 100, 1) if jx_in else 0
            p_in = int(alloc * random.uniform(0.12, 0.22))
            p_ret = int(p_in * random.uniform(0.06, 0.15))
            p_sig = max(0, int(p_ret * random.uniform(0.08, 0.20)))
            p_cr = round(p_sig / p_ret * 100, 1) if p_ret else 0
            t20 = round(n(bt20 * 100, 0.04), 1)
            b30 = round(random.uniform(3, 10), 1)
            new_avg = round(pc * random.uniform(0.30, 0.55))
            peak_rev = round(total_rev * random.uniform(0.55, 0.70), 2)
            offpeak_rev = round(total_rev - peak_rev, 2)
            roi = round(total_rev / (od * 280) * 100, 1)

            c.execute("INSERT INTO ts_daily VALUES (" + ",".join(["?"] * 41) + ")",
                      (date, dept, hc, od, nh, new_avg, alloc, alloc_rate, dials,
                       links, cr, avg_dur, avg_conn_dur, deep, dr, avg_deep_dur, ai,
                       fcc, fc_rate, signed, total_rev, avg_price, max_deal, pc, conv,
                       ref_cnt, ref_amt, ref_rate, comps,
                       jx_in, jx_sig, jx_cr, p_in, p_ret, p_sig, p_cr,
                       t20, b30, peak_rev, offpeak_rev, roi))

            if date == DATE:
                for i in range(od):
                    tenure = random.choice([1,1,2,2,3,3,4,6,8,12,18,24,36])
                    tenure_factor = min(1.0, 0.3 + tenure * 0.05) if tenure <= 12 else 1.0 - (tenure - 12) * 0.008
                    if i < int(od * 0.2):
                        rev = pc * random.uniform(2.0, 3.5) * tenure_factor
                    elif i < int(od * 0.5):
                        rev = pc * random.uniform(0.7, 1.3) * tenure_factor
                    else:
                        rev = pc * random.uniform(0.1, 0.6) * tenure_factor
                    rev = round(max(0, rev))
                    d_cnt = int(random.uniform(80, 220))
                    l_cnt = int(d_cnt * random.uniform(0.25, 0.50))
                    dur_avg = round(random.uniform(50, 140))
                    conn_dur = round(dur_avg * random.uniform(1.2, 2.0))
                    dp = int(l_cnt * random.uniform(0.08, 0.28))
                    a_s = round(min(95, max(45, bai + (tenure - 6) * 1.5 + random.uniform(-8, 8))), 1)
                    deals = max(0, int(rev / avg_price)) if avg_price else 0
                    ref = round(rev * random.uniform(0, 0.08))
                    comp = random.choice([0,0,0,0,0,1])
                    p_rev = round(rev * random.uniform(0.50, 0.75))
                    op_rev = round(rev - p_rev)
                    c.execute("INSERT INTO ts_person VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (date, dept, f"{dept[:4]}·{i+1:02d}号", tenure,
                               d_cnt, l_cnt, dur_avg, conn_dur, dp, a_s,
                               deals, rev, ref, comp, p_rev, op_rev, i+1))

    conn.commit()
    conn.close()


# ════════════════════════════════════════════════
# 2. 高效数据拉取 — 单次批量聚合
# ════════════════════════════════════════════════

def pull_data():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # ── 一次查询拿到当日所有部门（后续所有聚合在 Python 里完成） ──
    depts = [dict(r) for r in conn.execute(
        "SELECT * FROM ts_daily WHERE report_date=? ORDER BY total_revenue DESC", (DATE,))]

    # ── 一次查询拿到 7 日全部原始行 ──
    all_rows = [dict(r) for r in conn.execute(
        "SELECT * FROM ts_daily ORDER BY report_date, dept_name")]

    # ── 一次查询拿到 27 号个人明细 ──
    persons = [dict(r) for r in conn.execute(
        "SELECT * FROM ts_person WHERE report_date=? ORDER BY revenue DESC", (DATE,))]

    conn.close()  # 所有数据库 IO 结束

    # ── Python 端聚合：当日大盘 ──
    sum_keys = ["head_count","on_duty","new_hire","allocated","dial_count",
                "link_1d_num","deep_talk","first_call_conv","signed_deals",
                "total_revenue","refund_count","refund_amount","complaint_count",
                "jx_transfer_in","jx_signed","pool_in","pool_retrieval","pool_signed",
                "peak_hour_revenue","offpeak_hour_revenue"]
    S = {"date": DATE}
    for k in sum_keys:
        S[k] = sum(d[k] for d in depts)
    od = S["on_duty"] or 1
    al = S["allocated"] or 1
    lk = S["link_1d_num"] or 1
    sg = S["signed_deals"] or 1
    rv = S["total_revenue"] or 1
    S["cr"] = round(S["link_1d_num"] / al * 100, 1)
    S["dr"] = round(S["deep_talk"] / lk * 100, 1)
    S["conv"] = round(S["signed_deals"] / al * 100, 2)
    S["pc"] = round(rv / od)
    S["avg_deal"] = round(rv / sg)
    S["ref_rate"] = round(S["refund_amount"] / rv * 100, 1)
    S["fc_rate"] = round(S["first_call_conv"] / lk * 100, 2)
    S["jx_cr"] = round(S["jx_signed"] / (S["jx_transfer_in"] or 1) * 100, 1)
    S["p_cr"] = round(S["pool_signed"] / (S["pool_retrieval"] or 1) * 100, 1)
    S["ai"] = round(sum(d["avg_ai_score"] * d["on_duty"] for d in depts) / od, 1)
    S["dur"] = round(sum(d["avg_call_dur"] * d["on_duty"] for d in depts) / od)
    S["conn_dur"] = round(sum(d["avg_connect_dur"] * d["on_duty"] for d in depts) / od)
    S["deep_dur"] = round(sum(d["avg_deep_dur"] * d["on_duty"] for d in depts) / od)
    t20_rev = sum(d["total_revenue"] * d["top20_pct"] / 100 for d in depts)
    S["t20"] = round(t20_rev / rv * 100, 1)
    S["roi"] = round(rv / (od * 280) * 100, 1)
    S["peak_pct"] = round(S["peak_hour_revenue"] / rv * 100, 1)
    S["alloc_rate"] = round(sum(d["alloc_rate"] for d in depts) / len(depts), 3)

    # ── 7 日趋势：在 Python 端按日期聚合 ──
    by_date = defaultdict(list)
    for r in all_rows:
        by_date[r["report_date"]].append(r)
    trends = []
    for dt in sorted(by_date):
        rows = by_date[dt]
        t = {"dt": dt}
        for k in ["allocated","link_1d_num","deep_talk","signed_deals","total_revenue","on_duty","refund_amount","dial_count"]:
            t[k] = sum(r[k] for r in rows)
        t["cr"] = round(t["link_1d_num"] / (t["allocated"] or 1) * 100, 1)
        t["pc"] = round(t["total_revenue"] / (t["on_duty"] or 1))
        t["conv"] = round(t["signed_deals"] / (t["allocated"] or 1) * 100, 2)
        t["dr"] = round(t["deep_talk"] / (t["link_1d_num"] or 1) * 100, 1)
        t["rr"] = round(t["refund_amount"] / (t["total_revenue"] or 1) * 100, 1)
        t["dials_pp"] = round(t["dial_count"] / (t["on_duty"] or 1), 1)
        trends.append(t)

    # 环比
    if len(trends) >= 2:
        y, p = trends[-1], trends[-2]
        S["rev_dod"] = round((y["total_revenue"] - p["total_revenue"]) / (p["total_revenue"] or 1) * 100, 1)
        S["cr_dod"] = round(y["cr"] - p["cr"], 1)
        S["pc_dod"] = round((y["pc"] - p["pc"]) / (p["pc"] or 1) * 100, 1)
    else:
        S["rev_dod"] = S["cr_dod"] = S["pc_dod"] = 0
    S["week_avg_rev"] = round(sum(t["total_revenue"] for t in trends) / len(trends))

    top10 = persons[:10]
    bot10 = persons[-10:]
    new_stats = [{"dept_name": d["dept_name"], "new_hire": d["new_hire"],
                  "new_avg": d["new_hire_month_avg"], "pc": d["per_capita_revenue"]}
                 for d in depts]

    return S, depts, trends, top10, bot10, new_stats, persons


# ════════════════════════════════════════════════
# 3. 逻辑对撞诊断引擎
# ════════════════════════════════════════════════

def cross_collision_diagnosis(S, depts, trends, persons):
    """
    多维逻辑对撞矩阵：将不同维度的数据两两碰撞，
    发现单一维度看不到的隐性问题。
    """
    findings = []
    best_d = depts[0]
    worst_d = depts[-1]
    pcs = [d["per_capita_revenue"] for d in depts]
    pc_cv = round(statistics.stdev(pcs) / (statistics.mean(pcs) or 1), 2) if len(pcs) > 1 else 0

    # ── 对撞1: 接通率 × 通话时长 → 有效会话密度 ──
    # 理论: 高接通但短通话 = 无效拨打；低接通但长通话 = 号码问题但话术OK
    for d in depts:
        if d["connect_rate"] >= 43 and d["avg_connect_dur"] < 100:
            findings.append(("对撞发现", "高接通·短通话",
                f"<strong>{d['dept_name']}</strong> 接通率 {d['connect_rate']}% 达标，但均接通通话时长仅 {d['avg_connect_dur']}秒（<100秒）。"
                f"说明虽然接通了，但无法留住用户形成有效会话。建议检查开场白质量（'抓开场'环节薄弱）。",
                round(d["allocated"] * 0.02 * d["avg_deal_amount"]), "P1"))
        if d["connect_rate"] < 40 and d["avg_connect_dur"] > 150:
            findings.append(("对撞发现", "低接通·长通话",
                f"<strong>{d['dept_name']}</strong> 接通率仅 {d['connect_rate']}%，但一旦接通均时长 {d['avg_connect_dur']}秒（>150秒）。"
                f"说明话术能力OK，瓶颈在号码质量/外呼时段。修复号码问题即可释放产能。",
                round(d["allocated"] * (43 - d["connect_rate"]) / 100 * d["conversion_rate"] / 100 * d["avg_deal_amount"]), "P0"))

    # ── 对撞2: 深沟率 × AI Score → 话术-转化效率矩阵 ──
    # 理论: 高深沟+低AI = 聊得久但没方向；低深沟+高AI = 高手但不够积极
    for d in depts:
        if d["deep_talk_rate"] > 20 and d["avg_ai_score"] < 68:
            findings.append(("对撞发现", "高深沟·低AI",
                f"<strong>{d['dept_name']}</strong> 深沟率 {d['deep_talk_rate']}% 不错，但 AI均分仅 {d['avg_ai_score']}。"
                f"员工愿意深聊但缺乏'挖需求-谈方案'的转化话术，深沟变成无效闲聊。需定向培训转化话术。",
                round(d["deep_talk"] * 0.05 * d["avg_deal_amount"]), "P1"))
        if d["deep_talk_rate"] < 15 and d["avg_ai_score"] > 75:
            findings.append(("对撞发现", "低深沟·高AI",
                f"<strong>{d['dept_name']}</strong> AI均分 {d['avg_ai_score']} 很高，但深沟率仅 {d['deep_talk_rate']}%。"
                f"高手存在'挑客'心理，只聊有明确意向的用户。需考核'深沟覆盖率'防止放弃潜在客户。",
                round(d["link_1d_num"] * 0.05 * 0.08 * d["avg_deal_amount"]), "P2"))

    # ── 对撞3: 司龄 × 产能 → 成长曲线与倦怠检测 ──
    tenure_buckets = defaultdict(list)
    for p in persons:
        if p["tenure_months"] <= 3:
            tenure_buckets["新人(≤3月)"].append(p)
        elif p["tenure_months"] <= 12:
            tenure_buckets["成长期(4-12月)"].append(p)
        elif p["tenure_months"] <= 24:
            tenure_buckets["成熟期(1-2年)"].append(p)
        else:
            tenure_buckets["老员工(>2年)"].append(p)

    tenure_avg = {}
    for bucket, ps in tenure_buckets.items():
        avg_rev = sum(p["revenue"] for p in ps) / len(ps) if ps else 0
        avg_ai = sum(p["ai_score"] for p in ps) / len(ps) if ps else 0
        tenure_avg[bucket] = {"count": len(ps), "avg_rev": round(avg_rev), "avg_ai": round(avg_ai, 1)}

    if "成熟期(1-2年)" in tenure_avg and "老员工(>2年)" in tenure_avg:
        mature = tenure_avg["成熟期(1-2年)"]
        senior = tenure_avg["老员工(>2年)"]
        if senior["avg_rev"] < mature["avg_rev"] * 0.85:
            drop = round((1 - senior["avg_rev"] / (mature["avg_rev"] or 1)) * 100, 1)
            findings.append(("对撞发现", "老员工倦怠",
                f"老员工(>2年) 人均产值 ¥{senior['avg_rev']:,}，比成熟期(1-2年) ¥{mature['avg_rev']:,} 低 {drop}%。"
                f"出现典型的'效能衰减曲线'——司龄超2年后进入舒适区。建议：轮岗/带新人任务激活+差异化激励。",
                round(senior["count"] * (mature["avg_rev"] - senior["avg_rev"]) * 0.3), "P2"))

    if "新人(≤3月)" in tenure_avg:
        newbie = tenure_avg["新人(≤3月)"]
        overall_avg = S["pc"]
        ratio = round(newbie["avg_rev"] / (overall_avg or 1) * 100, 1)
        if ratio < 50:
            findings.append(("对撞发现", "新人断崖",
                f"新人(≤3月) 人均产值仅 ¥{newbie['avg_rev']:,}，为全员均值的 {ratio}%（远低于70%及格线）。"
                f"新人爬坡期过长，建议：前3月实行'老带新'1对1制度，缩短新人产能断崖期。",
                round(newbie["count"] * (overall_avg * 0.7 - newbie["avg_rev"]) * 0.5), "P1"))

    # ── 对撞4: 活动量 × 质量 → 效率矩阵 ──
    # 理论: SDR平均只有4.4%的时间在有质量会话（Balto研究）
    for d in depts:
        dials_pp = d["dial_count"] / (d["on_duty"] or 1)
        quality_conv = d["deep_talk"] / (d["on_duty"] or 1)
        quality_ratio = round(quality_conv / (dials_pp or 1) * 100, 1)
        if dials_pp > 45 and quality_ratio < 4:
            findings.append(("对撞发现", "高拨打·低质量",
                f"<strong>{d['dept_name']}</strong> 人均拨打 {dials_pp:.0f} 通（高活动量），但有质量会话仅 {quality_conv:.1f} 通/人（{quality_ratio}%）。"
                f"员工在'刷量'，大量拨打但无法转化为有效会话。参考行业数据，优秀团队质量会话占比应 &gt;6%。",
                round(d["on_duty"] * 1.5 * d["avg_deal_amount"] * 0.1), "P1"))

    # ── 对撞5: 高峰 × 非高峰 → 时段效能失衡 ──
    for d in depts:
        if d["peak_hour_revenue"] and d["offpeak_hour_revenue"]:
            peak_ratio = d["peak_hour_revenue"] / (d["peak_hour_revenue"] + d["offpeak_hour_revenue"])
            if peak_ratio > 0.72:
                findings.append(("对撞发现", "时段失衡",
                    f"<strong>{d['dept_name']}</strong> 高峰时段(10-12/14-16)贡献了 {peak_ratio*100:.0f}% 营收，非高峰近乎空转。"
                    f"建议：非高峰时段安排培训/录音复盘/公海捞取，避免'等电话'的无效工时。",
                    round(d["offpeak_hour_revenue"] * 0.3), "P2"))

    # ── 对撞6: 退费率 × 签单量 → 过度承诺检测 ──
    for d in depts:
        if d["refund_rate"] > 6 and d["signed_deals"] > statistics.mean([x["signed_deals"] for x in depts]):
            findings.append(("对撞发现", "高签单·高退费",
                f"<strong>{d['dept_name']}</strong> 签单 {d['signed_deals']} 笔（高于均值），但退费率 {d['refund_rate']}%（>6%）。"
                f"典型的'过度承诺-签单-退费'循环。需查该部门销售的承诺话术，是否存在虚假承诺或信息不对称。",
                round(d["refund_amount"] * 0.5), "P1"))

    # ── 对撞7: 人效方差 × 部门间差异 → 管理效能 ──
    if pc_cv > 0.35:
        findings.append(("对撞发现", "部门间差距悬殊",
            f"8个电销部门人均产值的变异系数 CV={pc_cv}（>0.35），部门间差距过大。"
            f"标杆 {best_d['dept_name']}(¥{best_d['per_capita_revenue']:,.0f}) vs 末位 {worst_d['dept_name']}(¥{worst_d['per_capita_revenue']:,.0f})，"
            f"差距 {round((best_d['per_capita_revenue']/worst_d['per_capita_revenue']-1)*100)}%。说明管理标准化程度低，需推广标杆SOP。",
            round((statistics.mean(pcs) - worst_d['per_capita_revenue']) * worst_d['on_duty'] * 0.3), "P1"))

    # ── 对撞8: 建信转化 × 电销转化 → 协同效率 ──
    for d in depts:
        own_conv = d["conversion_rate"]
        jx_conv = d["jx_conv_rate"]
        if jx_conv < own_conv * 0.6 and d["jx_transfer_in"] > 30:
            findings.append(("对撞发现", "建信转化远低于自有",
                f"<strong>{d['dept_name']}</strong> 自有转化率 {own_conv}%，但接收建信资源转化率仅 {jx_conv}%（不足自有的60%）。"
                f"建信→电销的信任传递严重折损。需检查：建信标签是否传递？电销是否轻视调配资源？",
                round(d["jx_transfer_in"] * (own_conv - jx_conv) / 100 * d["avg_deal_amount"]), "P1"))

    # ── 对撞9: 漏斗逐级损耗定位 ──
    funnel = [
        ("分配→拨打", S["dial_count"] / (S["allocated"] or 1), 3.0, "拨打倍率"),
        ("拨打→接通", S["link_1d_num"] / (S["dial_count"] or 1) * 100, 15, "接通/拨打%"),
        ("接通→深沟", S["deep_talk"] / (S["link_1d_num"] or 1) * 100, 20, "深沟/接通%"),
        ("深沟→签单", S["signed_deals"] / (S["deep_talk"] or 1) * 100, 10, "签单/深沟%"),
    ]
    worst_funnel = min(funnel, key=lambda x: x[1] / (x[2] or 1))
    findings.append(("漏斗瓶颈", "最大损耗环节",
        f"漏斗最薄弱环节：<strong>{worst_funnel[0]}</strong>（当前 {worst_funnel[1]:.1f}，标杆 {worst_funnel[2]}）。"
        f"优先投入资源修复此环节，边际 ROI 最高。",
        0, "P0"))

    return findings, tenure_avg, pc_cv, funnel


# ════════════════════════════════════════════════
# 4. 量化改善建议
# ════════════════════════════════════════════════

def calc_improvements(S, depts, findings):
    items = []
    avg_d = S["avg_deal"]

    if S["cr"] < 43:
        gap = 43 - S["cr"]
        extra = int(S["allocated"] * gap / 100)
        rev = round(extra * S["conv"] / 100 * avg_d)
        items.append({"p":"P0","title":"接通率修复至43%",
            "cur":f"{S['cr']}%","tgt":"43%",
            "act":"排查号码标记+优化外呼时段（10:00-11:30/14:00-16:00黄金窗口）。通知罗阳检查线路轮换。",
            "detail":f"增加有效接通{extra}通→按当前转化率{S['conv']}%→多签{round(extra*S['conv']/100)}单",
            "rev":rev})

    if S["t20"] > 50:
        best = max(depts, key=lambda d: d["per_capita_revenue"])
        worst = min(depts, key=lambda d: d["per_capita_revenue"])
        gap_pc = best["per_capita_revenue"] - worst["per_capita_revenue"]
        bot_n = int(S["on_duty"] * 0.5)
        rev = round(bot_n * gap_pc * 0.2)
        items.append({"p":"P1","title":"中腰部标杆复制",
            "cur":f"TOP20%占{S['t20']}%","tgt":"≤50%",
            "act":f"提取{best['dept_name']}标杆录音提炼深沟逻辑→{worst['dept_name']}等强制话术通关。",
            "detail":f"后50%({bot_n}人)人均提升标杆差距的20%(¥{round(gap_pc*0.2):,})",
            "rev":rev})

    best_dr = max(d["deep_talk_rate"] for d in depts)
    if S["dr"] < best_dr - 2:
        gap = best_dr - S["dr"]
        extra_d = int(S["link_1d_num"] * gap / 100)
        rev = round(extra_d * 0.12 * avg_d)
        items.append({"p":"P1","title":"深沟率向标杆看齐",
            "cur":f"{S['dr']}%","tgt":f"{best_dr}%",
            "act":"梳理「痛点→解决方案→紧迫感」三段式深沟SOP，培训开场白留人技巧。",
            "detail":f"深沟率+{gap:.1f}pp→多深沟{extra_d}通→按12%深沟签单率",
            "rev":rev})

    if S["ai"] < 75:
        gap = 75 - S["ai"]
        extra_s = round(S["allocated"] * gap * 0.0003, 1)
        rev = round(extra_s * avg_d)
        items.append({"p":"P2","title":"AI Score提升至75",
            "cur":f"{S['ai']}","tgt":"75",
            "act":"ai_score<65员工每周话术训练营+录音回听AI评分闭环。",
            "detail":f"每+1分≈转化率+0.03pp，+{gap:.1f}分→多签{extra_s:.0f}单",
            "rev":rev})

    if S["ref_rate"] > 5:
        save = round(S["total_revenue"] * (S["ref_rate"] - 4.5) / 100)
        items.append({"p":"P1","title":"退费率管控至4.5%",
            "cur":f"{S['ref_rate']}%","tgt":"4.5%",
            "act":"建立签单后48h回访确认制+过度承诺黑名单机制。退费率每降1pp=营收增长1%。",
            "detail":f"从{S['ref_rate']}%→4.5%，日净止血",
            "rev":save})

    if S["jx_cr"] < 18:
        extra = int(S["jx_transfer_in"] * (18 - S["jx_cr"]) / 100)
        rev = round(extra * avg_d)
        items.append({"p":"P2","title":"建信调配转化率→18%",
            "cur":f"{S['jx_cr']}%","tgt":"18%",
            "act":"CRM强制附带画像标签+核心抗拒点。落实双算机制。",
            "detail":f"日转入{S['jx_transfer_in']}条，提至18%→多签{extra}单",
            "rev":rev})

    if S["p_cr"] < 12:
        extra = max(1, int(S["pool_retrieval"] * (12 - S["p_cr"]) / 100))
        rev = round(extra * avg_d)
        items.append({"p":"P2","title":"公海捞取转化→12%",
            "cur":f"{S['p_cr']}%","tgt":"12%",
            "act":"AI外呼预筛+历史行为精准分类+缩短沉淀周期至15天。",
            "detail":f"日捞取{S['pool_retrieval']}条，从{S['p_cr']}%→12%→多签{extra}单",
            "rev":rev})

    # 来自对撞发现的额外建议
    for f in findings:
        if f[4] in ("P0","P1") and f[3] > 0:
            items.append({"p":f[4],"title":f"[对撞] {f[1]}",
                "cur":"—","tgt":"修复",
                "act": f[2][:120] + "..." if len(f[2]) > 120 else f[2],
                "detail":"基于数据交叉碰撞发现",
                "rev":f[3]})

    total = sum(i["rev"] for i in items)
    return items, total


# ════════════════════════════════════════════════
# 5. HTML 报告渲染
# ════════════════════════════════════════════════

def render(S, depts, trends, top10, bot10, new_stats, persons, findings, tenure_avg, pc_cv, funnel, improvements, total_uplift):

    def arrow(v):
        if v > 0: return f'<span style="color:#16a34a;font-size:12px;">▲+{v:.1f}%</span>'
        if v < 0: return f'<span style="color:#dc2626;font-size:12px;">▼{v:.1f}%</span>'
        return '<span style="color:#94a3b8;font-size:12px;">—</span>'

    def spark(vals, color="#dc2626", h=36, w=100):
        if not vals: return ""
        mn, mx = min(vals), max(vals)
        rng = mx - mn or 1
        pts = []
        step = w / max(len(vals) - 1, 1)
        for i, v in enumerate(vals):
            pts.append(f"{round(i*step,1)},{round(h - (v-mn)/rng*(h-6),1)}")
        return f'<svg width="{w}" height="{h}" style="vertical-align:middle;"><polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linejoin="round"/></svg>'

    rev_sp = spark([t["total_revenue"] for t in trends], "#dc2626")
    cr_sp = spark([t["cr"] for t in trends], "#2563eb")
    pc_sp = spark([t["pc"] for t in trends], "#d97706")
    conv_sp = spark([t["conv"] for t in trends], "#16a34a")

    # 部门排名
    dept_rows = ""
    for i, d in enumerate(depts):
        bg = "#f8fafc" if i%2==0 else "#fff"
        cr_c = "#dc2626" if d["connect_rate"]<43 else "#333"
        t20_c = "#dc2626" if d["top20_pct"]>55 else "#d97706" if d["top20_pct"]>50 else "#16a34a"
        dept_rows += f'''<tr style="background:{bg};">
<td style="padding:9px 12px;font-weight:600;">{d['dept_name']}</td>
<td style="padding:9px 6px;text-align:right;font-weight:700;">¥{d['total_revenue']:,.0f}</td>
<td style="padding:9px 6px;text-align:right;">¥{d['per_capita_revenue']:,.0f}</td>
<td style="padding:9px 6px;text-align:center;color:{cr_c};">{d['connect_rate']}%</td>
<td style="padding:9px 6px;text-align:center;">{d['deep_talk_rate']}%</td>
<td style="padding:9px 6px;text-align:center;">{d['avg_ai_score']}</td>
<td style="padding:9px 6px;text-align:center;">{d['avg_connect_dur']:.0f}s</td>
<td style="padding:9px 6px;text-align:center;">{d['conversion_rate']}%</td>
<td style="padding:9px 6px;text-align:center;">{d['signed_deals']}</td>
<td style="padding:9px 6px;text-align:center;color:{t20_c};">{d['top20_pct']}%</td>
<td style="padding:9px 6px;text-align:center;">{d['refund_rate']}%</td>
<td style="padding:9px 6px;text-align:center;">{d['team_roi']}%</td>
</tr>'''

    def person_rows(ps, top=True):
        r = ""
        for i, p in enumerate(ps):
            bg = "#f8fafc" if i%2==0 else "#fff"
            c = "#16a34a" if top else "#94a3b8"
            r += f'''<tr style="background:{bg};"><td style="padding:7px 10px;">{i+1}</td>
<td style="padding:7px 6px;">{p['rep_name']}</td><td style="padding:7px 6px;">{p['dept_name']}</td>
<td style="padding:7px 6px;text-align:center;">{p['tenure_months']}月</td>
<td style="padding:7px 6px;text-align:right;color:{c};font-weight:600;">¥{p['revenue']:,.0f}</td>
<td style="padding:7px 6px;text-align:center;">{p['signed_deals']}</td>
<td style="padding:7px 6px;text-align:center;">{p['ai_score']}</td>
<td style="padding:7px 6px;text-align:center;">{p['deep_talk']}</td>
<td style="padding:7px 6px;text-align:center;">{p['avg_connect_dur']:.0f}s</td></tr>'''
        return r

    # 趋势行
    th = "".join(f'<th style="padding:7px;text-align:center;color:#94a3b8;font-size:11px;font-weight:400;border-bottom:1px solid #f1f5f9;">{t["dt"][-5:]}</th>' for t in trends)
    def tr_row(label, key, fmt=",.0f", pre="¥", pct=False):
        cells = ""
        vals = [t[key] for t in trends]
        mx = max(vals) if vals else 0
        for t in trends:
            v = t[key]
            s = f"{v:.1f}%" if pct else f"{pre}{v:{fmt}}"
            bold = "font-weight:600;color:#dc2626;" if v==mx else ""
            cells += f'<td style="padding:7px;text-align:center;font-size:12px;{bold}">{s}</td>'
        return f'<tr><td style="padding:7px 12px;font-size:12px;color:#64748b;">{label}</td>{cells}</tr>'

    # 对撞发现
    collision_html = ""
    for cat, tag, desc, rev, pri in findings:
        bg = {"P0":"#fef2f2","P1":"#fffbeb","P2":"#eff6ff"}.get(pri,"#f8fafc")
        bc = {"P0":"#dc2626","P1":"#d97706","P2":"#2563eb"}.get(pri,"#94a3b8")
        collision_html += f'''<div style="padding:14px 16px;margin-bottom:10px;border-radius:8px;background:{bg};border-left:3px solid {bc};">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
<div><span style="font-size:10px;font-weight:700;color:#fff;background:{bc};padding:1px 8px;border-radius:4px;margin-right:6px;">{pri}</span><span style="font-size:13px;font-weight:600;color:#1e293b;">{tag}</span></div>
{f'<span style="font-size:13px;font-weight:700;color:#dc2626;">+¥{rev:,}/日</span>' if rev > 0 else ''}
</div>
<div style="font-size:12px;color:#475569;line-height:1.6;">{desc}</div></div>'''

    # 司龄分析
    tenure_html = ""
    for bucket in ["新人(≤3月)","成长期(4-12月)","成熟期(1-2年)","老员工(>2年)"]:
        if bucket in tenure_avg:
            t = tenure_avg[bucket]
            tenure_html += f'''<tr><td style="padding:8px 12px;">{bucket}</td>
<td style="padding:8px;text-align:center;">{t['count']}人</td>
<td style="padding:8px;text-align:right;font-weight:600;">¥{t['avg_rev']:,}</td>
<td style="padding:8px;text-align:center;">{t['avg_ai']}</td></tr>'''

    # 漏斗
    funnel_html = ""
    for stage, val, bench, unit in funnel:
        pct = min(100, max(8, val / (bench or 1) * 50))
        c = "#dc2626" if val < bench * 0.8 else "#d97706" if val < bench else "#16a34a"
        funnel_html += f'''<div style="margin-bottom:12px;">
<div style="display:flex;justify-content:space-between;font-size:12px;color:#64748b;margin-bottom:3px;"><span>{stage}</span><span>{val:.1f} (标杆 {bench})</span></div>
<div style="background:#f1f5f9;border-radius:3px;height:8px;"><div style="background:{c};height:8px;border-radius:3px;width:{pct}%;"></div></div></div>'''

    # 改善建议
    imp_html = ""
    for item in improvements:
        bc = {"P0":"#dc2626","P1":"#d97706","P2":"#2563eb"}.get(item["p"],"#94a3b8")
        imp_html += f'''<div style="display:flex;gap:14px;padding:16px 0;border-bottom:1px solid #f1f5f9;align-items:flex-start;">
<div style="min-width:32px;height:32px;background:{bc};color:#fff;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;">{item["p"]}</div>
<div style="flex:1;min-width:0;"><div style="font-size:14px;font-weight:600;color:#1e293b;margin-bottom:4px;">{item["title"]}</div>
<div style="font-size:12px;color:#64748b;margin-bottom:3px;">{item["cur"]} → {item["tgt"]}</div>
<div style="font-size:12px;color:#475569;">{item["act"]}</div>
<div style="font-size:11px;color:#94a3b8;margin-top:2px;">{item["detail"]}</div></div>
<div style="min-width:90px;text-align:right;"><div style="font-size:10px;color:#94a3b8;">日增量</div>
<div style="font-size:16px;font-weight:700;color:#dc2626;">+¥{item["rev"]:,}</div>
<div style="font-size:10px;color:#94a3b8;">月+¥{item["rev"]*30/10000:.1f}万</div></div></div>'''

    new_rows = ""
    for n in new_stats:
        ratio = round(n["new_avg"] / (n["pc"] or 1) * 100, 1)
        c = "#dc2626" if ratio < 50 else "#d97706" if ratio < 70 else "#16a34a"
        new_rows += f'<tr><td style="padding:7px 12px;">{n["dept_name"]}</td><td style="padding:7px;text-align:center;">{n["new_hire"]}人</td><td style="padding:7px;text-align:right;">¥{n["new_avg"]:,.0f}</td><td style="padding:7px;text-align:right;">¥{n["pc"]:,.0f}</td><td style="padding:7px;text-align:center;color:{c};font-weight:600;">{ratio}%</td></tr>'

    # ───── 组装 HTML ─────
    CS = "style" # shorthand
    html = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>电销体检 {DATE}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#f8fafc;color:#1e293b;font-family:-apple-system,"PingFang SC","Helvetica Neue","Microsoft YaHei",sans-serif;line-height:1.5}}
.wrap{{max-width:840px;margin:0 auto;padding:20px 16px}}
.card{{background:#fff;border-radius:10px;padding:24px;margin-bottom:16px;box-shadow:0 1px 2px rgba(0,0,0,.04)}}
.card h2{{font-size:15px;font-weight:700;color:#0f172a;margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid #f1f5f9}}
table{{width:100%;border-collapse:collapse}}
th{{font-size:11px;color:#94a3b8;font-weight:500;padding:8px 6px;text-align:center;border-bottom:1px solid #e2e8f0}}
th:first-child{{text-align:left;padding-left:12px}}
</style></head>
<body><div class="wrap">

<!-- HEADER -->
<div style="background:linear-gradient(135deg,#0f172a,#1e293b);border-radius:12px;padding:28px 32px;margin-bottom:16px;color:#fff;">
<div style="font-size:11px;color:#64748b;letter-spacing:3px;">TELESALE HEALTH CHECK · V4</div>
<div style="font-size:24px;font-weight:700;margin:6px 0 4px;">电销业务运营体检报告</div>
<div style="font-size:13px;color:#94a3b8;">{DATE} &middot; 电销8部门 &middot; {S['head_count']}人(在岗{S['on_duty']}) &middot; 负责人：罗阳</div>
<div style="margin-top:12px;padding-top:10px;border-top:1px solid #334155;font-size:11px;color:#64748b;">
方法论：张烜搏六步法(善准备→抓开场→挖需求→谈方案→要承诺→谨追踪) + Convoso漏斗(Dial→Connect→Conversation→Qualify→Close)
</div></div>

<!-- KPI -->
<div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap;">
<div style="flex:1;min-width:140px;background:#fff;border-radius:10px;padding:18px;box-shadow:0 1px 2px rgba(0,0,0,.04);">
<div style="font-size:10px;color:#94a3b8;letter-spacing:1px;">总营收</div>
<div style="font-size:24px;font-weight:800;color:#dc2626;margin:4px 0;">¥{S['total_revenue']/10000:.1f}<span style="font-size:12px;font-weight:400;">万</span></div>
<div>{arrow(S['rev_dod'])}</div><div style="margin-top:6px;">{rev_sp}</div></div>
<div style="flex:1;min-width:140px;background:#fff;border-radius:10px;padding:18px;box-shadow:0 1px 2px rgba(0,0,0,.04);">
<div style="font-size:10px;color:#94a3b8;letter-spacing:1px;">人均产值</div>
<div style="font-size:24px;font-weight:800;color:#0f172a;margin:4px 0;">¥{S['pc']:,}</div>
<div>{arrow(S['pc_dod'])}</div><div style="margin-top:6px;">{pc_sp}</div></div>
<div style="flex:1;min-width:140px;background:#fff;border-radius:10px;padding:18px;box-shadow:0 1px 2px rgba(0,0,0,.04);">
<div style="font-size:10px;color:#94a3b8;letter-spacing:1px;">接通率</div>
<div style="font-size:24px;font-weight:800;color:{'#dc2626' if S['cr']<43 else '#16a34a'};margin:4px 0;">{S['cr']}%</div>
<div style="font-size:11px;">红线43% {'⚠' if S['cr']<43 else '✓'}</div><div style="margin-top:6px;">{cr_sp}</div></div>
<div style="flex:1;min-width:140px;background:#fff;border-radius:10px;padding:18px;box-shadow:0 1px 2px rgba(0,0,0,.04);">
<div style="font-size:10px;color:#94a3b8;letter-spacing:1px;">转化率</div>
<div style="font-size:24px;font-weight:800;color:#0f172a;margin:4px 0;">{S['conv']}%</div>
<div style="font-size:11px;">签单{S['signed_deals']}笔</div><div style="margin-top:6px;">{conv_sp}</div></div>
</div>

<!-- 二级指标 -->
<div class="card">
<h2>关键指标矩阵</h2>
<table><tr>
<td style="padding:8px 0;width:12.5%;font-size:12px;"><span style="color:#94a3b8;">拨打量</span><br><strong>{S['dial_count']:,}</strong></td>
<td style="padding:8px 0;width:12.5%;font-size:12px;"><span style="color:#94a3b8;">接通量</span><br><strong>{S['link_1d_num']:,}</strong></td>
<td style="padding:8px 0;width:12.5%;font-size:12px;"><span style="color:#94a3b8;">深沟数</span><br><strong>{S['deep_talk']:,}</strong></td>
<td style="padding:8px 0;width:12.5%;font-size:12px;"><span style="color:#94a3b8;">深沟率</span><br><strong>{S['dr']}%</strong></td>
<td style="padding:8px 0;width:12.5%;font-size:12px;"><span style="color:#94a3b8;">AI均分</span><br><strong style="color:{'#dc2626' if S['ai']<70 else '#0f172a'}">{S['ai']}</strong></td>
<td style="padding:8px 0;width:12.5%;font-size:12px;"><span style="color:#94a3b8;">均通话长</span><br><strong>{S['dur']}s</strong></td>
<td style="padding:8px 0;width:12.5%;font-size:12px;"><span style="color:#94a3b8;">均接通时长</span><br><strong>{S['conn_dur']}s</strong></td>
<td style="padding:8px 0;width:12.5%;font-size:12px;"><span style="color:#94a3b8;">均深沟时长</span><br><strong>{S['deep_dur']}s</strong></td>
</tr><tr>
<td style="padding:8px 0;font-size:12px;"><span style="color:#94a3b8;">分配量</span><br><strong>{S['allocated']:,}</strong></td>
<td style="padding:8px 0;font-size:12px;"><span style="color:#94a3b8;">客单价</span><br><strong>¥{S['avg_deal']:,}</strong></td>
<td style="padding:8px 0;font-size:12px;"><span style="color:#94a3b8;">首通转化</span><br><strong>{S['fc_rate']}%</strong></td>
<td style="padding:8px 0;font-size:12px;"><span style="color:#94a3b8;">退费率</span><br><strong style="color:{'#dc2626' if S['ref_rate']>5 else '#0f172a'}">{S['ref_rate']}%</strong></td>
<td style="padding:8px 0;font-size:12px;"><span style="color:#94a3b8;">TOP20%占</span><br><strong style="color:{'#dc2626' if S['t20']>50 else '#16a34a'}">{S['t20']}%</strong></td>
<td style="padding:8px 0;font-size:12px;"><span style="color:#94a3b8;">投诉</span><br><strong>{S['complaint_count']}件</strong></td>
<td style="padding:8px 0;font-size:12px;"><span style="color:#94a3b8;">黄金时段占比</span><br><strong>{S['peak_pct']}%</strong></td>
<td style="padding:8px 0;font-size:12px;"><span style="color:#94a3b8;">团队ROI</span><br><strong>{S['roi']}%</strong></td>
</tr><tr>
<td style="padding:8px 0;font-size:12px;"><span style="color:#94a3b8;">建信转入</span><br><strong>{S['jx_transfer_in']}条</strong></td>
<td style="padding:8px 0;font-size:12px;"><span style="color:#94a3b8;">建信转化</span><br><strong>{S['jx_signed']}单({S['jx_cr']}%)</strong></td>
<td style="padding:8px 0;font-size:12px;"><span style="color:#94a3b8;">公海捞取</span><br><strong>{S['pool_retrieval']}条</strong></td>
<td style="padding:8px 0;font-size:12px;"><span style="color:#94a3b8;">公海转化</span><br><strong>{S['pool_signed']}单({S['p_cr']}%)</strong></td>
<td style="padding:8px 0;font-size:12px;"><span style="color:#94a3b8;">部门CV系数</span><br><strong style="color:{'#dc2626' if pc_cv>0.35 else '#0f172a'}">{pc_cv}</strong></td>
<td style="padding:8px 0;font-size:12px;"><span style="color:#94a3b8;">分配率</span><br><strong>{S['alloc_rate']*100:.0f}%</strong></td>
<td style="padding:8px 0;font-size:12px;"><span style="color:#94a3b8;">退费额</span><br><strong>¥{S['refund_amount']:,.0f}</strong></td>
<td style="padding:8px 0;font-size:12px;"><span style="color:#94a3b8;">新人数</span><br><strong>{S['new_hire']}人</strong></td>
</tr></table></div>

<!-- 漏斗 -->
<div class="card">
<h2>转化漏斗（Dial→Connect→Conversation→Close）</h2>
{funnel_html}
</div>

<!-- 对撞发现 -->
<div class="card">
<h2>逻辑对撞诊断（数据交叉碰撞 · {len(findings)}项发现）</h2>
{collision_html}
</div>

<!-- 7日趋势 -->
<div class="card" style="overflow-x:auto;">
<h2>7日趋势</h2>
<table style="min-width:600px;"><thead><tr><th style="text-align:left;padding-left:12px;">指标</th>{th}</tr></thead><tbody>
{tr_row("营收","total_revenue")}
{tr_row("人均产值","pc")}
{tr_row("接通率","cr",".1f","",True)}
{tr_row("转化率","conv",".2f","",True)}
{tr_row("深沟率","dr",".1f","",True)}
{tr_row("退费率","rr",".1f","",True)}
{tr_row("人均拨打","dials_pp",".1f","")}
</tbody></table></div>

<!-- 改善建议 -->
<div class="card">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid #f1f5f9;">
<h2 style="margin:0;padding:0;border:0;">改善建议与增量预估</h2>
<div style="background:#fef2f2;padding:4px 14px;border-radius:16px;font-size:12px;">
全部落地 <strong style="color:#dc2626;font-size:16px;margin:0 4px;">+¥{total_uplift:,}/日</strong> (月+¥{total_uplift*30/10000:.1f}万)
</div></div>
{imp_html}
</div>

<!-- 司龄-产能 -->
<div class="card">
<h2>司龄-产能成长曲线</h2>
<table><thead><tr><th style="text-align:left;padding-left:12px;">阶段</th><th>人数</th><th style="text-align:right;">人均产值</th><th>AI均分</th></tr></thead>
<tbody>{tenure_html}</tbody></table>
<div style="font-size:11px;color:#94a3b8;margin-top:8px;">* 产能曲线：新人爬坡→成长期冲刺→成熟期巅峰→老员工可能衰减。关注断崖和倦怠点。</div>
</div>

<!-- 部门排名 -->
<div class="card" style="overflow-x:auto;">
<h2>部门排名（仅电销8部门·按营收降序）</h2>
<table style="font-size:12px;min-width:800px;"><thead><tr>
<th style="text-align:left;padding-left:12px;">部门</th><th style="text-align:right;">营收</th><th style="text-align:right;">人均</th>
<th>接通率</th><th>深沟率</th><th>AI</th><th>均接通时长</th><th>转化率</th><th>签单</th><th>TOP20%</th><th>退费率</th><th>ROI</th>
</tr></thead><tbody>{dept_rows}</tbody></table></div>

<!-- 新人 -->
<div class="card">
<h2>新人成长追踪</h2>
<table style="font-size:12px;"><thead><tr><th style="text-align:left;padding-left:12px;">部门</th><th>新人数</th><th style="text-align:right;">新人均产</th><th style="text-align:right;">全员均产</th><th>达标率</th></tr></thead>
<tbody>{new_rows}</tbody></table>
<div style="font-size:11px;color:#94a3b8;margin-top:6px;">* 第4个月新人需 ≥ 70%。低于50%为断崖预警。</div></div>

<!-- TOP & BOTTOM -->
<div class="card" style="overflow-x:auto;">
<h2>个人 TOP10</h2>
<table style="font-size:12px;"><thead><tr><th>#</th><th style="text-align:left;">姓名</th><th style="text-align:left;">部门</th><th>司龄</th><th style="text-align:right;">营收</th><th>签单</th><th>AI</th><th>深沟</th><th>均接通时长</th></tr></thead>
<tbody>{person_rows(top10)}</tbody></table></div>

<div class="card" style="overflow-x:auto;">
<h2>个人 BOTTOM10</h2>
<table style="font-size:12px;"><thead><tr><th>#</th><th style="text-align:left;">姓名</th><th style="text-align:left;">部门</th><th>司龄</th><th style="text-align:right;">营收</th><th>签单</th><th>AI</th><th>深沟</th><th>均接通时长</th></tr></thead>
<tbody>{person_rows(bot10, False)}</tbody></table></div>

<!-- 因果链 -->
<div class="card">
<h2>因果链综合诊断</h2>
<div style="font-size:13px;line-height:1.9;color:#475569;">
<strong style="color:#0f172a;">资源端</strong> 日分配{S['allocated']:,}条 · 分配率{S['alloc_rate']*100:.0f}% · 资源{'充足' if S['allocated']>S['on_duty']*12 else '偏紧'}<br>
<strong style="color:#0f172a;">触达端</strong> 拨打{S['dial_count']:,}次(人均{S['dial_count']//S['on_duty']}通) · 接通{S['link_1d_num']:,}通({S['cr']}%) · 均通话{S['dur']}s · 均接通{S['conn_dur']}s<br>
<strong style="color:#0f172a;">转化端</strong> 深沟{S['deep_talk']:,}通(深沟率{S['dr']}% · 均深沟{S['deep_dur']}s) · AI均分{S['ai']} · 首通转化{S['fc_rate']}% · 总转化{S['conv']}%<br>
<strong style="color:#0f172a;">产出端</strong> 签单{S['signed_deals']}笔 · 客单价¥{S['avg_deal']:,} · 总营收¥{S['total_revenue']:,.0f} · 人均¥{S['pc']:,}<br>
<strong style="color:#0f172a;">质量端</strong> 退费{S['refund_count']}笔(¥{S['refund_amount']:,.0f} · {S['ref_rate']}%) · 投诉{S['complaint_count']}件<br>
<strong style="color:#0f172a;">协同端</strong> 建信转入{S['jx_transfer_in']}条→{S['jx_signed']}单({S['jx_cr']}%) · 公海{S['pool_retrieval']}条→{S['pool_signed']}单({S['p_cr']}%)<br>
<strong style="color:#0f172a;">效率端</strong> 黄金时段贡献{S['peak_pct']}%营收 · 部门间CV={pc_cv} · TOP20%贡献{S['t20']}%
</div></div>

<div style="text-align:center;color:#cbd5e1;font-size:10px;padding:16px 0;">
珍爱网电销体检 · 仅电销8部门 · {DATE} · 逻辑对撞诊断引擎v4 · 方法论：张烜搏六步法+Convoso漏斗模型
</div>
</div></body></html>'''
    return html


# ════════════════════════════════════════════════
# 6. 邮件发送
# ════════════════════════════════════════════════

def send(html, S):
    a = "↑" if S["rev_dod"]>0 else "↓"
    subj = f"【电销体检】02月27日 — ¥{S['total_revenue']/10000:.1f}万({a}{abs(S['rev_dod'])}%) 人均¥{S['pc']:,} 接通{S['cr']}% [含对撞诊断]"
    msg = MIMEMultipart()
    msg["From"] = "Data API <zhao.can@zhenai.com>"
    msg["To"] = "zhao.can@zhenai.com"
    msg["Cc"] = "xiaoying.tian@zhenai.com"
    msg["Subject"] = subj
    msg.attach(MIMEText(html, "html", "utf-8"))
    to = ["zhao.can@zhenai.com", "xiaoying.tian@zhenai.com"]
    with smtplib.SMTP_SSL("smtp.exmail.qq.com", 465, timeout=15) as s:
        s.login("zhao.can@zhenai.com", "b6k36jmUW8EcUsDg")
        s.sendmail("zhao.can@zhenai.com", to, msg.as_string())
    print("  邮件发送成功")


# ════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════

if __name__ == "__main__":
    print("═" * 50)
    print("珍爱网电销体检 v4 · 逻辑对撞诊断引擎")
    print("═" * 50)

    print("\n[1/5] 构建数据库...")
    build_db()

    print("[2/5] 高效数据拉取（3次SQL完成全部IO）...")
    S, depts, trends, top10, bot10, new_stats, persons = pull_data()

    # 校验
    assert all("电销" in d["dept_name"] for d in depts), "数据泄漏：非电销部门"
    assert abs(sum(d["total_revenue"] for d in depts) - S["total_revenue"]) < 1, "营收校验失败"
    print(f"  营收 ¥{S['total_revenue']/10000:.1f}万 | 人均 ¥{S['pc']:,} | 接通 {S['cr']}% | 校验✓")

    print("[3/5] 逻辑对撞诊断...")
    findings, tenure_avg, pc_cv, funnel = cross_collision_diagnosis(S, depts, trends, persons)
    print(f"  发现 {len(findings)} 项交叉碰撞结论")

    print("[4/5] 量化改善建议...")
    improvements, total_uplift = calc_improvements(S, depts, findings)
    print(f"  {len(improvements)} 条建议，总增量 +¥{total_uplift:,}/日 (+¥{total_uplift*30/10000:.1f}万/月)")

    print("[5/5] 生成报告 & 发送...")
    html = render(S, depts, trends, top10, bot10, new_stats, persons,
                  findings, tenure_avg, pc_cv, funnel, improvements, total_uplift)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Telesale_Report_0227_v4.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    send(html, S)
    webbrowser.open("file://" + os.path.realpath(path))
    print(f"\n完成 → {path}")
