"""
分析管道 - 将数据对撞和逻辑对撞组装为完整分析流程
Analysis Pipeline

强制规则:
1. 每次分析必须同时执行数据对撞和逻辑对撞
2. 数据对撞至少5组，覆盖3种对撞类型
3. 逻辑对撞至少3组假设对撞链
4. 所有发现必须量化影响+标注优先级+给出建议
"""

import sqlite3
import os
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from agent_system.engines.collision_engine import (
    DataCollisionEngine,
    LogicCollisionEngine,
    CrossDomainCollisionEngine,
    CollisionFinding,
    validate_feasibility,
)


@dataclass
class AnalysisReport:
    """分析报告结构"""
    date: str
    summary: dict
    departments: list
    trends: list
    persons: list
    top_performers: list
    bottom_performers: list
    new_hire_stats: list
    tenure_analysis: dict

    data_collision_findings: list
    data_collision_summary: dict
    logic_collision_findings: list
    logic_collision_summary: dict
    cross_domain_findings: list = field(default_factory=list)
    cross_domain_summary: dict = field(default_factory=dict)
    hypotheses: list = field(default_factory=list)
    causal_chains: list = field(default_factory=list)

    all_findings: list = field(default_factory=list)
    improvements: list = field(default_factory=list)
    total_uplift: float = 0

    funnel: list = field(default_factory=list)
    pc_cv: float = 0

    def get_all_findings_sorted(self):
        """按优先级排序所有发现(三引擎合并)"""
        priority_order = {"P0": 0, "P1": 1, "P2": 2}
        all_f = (self.data_collision_findings +
                 self.logic_collision_findings +
                 self.cross_domain_findings)
        return sorted(all_f, key=lambda f: (priority_order.get(f.priority, 9), -f.revenue_impact))


class AnalysisPipeline:
    """
    分析管道 - 数据专家核心分析流程

    流程:
    1. 数据拉取 → 2. 数据对撞 → 3. 逻辑对撞 → 4. 量化改善建议 → 5. 组装报告

    每次分析严格执行:
    - 数据对撞: 12种对撞模型(至少触发5种)
    - 逻辑对撞: 假设验证+因果链+规律例外+多视角
    """

    def __init__(self, db_path: str, dept_managers: dict = None):
        self.db_path = db_path
        self.dept_managers = dept_managers or {}
        self.data_engine = DataCollisionEngine()
        self.logic_engine = LogicCollisionEngine()
        self.cross_domain_engine = CrossDomainCollisionEngine()

    def run(self, date: str, dates_range: Optional[list] = None) -> AnalysisReport:
        """执行完整分析流程"""
        if dates_range is None:
            d = int(date[-2:])
            dates_range = [f"{date[:-2]}{i:02d}" for i in range(max(1, d - 9), d + 1)]

        S, depts, trends, top10, bot10, new_stats, persons = self._pull_data(date, dates_range)
        tenure_avg = self._compute_tenure_analysis(persons)

        data_findings = self.data_engine.execute(S, depts, trends, persons,
                                                    dept_managers=self.dept_managers)

        pcs = [d["per_capita_revenue"] for d in depts]
        pc_cv = round(statistics.stdev(pcs) / (statistics.mean(pcs) or 1), 2) if len(pcs) > 1 else 0

        funnel = [
            ("分配→拨打", S["dial_count"] / (S["allocated"] or 1), 3.0, "拨打倍率"),
            ("拨打→接通", S["link_1d_num"] / (S["dial_count"] or 1) * 100, 15, "接通/拨打%"),
            ("接通→深沟", S["deep_talk"] / (S["link_1d_num"] or 1) * 100, 20, "深沟/接通%"),
            ("深沟→签单", S["signed_deals"] / (S["deep_talk"] or 1) * 100, 10, "签单/深沟%"),
        ]

        logic_findings, hypotheses, causal_chains = self.logic_engine.execute(
            S, depts, trends, persons, data_findings)

        cross_domain_findings = self.cross_domain_engine.execute(
            S, depts, data_findings, logic_findings)

        all_findings = data_findings + logic_findings + cross_domain_findings
        improvements, total_uplift = self._calc_improvements(S, depts, data_findings)

        report = AnalysisReport(
            date=date,
            summary=S,
            departments=depts,
            trends=trends,
            persons=persons,
            top_performers=top10,
            bottom_performers=bot10,
            new_hire_stats=new_stats,
            tenure_analysis=tenure_avg,
            data_collision_findings=data_findings,
            data_collision_summary=self.data_engine.get_summary(),
            logic_collision_findings=logic_findings,
            logic_collision_summary=self.logic_engine.get_summary(),
            cross_domain_findings=cross_domain_findings,
            cross_domain_summary=self.cross_domain_engine.get_summary(),
            hypotheses=hypotheses,
            causal_chains=causal_chains,
            all_findings=all_findings,
            improvements=improvements,
            total_uplift=total_uplift,
            funnel=funnel,
            pc_cv=pc_cv
        )

        return report

    def _pull_data(self, date, dates_range):
        """从数据库拉取所有数据(3次SQL完成全部IO)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        depts = [dict(r) for r in conn.execute(
            "SELECT * FROM ts_daily WHERE report_date=? ORDER BY total_revenue DESC",
            (date,))]

        all_rows = [dict(r) for r in conn.execute(
            "SELECT * FROM ts_daily ORDER BY report_date, dept_name")]

        persons = [dict(r) for r in conn.execute(
            "SELECT * FROM ts_person WHERE report_date=? ORDER BY revenue DESC",
            (date,))]

        conn.close()

        S = self._aggregate_summary(depts, date)
        trends = self._aggregate_trends(all_rows)

        if len(trends) >= 2:
            y, p = trends[-1], trends[-2]
            S["rev_dod"] = round((y["total_revenue"] - p["total_revenue"]) /
                                 (p["total_revenue"] or 1) * 100, 1)
            S["cr_dod"] = round(y["cr"] - p["cr"], 1)
            S["pc_dod"] = round((y["pc"] - p["pc"]) / (p["pc"] or 1) * 100, 1)
        else:
            S["rev_dod"] = S["cr_dod"] = S["pc_dod"] = 0

        S["week_avg_rev"] = round(sum(t["total_revenue"] for t in trends) / max(len(trends), 1))

        top10 = persons[:10]
        bot10 = persons[-10:]
        new_stats = [{"dept_name": d["dept_name"], "new_hire": d["new_hire"],
                      "new_avg": d["new_hire_month_avg"], "pc": d["per_capita_revenue"]}
                     for d in depts]

        return S, depts, trends, top10, bot10, new_stats, persons

    def _aggregate_summary(self, depts, date):
        """聚合当日大盘数据"""
        sum_keys = ["head_count", "on_duty", "new_hire", "allocated", "dial_count",
                     "link_1d_num", "deep_talk", "first_call_conv", "signed_deals",
                     "total_revenue", "refund_count", "refund_amount", "complaint_count",
                     "jx_transfer_in", "jx_signed", "pool_in", "pool_retrieval",
                     "pool_signed", "peak_hour_revenue", "offpeak_hour_revenue"]
        S = {"date": date}
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
        S["alloc_rate"] = round(sum(d["alloc_rate"] for d in depts) / max(len(depts), 1), 3)

        return S

    def _aggregate_trends(self, all_rows):
        """聚合7日趋势"""
        by_date = defaultdict(list)
        for r in all_rows:
            by_date[r["report_date"]].append(r)

        trends = []
        for dt in sorted(by_date):
            rows = by_date[dt]
            t = {"dt": dt}
            for k in ["allocated", "link_1d_num", "deep_talk", "signed_deals",
                       "total_revenue", "on_duty", "refund_amount", "dial_count"]:
                t[k] = sum(r[k] for r in rows)
            t["cr"] = round(t["link_1d_num"] / (t["allocated"] or 1) * 100, 1)
            t["pc"] = round(t["total_revenue"] / (t["on_duty"] or 1))
            t["conv"] = round(t["signed_deals"] / (t["allocated"] or 1) * 100, 2)
            t["dr"] = round(t["deep_talk"] / (t["link_1d_num"] or 1) * 100, 1)
            t["rr"] = round(t["refund_amount"] / (t["total_revenue"] or 1) * 100, 1)
            t["dials_pp"] = round(t["dial_count"] / (t["on_duty"] or 1), 1)
            trends.append(t)

        return trends

    def _compute_tenure_analysis(self, persons):
        """计算司龄-产能分析"""
        buckets = defaultdict(list)
        for p in persons:
            tm = p["tenure_months"]
            if tm <= 3:
                buckets["新人(≤3月)"].append(p)
            elif tm <= 12:
                buckets["成长期(4-12月)"].append(p)
            elif tm <= 24:
                buckets["成熟期(1-2年)"].append(p)
            else:
                buckets["老员工(>2年)"].append(p)

        result = {}
        for bucket, ps in buckets.items():
            if not ps:
                continue
            result[bucket] = {
                "count": len(ps),
                "avg_rev": round(sum(p["revenue"] for p in ps) / len(ps)),
                "avg_ai": round(sum(p["ai_score"] for p in ps) / len(ps), 1),
                "avg_dials": round(sum(p["dial_count"] for p in ps) / len(ps))
            }
        return result

    def _calc_improvements(self, S, depts, findings):
        """计算量化改善建议(含时间维度执行指令)"""
        items = []
        avg_d = S["avg_deal"]
        from datetime import datetime, timedelta
        tomorrow = (datetime.strptime(S["date"], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

        if S["cr"] < 43:
            gap = 43 - S["cr"]
            extra = int(S["allocated"] * gap / 100)
            rev = round(extra * S["conv"] / 100 * avg_d)
            items.append({
                "p": "P0", "title": "接通率修复至43%",
                "cur": f"{S['cr']}%", "tgt": "43%",
                "act": "排查号码标记+优化外呼时段(10:00-11:30/14:00-16:00黄金窗口)",
                "detail": f"增加有效接通{extra}通→多签{round(extra * S['conv'] / 100)}单",
                "rev": rev,
                "refs": ["T18:外呼营销实战-接通率", "T22:电销新思维-AI外呼"],
                "deploy_date": tomorrow,
                "target_entity": "全部门(接通率<43%的部门重点)",
                "daily_action": "每日排查号码标记比例+线路轮换检查+外呼时段数据复盘",
                "duration_days": 7,
                "milestone": "第3天检查改善趋势，第7天验收是否达标",
            })

        if S.get("t20", 0) > 50:
            best = max(depts, key=lambda d: d["per_capita_revenue"])
            worst = min(depts, key=lambda d: d["per_capita_revenue"])
            gap_pc = best["per_capita_revenue"] - worst["per_capita_revenue"]
            bot_n = int(S["on_duty"] * 0.5)
            rev = round(bot_n * gap_pc * 0.2)
            worst_mgr = self.dept_managers.get(worst["dept_name"], "")
            items.append({
                "p": "P1", "title": "中腰部标杆复制",
                "cur": f"TOP20%占{S['t20']}%", "tgt": "<=50%",
                "act": f"提取{best['dept_name']}标杆录音→{worst['dept_name']}"
                       f"{'(' + worst_mgr + ')' if worst_mgr else ''}话术通关",
                "detail": f"后50%({bot_n}人)人均提升¥{round(gap_pc * 0.2):,}",
                "rev": rev,
                "refs": ["T06:可复制的销售力", "T08:通关培训体系"],
                "deploy_date": tomorrow,
                "target_entity": f"中腰部员工(后50%约{bot_n}人)，重点{worst['dept_name']}",
                "daily_action": "每日晨会播放1条标杆录音+午间话术通关测试1轮",
                "duration_days": 14,
                "milestone": "第7天中期检查通关率，第14天验收人均产值变化",
            })

        best_dr = max(d["deep_talk_rate"] for d in depts) if depts else 0
        if S["dr"] < best_dr - 2:
            gap = best_dr - S["dr"]
            extra_d = int(S["link_1d_num"] * gap / 100)
            rev = round(extra_d * 0.12 * avg_d)
            items.append({
                "p": "P1", "title": "深沟率向标杆看齐",
                "cur": f"{S['dr']}%", "tgt": f"{best_dr}%",
                "act": "梳理'痛点→解决方案→紧迫感'三段式深沟SOP",
                "detail": f"深沟率+{gap:.1f}pp→多深沟{extra_d}通→按12%签单率",
                "rev": rev,
                "refs": ["S01:SPIN Selling", "T13:深度销售"],
                "deploy_date": tomorrow,
                "target_entity": "深沟率低于均值的部门全员",
                "daily_action": "每日抽查3通深沟录音→评估是否按SOP推进→反馈改善",
                "duration_days": 10,
                "milestone": "第5天检查深沟率变化，第10天验收",
            })

        if S["ai"] < 75:
            gap = 75 - S["ai"]
            extra_s = round(S["allocated"] * gap * 0.0003, 1)
            rev = round(extra_s * avg_d)
            items.append({
                "p": "P2", "title": "AI Score提升至75",
                "cur": f"{S['ai']}", "tgt": "75",
                "act": "ai_score<65员工每周话术训练营+录音回听AI评分闭环",
                "detail": f"每+1分约转化率+0.03pp，+{gap:.1f}分→多签{extra_s:.0f}单",
                "rev": rev,
                "refs": ["T22:电销新思维-AI质检"],
                "deploy_date": tomorrow,
                "target_entity": "AI评分<65的员工(约占30%)",
                "daily_action": "每日1小时话术训练+AI模拟通关，主管录音回听点评",
                "duration_days": 21,
                "milestone": "每周五检测AI评分变化，连续3周无提升调整培训方案",
            })

        if S["ref_rate"] > 5:
            save = round(S["total_revenue"] * (S["ref_rate"] - 4.5) / 100)
            items.append({
                "p": "P1", "title": "退费率管控至4.5%",
                "cur": f"{S['ref_rate']}%", "tgt": "4.5%",
                "act": "签单后48h回访确认+过度承诺黑名单机制",
                "detail": f"从{S['ref_rate']}%→4.5%，日净止血",
                "rev": save,
                "refs": ["S15:客户成功-LTV管理", "T10:极致服务"],
                "deploy_date": tomorrow,
                "target_entity": "退费率>6%的部门+月退费>2笔的个人",
                "daily_action": "每日质检抽查2条成交录音是否有过度承诺+48h新签客户回访",
                "duration_days": 30,
                "milestone": "每周统计退费率变化，连续2周>6%启动个人辅导期",
            })

        if S["jx_cr"] < 18:
            extra = int(S["jx_transfer_in"] * (18 - S["jx_cr"]) / 100)
            rev = round(extra * avg_d)
            items.append({
                "p": "P2", "title": "建信调配转化率→18%",
                "cur": f"{S['jx_cr']}%", "tgt": "18%",
                "act": "CRM强制附带画像标签+核心抗拒点+双算机制",
                "detail": f"日转入{S['jx_transfer_in']}条→多签{extra}单",
                "rev": rev,
                "refs": ["S05:预测收入-SDR/BDR", "L08:关键对话"],
                "deploy_date": tomorrow,
                "target_entity": "建信→电销交接环节全员",
                "daily_action": "每笔调配资源强制录入画像标签+3分钟预热电话",
                "duration_days": 14,
                "milestone": "第7天检查转化率变化，第14天评估双算机制效果",
            })

        if S["p_cr"] < 12:
            extra = max(1, int(S["pool_retrieval"] * (12 - S["p_cr"]) / 100))
            rev = round(extra * avg_d)
            items.append({
                "p": "P2", "title": "公海捞取转化→12%",
                "cur": f"{S['p_cr']}%", "tgt": "12%",
                "act": "AI外呼预筛+历史行为精准分类+缩短沉淀周期至15天",
                "detail": f"日捞取{S['pool_retrieval']}条→多签{extra}单",
                "rev": rev,
                "refs": ["T22:电销新思维-AI外呼", "A13:数据驱动增长"],
                "deploy_date": tomorrow,
                "target_entity": "公海资源管理+各部门捞取人员",
                "daily_action": "每日AI外呼清洗→意向分级→精准分配到部门→跟进反馈",
                "duration_days": 14,
                "milestone": "第7天检查捞取转化率，第14天评估AI预筛准确率",
            })

        for f in findings:
            if f.priority in ("P0", "P1") and f.revenue_impact > 0:
                target = f"{f.dept_name}({'管理者:' + f.manager_name if f.manager_name else ''})" if f.dept_name else "相关部门"
                items.append({
                    "p": f.priority,
                    "title": f"[对撞] {f.tag}",
                    "cur": "-", "tgt": "修复",
                    "act": f.description[:150],
                    "detail": "基于数据×逻辑双对撞发现",
                    "rev": f.revenue_impact,
                    "refs": f.knowledge_refs,
                    "deploy_date": tomorrow,
                    "target_entity": target,
                    "daily_action": f.recommendations[0] if f.recommendations else "按对撞建议执行",
                    "duration_days": 7,
                    "milestone": "第3天检查数据变化，第7天验收",
                })

        for item in items:
            fv = validate_feasibility(item)
            item["feasibility"] = fv["feasibility"]
            item["dependency"] = fv["dependency"]
            item["risk_notes"] = fv["risk_notes"]

        total = sum(i["rev"] for i in items)
        return items, total
