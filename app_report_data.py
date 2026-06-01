# -*- coding: utf-8 -*-
"""APP日报 — 数据聚合模块（3张表全量字段解析）"""
from collections import defaultdict
from agent_system.actions.api_client import safe_float, safe_int

PRODUCTS = [
    ("zhenxin_member",    "珍心会员",   "#dc2626", "核心付费产品"),
    ("super_member_full", "超级会员全", "#d97706", "高价值产品"),
    ("live_guard",        "直播守护",   "#7c3aed", "互动付费"),
    ("super_member_plus", "超级会员+",  "#2563eb", "中级会员"),
    ("zhenai_coin",       "珍爱币",     "#16a34a", "虚拟货币"),
    ("super_remind",      "超级提醒",   "#d97706", "功能付费"),
    ("star_privilege",    "星光特权",   "#6366f1", "特权产品"),
    ("super_recommend",   "超级推荐",   "#0891b2", "推荐算法付费"),
    ("other",             "其他",       "#94a3b8", "其他产品"),
]

BOOK_REFS = {
    "HOOKED": "《Hooked》Nir Eyal",
    "GROWTH": "《增长黑客》Sean Ellis",
    "NSFOCUS": "《硅谷增长黑客实战笔记》曲卉",
    "RETENTION": "《用户增长方法论》范冰",
    "REVENUE": "《订阅经济》Tien Tzuo",
    "UX": "《用户体验要素》Jesse Garrett",
    "LEAN": "《精益数据分析》Alistair Croll",
    "PLATSCALE": "《平台革命》Parker",
}

APP_METRIC_LABELS = {
    "total_rev": "日营收",
    "pay_num": "付费人数",
    "active": "DAU",
    "arpu": "ARPU",
    "pay_rate": "付费率%",
    "refund": "退款金额",
    "refund_rate": "退款率%",
    "retain_rate_1d": "次日留存率%",
    "fugou_amt": "复购金额",
    "fugou_pct": "复购占比%",
    "order_conv": "订单支付率%",
    "live_rev": "直播营收",
    "anchmems": "开播主播数",
    "giftmems": "送礼人数",
    "amt_m": "月累营收",
    "new_pay": "新增付费",
    "costmoney": "直播消费金额",
    "regnew_mems_total": "新注册会员",
    "trial_cnt": "试用订单数",
    "trial_amt": "试用金额",
}


def parse_rows(resp):
    return resp.get("rows", []) if isinstance(resp, dict) else []


def agg_app(rows):
    """聚合daily表（51字段），返回全量指标字典"""
    if not rows:
        return {}
    r = rows[0]
    total_rev = safe_float(r.get("amt"))
    pay_num = safe_int(r.get("pay_num"))
    active = safe_int(r.get("active_members"))
    refund = safe_float(r.get("refund_money"))
    new_pay = safe_int(r.get("pay_num_new"))
    order_cnt = safe_int(r.get("order_cnt"))
    order_pay = safe_int(r.get("order_pay"))
    order_num = safe_int(r.get("order_num"))
    mems = safe_int(r.get("mems"))
    fugou_amt = safe_float(r.get("fugou_amt"))
    pay_amt = safe_float(r.get("pay_amt"))

    anchmems = safe_int(r.get("anchmems"))
    anchtime = safe_int(r.get("anchtime"))
    giftmems = safe_int(r.get("giftmems"))
    costmoney = safe_float(r.get("costmoney"))
    live_guard = safe_float(r.get("live_guard"))

    link_1d = safe_int(r.get("link_1d_num"))
    callout_1d = safe_int(r.get("callout_1d_num"))
    leads_offline = safe_int(r.get("leads_offline"))
    leads_online = safe_int(r.get("leads_online"))
    allot = safe_int(r.get("allot"))
    laoqu = safe_int(r.get("laoqu"))

    reg_m = safe_int(r.get("reg_num_m"))
    pay_m = safe_int(r.get("pay_num_m"))
    amt_m = safe_float(r.get("pay_amt_m"))
    pay_m_cut = safe_int(r.get("pay_num_m_cut"))
    amt_m_cut = safe_float(r.get("pay_amt_m_cut"))
    pay_d_lj = safe_int(r.get("pay_d_lj_mems"))
    amt_m_online1 = safe_float(r.get("amt_pay_m_online1"))
    last_consume_d = safe_float(r.get("last_consumeonday_d"))
    last_consume_m = safe_float(r.get("last_consumeonday_m"))

    retain = {}
    for d in [1, 2, 3, 4, 5, 6, 7, 15, 30]:
        retain[d] = safe_int(r.get(f"retain_{d}d"))

    prod_vals = {k: safe_float(r.get(k)) for k, _, _, _ in PRODUCTS}
    prod_total = sum(prod_vals.values()) or 1
    zhenxin = safe_float(r.get("zhenxin_member"))

    arpu = total_rev / pay_num if pay_num > 0 else 0
    pay_rate = pay_num / active * 100 if active > 0 else 0
    refund_rate = refund / total_rev * 100 if total_rev > 0 else 0
    zhenxin_pct = zhenxin / total_rev * 100 if total_rev > 0 else 0
    retain_rate_1d = retain[1] / mems * 100 if mems > 0 else 0
    retain_rate_7d = retain[7] / mems * 100 if mems > 0 else 0
    order_conv = order_pay / order_cnt * 100 if order_cnt > 0 else 0
    order_fail = order_cnt - order_pay
    order_fail_rate = order_fail / order_cnt * 100 if order_cnt > 0 else 0
    fugou_pct = fugou_amt / total_rev * 100 if total_rev > 0 else 0
    new_rev = total_rev - fugou_amt
    avg_anchtime = anchtime / anchmems if anchmems > 0 else 0
    gift_per_viewer = costmoney / giftmems if giftmems > 0 else 0
    live_rev = safe_float(r.get("live_guard")) + safe_float(r.get("zhenai_coin"))

    return dict(
        total_rev=total_rev, pay_num=pay_num, active=active,
        refund=refund, new_pay=new_pay, order_cnt=order_cnt,
        order_pay=order_pay, order_num=order_num, mems=mems,
        fugou_amt=fugou_amt, pay_amt=pay_amt, zhenxin=zhenxin,
        anchmems=anchmems, anchtime=anchtime, giftmems=giftmems,
        costmoney=costmoney, live_guard=live_guard,
        link_1d=link_1d, callout_1d=callout_1d,
        leads_offline=leads_offline, leads_online=leads_online,
        allot=allot, laoqu=laoqu,
        reg_m=reg_m, pay_m=pay_m, amt_m=amt_m,
        pay_m_cut=pay_m_cut, amt_m_cut=amt_m_cut,
        pay_d_lj=pay_d_lj, amt_m_online1=amt_m_online1,
        last_consume_d=last_consume_d, last_consume_m=last_consume_m,
        retain=retain, prod_vals=prod_vals, prod_total=prod_total,
        arpu=arpu, pay_rate=pay_rate, refund_rate=refund_rate,
        zhenxin_pct=zhenxin_pct,
        retain_rate_1d=retain_rate_1d, retain_rate_7d=retain_rate_7d,
        order_conv=order_conv, order_fail=order_fail,
        order_fail_rate=order_fail_rate,
        fugou_pct=fugou_pct, new_rev=new_rev,
        avg_anchtime=avg_anchtime, gift_per_viewer=gift_per_viewer,
        live_rev=live_rev,
    )


def agg_orders(rows):
    """聚合orders表，返回多维度分组数据"""
    def _bucket():
        return {"cnt": 0, "pay": 0, "amt": 0, "pay_num": 0}

    by_entrance1 = defaultdict(_bucket)
    by_entrance2 = defaultdict(_bucket)
    by_channel = defaultdict(_bucket)
    by_platform = defaultdict(_bucket)
    by_product = defaultdict(_bucket)
    by_utype = defaultdict(_bucket)
    by_live_e2 = defaultdict(_bucket)
    by_live_prod = defaultdict(_bucket)
    by_version = defaultdict(_bucket)
    by_callback = defaultdict(_bucket)
    by_entrance3 = defaultdict(_bucket)
    by_prodname = defaultdict(_bucket)
    by_channelname2 = defaultdict(_bucket)
    by_trial = defaultdict(_bucket)

    for row in rows:
        cnt = safe_int(row.get("order_cnt"))
        pay = safe_int(row.get("order_pay"))
        amt = safe_float(row.get("amt"))
        pn = safe_int(row.get("pay_num"))

        def _add(d, key):
            d[key]["cnt"] += cnt
            d[key]["pay"] += pay
            d[key]["amt"] += amt
            d[key]["pay_num"] += pn

        e1 = row.get("entrance1", "未知")
        _add(by_entrance1, e1)
        _add(by_entrance2, row.get("entrance2", "未知"))
        _add(by_channel, row.get("channelname", "未知"))
        _add(by_platform, row.get("platformname", "未知"))
        _add(by_product, row.get("producttype", "未知"))
        _add(by_utype, row.get("user_type", "未知"))
        _add(by_version, row.get("app_version", "未知"))
        _add(by_callback, str(row.get("iscallback", "")))
        _add(by_entrance3, row.get("entrance3", "未知"))
        _add(by_prodname, row.get("productfullname", "未知"))
        _add(by_channelname2, row.get("channelname2", "未知"))
        _add(by_trial, row.get("is_trial", "未知"))

        if e1 == "直播":
            _add(by_live_e2, row.get("entrance2", "未知"))
            _add(by_live_prod, row.get("producttype", "未知"))

    def _sorted(d):
        return sorted(d.items(), key=lambda x: x[1]["amt"], reverse=True)

    return dict(
        by_entrance1=_sorted(by_entrance1),
        by_entrance2=_sorted(by_entrance2),
        by_channel=_sorted(by_channel),
        by_platform=_sorted(by_platform),
        by_product=_sorted(by_product),
        by_utype=_sorted(by_utype),
        by_live_e2=_sorted(by_live_e2),
        by_live_prod=_sorted(by_live_prod),
        by_version=_sorted(by_version),
        by_callback=_sorted(by_callback),
        by_entrance3=_sorted(by_entrance3),
        by_prodname=_sorted(by_prodname),
        by_channelname2=_sorted(by_channelname2),
        by_trial=_sorted(by_trial),
        total_cnt=sum(v["cnt"] for v in by_entrance1.values()),
        total_pay=sum(v["pay"] for v in by_entrance1.values()),
        total_amt=sum(v["amt"] for v in by_entrance1.values()),
        trial_cnt=sum(v["cnt"] for v in by_trial.values() if True),
    )


def agg_traffic(rows):
    """聚合traffic表，返回渠道ROI数据"""
    _ch_init = lambda: {
        "reg": 0, "pay": 0, "amt_d": 0, "amt_m": 0,
        "cost": 0, "valid": 0, "lj_mems": 0, "regnew": 0
    }
    by_parent = defaultdict(_ch_init)
    by_sub = defaultdict(_ch_init)
    for row in rows:
        p = row.get("parent_name", "未知")
        s = row.get("parents", "未知")
        for d in (by_parent[p], by_sub[s]):
            d["reg"] += safe_int(row.get("regnum"))
            d["pay"] += safe_int(row.get("num_pay_online_d"))
            d["amt_d"] += safe_float(row.get("amt_pay_d_online"))
            d["amt_m"] += safe_float(row.get("amt_pay_m_online1"))
            d["cost"] += safe_float(row.get("real_cost"))
            d["valid"] += safe_int(row.get("validnum"))
            d["lj_mems"] += safe_int(row.get("pay_d_lj_mems"))
            d["regnew"] += safe_int(row.get("regnew_mems"))

    channels = []
    for name, v in sorted(by_parent.items(), key=lambda x: x[1]["amt_d"], reverse=True):
        roi = v["amt_d"] / v["cost"] if v["cost"] > 0 else 0
        pay_rate = v["pay"] / v["reg"] * 100 if v["reg"] > 0 else 0
        cpa = v["cost"] / v["reg"] if v["reg"] > 0 else 0
        channels.append(dict(
            name=name, **v, roi=roi, pay_rate=pay_rate, cpa=cpa
        ))

    sub_channels = []
    for name, v in sorted(by_sub.items(), key=lambda x: x[1]["amt_d"], reverse=True):
        roi = v["amt_d"] / v["cost"] if v["cost"] > 0 else 0
        pay_rate = v["pay"] / v["reg"] * 100 if v["reg"] > 0 else 0
        cpa = v["cost"] / v["reg"] if v["reg"] > 0 else 0
        sub_channels.append(dict(name=name, **v, roi=roi, pay_rate=pay_rate, cpa=cpa))

    total_cost = sum(v["cost"] for v in by_parent.values())
    total_reg = sum(v["reg"] for v in by_parent.values())
    total_pay = sum(v["pay"] for v in by_parent.values())
    total_amt_d = sum(v["amt_d"] for v in by_parent.values())
    total_amt_m = sum(v["amt_m"] for v in by_parent.values())
    total_regnew = sum(v["regnew"] for v in by_parent.values())
    overall_roi = total_amt_d / total_cost if total_cost > 0 else 0

    return dict(
        channels=channels, sub_channels=sub_channels,
        total_cost=total_cost, total_reg=total_reg,
        total_pay=total_pay, total_amt_d=total_amt_d,
        total_amt_m=total_amt_m, total_regnew=total_regnew,
        overall_roi=overall_roi,
    )


def build_trend_data(trend_rows):
    """多天daily数据聚合为趋势"""
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
        for k in ("amt", "pay_num", "active_members", "refund_money",
                   "retain_1d", "retain_7d", "mems", "order_cnt",
                   "order_pay", "anchmems", "giftmems", "fugou_amt"):
            t[k] = sum(safe_float(r.get(k)) for r in rows)
        t["arpu"] = t["amt"] / t["pay_num"] if t["pay_num"] > 0 else 0
        t["pay_rate"] = (t["pay_num"] / t["active_members"] * 100
                         if t["active_members"] > 0 else 0)
        t["refund_rate"] = (t["refund_money"] / t["amt"] * 100
                            if t["amt"] > 0 else 0)
        t["retain_rate_1d"] = (t["retain_1d"] / t["mems"] * 100
                               if t["mems"] > 0 else 0)
        t["retain_rate_7d"] = (t["retain_7d"] / t["mems"] * 100
                               if t["mems"] > 0 else 0)
        t["fugou_pct"] = (t["fugou_amt"] / t["amt"] * 100
                          if t["amt"] > 0 else 0)
        t["order_conv"] = (t["order_pay"] / t["order_cnt"] * 100
                           if t["order_cnt"] > 0 else 0)
        result.append(t)
    return result
