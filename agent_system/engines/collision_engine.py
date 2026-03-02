"""
三引擎对撞系统 — 数据对撞 + 逻辑对撞 + 跨领域对撞
Data Collision Engine + Logic Collision Engine + Cross-Domain Collision Engine

数据对撞：多维数据交叉碰撞，发现隐性关联和矛盾
逻辑对撞：假设验证与因果推断，揭示业务因果链
跨领域对撞：8大领域×108本书的理论交叉碰撞，输出跨领域洞察

规则：每次分析必须同时执行三种对撞方法
"""

import json
import os
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


MANAGEMENT_GAP_RULES = {
    "low_connect": "该管理者可能缺乏对号码健康度和外呼时段的精细化管理意识，未及时排查号码标记和线路轮换",
    "high_connect_low_dur": "该管理者可能忽视了开场白训练，团队能接通但留不住客户，缺少'价值钩子'设计",
    "high_deep_low_ai": "该管理者可能忽视了话术结构化训练，团队在闲聊而非按SPIN框架推进转化",
    "low_deep_high_ai": "该管理者可能默许了'挑客'文化，高手只服务优质客户，潜在客户被放弃",
    "high_top20": "该管理者可能缺乏中腰部差异化辅导策略，过度依赖TOP员工而非系统化复制能力",
    "high_refund": "该管理者可能对签单话术合规性监管不足，团队存在过度承诺倾向",
    "low_quality_ratio": "该管理者可能只追拨打量不追质量，团队在'刷量'而非做有效会话",
    "peak_imbalance": "该管理者可能缺乏非高峰时段的工作安排规划，大量工时被浪费",
    "jx_low_conv": "该管理者可能对建信调配资源重视不足，未建立有效的信任传递机制",
    "high_activity_low_rev": "该管理者可能只关注活动量指标而忽视转化质量，需从'追量'转向'追效'",
    "persistent_no_improve": "该管理者已连续多日未采取有效管理动作改善问题指标，执行力或管理意识存在严重缺失",
}


@dataclass
class CollisionFinding:
    """对撞发现"""
    collision_type: str       # 对撞类型
    tag: str                  # 标签
    description: str          # 描述
    revenue_impact: float     # 营收影响(元/日)
    priority: str             # P0/P1/P2
    evidence: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)
    knowledge_refs: list = field(default_factory=list)
    scope: str = "global"     # "global" | "dept"
    dept_name: str = ""       # 部门名(scope=dept时)
    manager_name: str = ""    # 部门经理姓名
    management_gap: str = ""  # 管理视角缺失推断

    def to_dict(self):
        d = {
            "collision_type": self.collision_type,
            "tag": self.tag,
            "description": self.description,
            "revenue_impact": self.revenue_impact,
            "priority": self.priority,
            "evidence": self.evidence,
            "recommendations": self.recommendations,
            "knowledge_refs": self.knowledge_refs,
            "scope": self.scope,
            "dept_name": self.dept_name,
        }
        if self.manager_name:
            d["manager_name"] = self.manager_name
            d["management_gap"] = self.management_gap
        return d


class DataCollisionEngine:
    """
    数据对撞引擎

    核心方法论(来源: 185本知识库融合):
    - 指标×指标: 接通率×通话时长, 深沟率×AI评分, 签单×退费 等
    - 指标×时间: 日数据×7日均线, 峰值×非峰值
    - 指标×实体: 部门间差异, 司龄×产能
    - 实体×实体: 建信×电销, 新人×老人
    - 漏斗×标杆: 实际漏斗vs行业/历史标杆

    规则: 每次分析最少执行5组数据对撞, 覆盖至少3种对撞类型
    """

    def __init__(self):
        self._load_rules()
        self.findings: list[CollisionFinding] = []
        self.collision_count = 0
        self.collision_types_used = set()
        self.dept_managers: dict = {}

    def _load_rules(self):
        rules_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "knowledge_base", "frameworks", "data_collision_rules.json"
        )
        if os.path.exists(rules_path):
            with open(rules_path, "r", encoding="utf-8") as f:
                self.rules = json.load(f)
            self.benchmarks = self.rules.get("benchmarks", {}).get("telemarketing", {})
        else:
            self.rules = {}
            self.benchmarks = {}

    def _bm(self, key, level="warning"):
        b = self.benchmarks.get(key, {})
        return b.get(level, 0)

    def execute(self, summary, depts, trends, persons, dept_managers=None):
        """执行全部数据对撞分析"""
        self.findings = []
        self.collision_count = 0
        self.collision_types_used = set()
        self.dept_managers = dept_managers or {}

        self._collide_connect_rate_x_duration(depts)
        self._collide_deep_talk_x_ai_score(depts)
        self._collide_tenure_x_productivity(summary, persons)
        self._collide_activity_x_quality(depts)
        self._collide_peak_x_offpeak(depts)
        self._collide_signed_x_refund(depts)
        self._collide_dept_variance(summary, depts)
        self._collide_jx_x_own_conversion(depts)
        self._collide_funnel_x_benchmark(summary)
        self._collide_trend_x_volatility(trends)
        self._collide_new_hire_x_overall(summary, persons)
        self._collide_dials_x_connects_x_revenue(depts)
        self._collide_persistence_detection(depts, trends)

        self._validate_rules()

        return self.findings

    def _add_finding(self, collision_type, tag, description, revenue_impact,
                     priority, evidence=None, recs=None, refs=None,
                     scope="global", dept_name="", gap_key=""):
        mgr = self.dept_managers.get(dept_name, "") if dept_name else ""
        gap = MANAGEMENT_GAP_RULES.get(gap_key, "") if gap_key and mgr else ""
        self.findings.append(CollisionFinding(
            collision_type=collision_type,
            tag=tag,
            description=description,
            revenue_impact=revenue_impact,
            priority=priority,
            evidence=evidence or [],
            recommendations=recs or [],
            knowledge_refs=refs or [],
            scope=scope,
            dept_name=dept_name,
            manager_name=mgr,
            management_gap=gap,
        ))
        self.collision_count += 1
        self.collision_types_used.add(collision_type)

    # ──── 对撞1: 接通率 × 通话时长 → 有效会话密度 ────
    def _collide_connect_rate_x_duration(self, depts):
        """
        来源: 张烜搏六步法('抓开场') + Convoso漏斗模型
        高接通+短通话 = 接通了但留不住 → 开场白问题
        低接通+长通话 = 号码问题但话术OK → 修复号码即可释放产能
        """
        for d in depts:
            cr = d["connect_rate"]
            dur = d["avg_connect_dur"]

            if cr >= 43 and dur < 100:
                gap_rev = round(d["allocated"] * 0.02 * d["avg_deal_amount"])
                self._add_finding(
                    "metric_x_metric", "高接通·短通话",
                    f"{d['dept_name']} 接通率{cr}%达标但均接通时长仅{dur:.0f}s(<100s)，"
                    f"接通后留不住用户，开场白'抓客'能力不足。",
                    gap_rev, "P1",
                    evidence=[f"接通率{cr}%≥43%", f"均接通时长{dur:.0f}s<100s"],
                    recs=["强化开场白训练:3秒自报家门+价值钩子+开放式问题",
                          "录音分析秒挂原因TOP3并针对性培训"],
                    refs=["T01:张烜搏六步法-抓开场", "S09:超级转化率-六要素"],
                    scope="dept", dept_name=d["dept_name"], gap_key="high_connect_low_dur"
                )

            if cr < 40 and dur > 150:
                potential = round(d["allocated"] * (43 - cr) / 100 *
                                  d["conversion_rate"] / 100 * d["avg_deal_amount"])
                self._add_finding(
                    "metric_x_metric", "低接通·长通话",
                    f"{d['dept_name']} 接通率仅{cr}%但一旦接通均时长{dur:.0f}s(>150s)，"
                    f"话术能力强但号码/时段有瓶颈。修复接通率即可释放产能。",
                    potential, "P0",
                    evidence=[f"接通率{cr}%<40%", f"均接通时长{dur:.0f}s>150s"],
                    recs=["排查号码标记比例，轮换外呼线路",
                          "优化外呼时段:10:00-11:30/14:00-16:00黄金窗口"],
                    refs=["T18:外呼营销实战-接通率提升", "T22:电销新思维-AI外呼"],
                    scope="dept", dept_name=d["dept_name"], gap_key="low_connect"
                )

    # ──── 对撞2: 深沟率 × AI Score → 话术-转化矩阵 ────
    def _collide_deep_talk_x_ai_score(self, depts):
        """
        来源: SPIN Selling + 挑战式销售模型
        高深沟+低AI = 聊得久但没方向 → 缺转化话术
        低深沟+高AI = 高手但挑客 → 需考核深沟覆盖率
        """
        for d in depts:
            dr = d["deep_talk_rate"]
            ai = d["avg_ai_score"]

            if dr > 20 and ai < 68:
                rev = round(d["deep_talk"] * 0.05 * d["avg_deal_amount"])
                self._add_finding(
                    "metric_x_metric", "高深沟·低AI",
                    f"{d['dept_name']} 深沟率{dr}%不错但AI均分仅{ai}，"
                    f"员工愿深聊但缺'挖需求→谈方案'的转化话术，深沟变成闲聊。",
                    rev, "P1",
                    evidence=[f"深沟率{dr}%>20%", f"AI均分{ai}<68"],
                    recs=["定向培训SPIN提问法:情境→问题→暗示→需求回报",
                          "建立'深沟质量检查表':需求确认/方案匹配/促成试探"],
                    refs=["S01:SPIN Selling", "T05:电话销售中的心理学"],
                    scope="dept", dept_name=d["dept_name"], gap_key="high_deep_low_ai"
                )

            if dr < 15 and ai > 75:
                rev = round(d["link_1d_num"] * 0.05 * 0.08 * d["avg_deal_amount"])
                self._add_finding(
                    "metric_x_metric", "低深沟·高AI",
                    f"{d['dept_name']} AI均分{ai}很高但深沟率仅{dr}%，"
                    f"高手存在'挑客'心理，只聊明确意向客户。潜在客户被放弃。",
                    rev, "P2",
                    evidence=[f"深沟率{dr}%<15%", f"AI均分{ai}>75"],
                    recs=["增加'深沟覆盖率'考核指标(接通中深沟占比)",
                          "实行'挑战式销售':主动教育客户创造需求"],
                    refs=["S02:挑战式销售-教学裁剪掌控", "T09:打造狼性销售团队"],
                    scope="dept", dept_name=d["dept_name"], gap_key="low_deep_high_ai"
                )

    # ──── 对撞3: 司龄 × 产能 → 成长曲线与倦怠检测 ────
    def _collide_tenure_x_productivity(self, summary, persons):
        """
        来源: 组织行为学 + 司龄效能衰减模型
        产能=f(司龄)是倒U型曲线，峰值12-18月，>24月可能衰减
        """
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

        tenure_avg = {}
        for bucket, ps in buckets.items():
            if not ps:
                continue
            avg_rev = sum(p["revenue"] for p in ps) / len(ps)
            avg_ai = sum(p["ai_score"] for p in ps) / len(ps)
            avg_dials = sum(p["dial_count"] for p in ps) / len(ps)
            tenure_avg[bucket] = {
                "count": len(ps),
                "avg_rev": round(avg_rev),
                "avg_ai": round(avg_ai, 1),
                "avg_dials": round(avg_dials)
            }

        if "成熟期(1-2年)" in tenure_avg and "老员工(>2年)" in tenure_avg:
            mature = tenure_avg["成熟期(1-2年)"]
            senior = tenure_avg["老员工(>2年)"]
            if senior["avg_rev"] < mature["avg_rev"] * 0.85:
                drop = round((1 - senior["avg_rev"] / (mature["avg_rev"] or 1)) * 100, 1)
                daily_loss = round(senior["count"] *
                                   (mature["avg_rev"] - senior["avg_rev"]) * 0.3)
                self._add_finding(
                    "metric_x_entity", "老员工倦怠",
                    f"老员工(>2年){senior['count']}人均产值¥{senior['avg_rev']:,}，"
                    f"比成熟期¥{mature['avg_rev']:,}低{drop}%。"
                    f"典型'效能衰减曲线'——司龄超2年进入舒适区。",
                    daily_loss, "P2",
                    evidence=[f"老员工均产¥{senior['avg_rev']:,}",
                              f"成熟期均产¥{mature['avg_rev']:,}",
                              f"衰减{drop}%"],
                    recs=["轮岗制度:每18个月轮换部门或产品线",
                          "带教任务:老员工绑定新人，新人产出纳入老员工考核",
                          "差异化激励:阶梯式提成激活积极性"],
                    refs=["L07:驱动力-自主专精目的", "PE11:人效革命"]
                )

        if "新人(≤3月)" in tenure_avg:
            newbie = tenure_avg["新人(≤3月)"]
            overall_avg = summary["pc"]
            ratio = round(newbie["avg_rev"] / (overall_avg or 1) * 100, 1)
            if ratio < 50:
                daily_loss = round(newbie["count"] *
                                   (overall_avg * 0.7 - newbie["avg_rev"]) * 0.5)
                self._add_finding(
                    "metric_x_entity", "新人断崖",
                    f"新人(≤3月){newbie['count']}人均产值仅¥{newbie['avg_rev']:,}，"
                    f"为全员均值的{ratio}%(远低于70%及格线)。爬坡期过长。",
                    max(0, daily_loss), "P1",
                    evidence=[f"新人均产¥{newbie['avg_rev']:,}",
                              f"全员均产¥{overall_avg:,}",
                              f"达标率{ratio}%<50%"],
                    recs=["前3月实行'老带新'1对1制度",
                          "建立新人21天通关地图:Day1-7基础/Day8-14实战/Day15-21独立",
                          "新人首月设定保底指标，降低考核压力但强化学习"],
                    refs=["T06:可复制的销售力-SOP标准化",
                          "T08:销售冠军-通关培训体系",
                          "L16:高绩效教练-GROW模型"]
                )

        return tenure_avg

    # ──── 对撞4: 活动量 × 质量 → 效率矩阵 ────
    def _collide_activity_x_quality(self, depts):
        """
        来源: Balto研究(SDR仅4.4%时间在有质量会话) + Convoso漏斗
        """
        for d in depts:
            od = d["on_duty"] or 1
            dials_pp = d["dial_count"] / od
            quality_conv = d["deep_talk"] / od
            quality_ratio = round(quality_conv / (dials_pp or 1) * 100, 1)

            if dials_pp > 45 and quality_ratio < 4:
                rev = round(od * 1.5 * d["avg_deal_amount"] * 0.1)
                self._add_finding(
                    "metric_x_metric", "高拨打·低质量",
                    f"{d['dept_name']} 人均拨打{dials_pp:.0f}通(高活动量)但有质量会话仅"
                    f"{quality_conv:.1f}通/人({quality_ratio}%)。员工在'刷量'。",
                    rev, "P1",
                    evidence=[f"人均拨打{dials_pp:.0f}通", f"质量会话占比{quality_ratio}%<4%"],
                    recs=["优秀团队质量会话占比应>6%",
                          "从'追拨打量'转向'追有效会话数'考核",
                          "每日晨会分享优质会话录音，建立质量标杆"],
                    refs=["T23:Fanatical Prospecting", "PE08:因果链归因"],
                    scope="dept", dept_name=d["dept_name"], gap_key="low_quality_ratio"
                )

    # ──── 对撞5: 高峰 × 非高峰 → 时段效能失衡 ────
    def _collide_peak_x_offpeak(self, depts):
        """
        来源: 呼叫中心排班管理 + 精益思想(消除等待浪费)
        """
        for d in depts:
            total = d["peak_hour_revenue"] + d["offpeak_hour_revenue"]
            if total <= 0:
                continue
            peak_ratio = d["peak_hour_revenue"] / total
            if peak_ratio > 0.72:
                rev = round(d["offpeak_hour_revenue"] * 0.3)
                self._add_finding(
                    "metric_x_time", "时段失衡",
                    f"{d['dept_name']} 高峰时段贡献{peak_ratio*100:.0f}%营收，"
                    f"非高峰近乎空转。大量工时被浪费。",
                    rev, "P2",
                    evidence=[f"高峰占比{peak_ratio*100:.0f}%>72%"],
                    recs=["非高峰安排:培训/录音复盘/公海捞取/AI外呼预筛",
                          "尝试错峰外呼:测试12:30-13:30午休时段接通率"],
                    refs=["T19:Call Center Management", "O05:精益思想-消除浪费"],
                    scope="dept", dept_name=d["dept_name"], gap_key="peak_imbalance"
                )

    # ──── 对撞6: 签单量 × 退费率 → 过度承诺检测 ────
    def _collide_signed_x_refund(self, depts):
        """
        来源: 客户成功 + 极致服务ICARE模型
        高签单+高退费 = 过度承诺-签单-退费循环
        """
        avg_signed = statistics.mean([d["signed_deals"] for d in depts]) if depts else 0
        for d in depts:
            if d["refund_rate"] > 6 and d["signed_deals"] > avg_signed:
                self._add_finding(
                    "metric_x_metric", "高签单·高退费",
                    f"{d['dept_name']} 签单{d['signed_deals']}笔(高于均值{avg_signed:.0f})，"
                    f"但退费率{d['refund_rate']}%(>6%)。典型过度承诺循环。",
                    round(d["refund_amount"] * 0.5), "P1",
                    evidence=[f"签单{d['signed_deals']}笔>均值{avg_signed:.0f}",
                              f"退费率{d['refund_rate']}%>6%"],
                    recs=["签单后48h回访确认制度",
                          "建立'过度承诺黑名单':连续2月退费率>8%的个人进入辅导期",
                          "质检重点抽查高签单员工的成交话术"],
                    refs=["S15:客户成功-LTV管理", "T10:极致服务-ICARE"],
                    scope="dept", dept_name=d["dept_name"], gap_key="high_refund"
                )

    # ──── 对撞7: 部门间人效方差 → 管理效能 ────
    def _collide_dept_variance(self, summary, depts):
        """
        来源: 六西格玛变异控制 + 标杆管理
        CV>0.35说明管理标准化不足，有大量SOP推广空间
        """
        if len(depts) < 2:
            return

        pcs = [d["per_capita_revenue"] for d in depts]
        pc_mean = statistics.mean(pcs)
        pc_std = statistics.stdev(pcs)
        pc_cv = round(pc_std / (pc_mean or 1), 2)

        if pc_cv > 0.35:
            best = max(depts, key=lambda d: d["per_capita_revenue"])
            worst = min(depts, key=lambda d: d["per_capita_revenue"])
            gap_pct = round((best["per_capita_revenue"] / worst["per_capita_revenue"] - 1) * 100)
            rev = round((pc_mean - worst["per_capita_revenue"]) * worst["on_duty"] * 0.3)
            worst_mgr = self.dept_managers.get(worst["dept_name"], "")
            mgr_note = f"末位部门负责人{worst_mgr}需重点关注。" if worst_mgr else ""
            self._add_finding(
                "entity_x_entity", "部门间差距悬殊",
                f"{len(depts)}个部门人均产值CV={pc_cv}(>0.35)，"
                f"标杆{best['dept_name']}(¥{best['per_capita_revenue']:,.0f}) "
                f"vs 末位{worst['dept_name']}(¥{worst['per_capita_revenue']:,.0f})，"
                f"差距{gap_pct}%。管理标准化程度低。{mgr_note}",
                rev, "P1",
                evidence=[f"CV变异系数={pc_cv}>0.35",
                          f"标杆-末位差距{gap_pct}%"],
                recs=["提取标杆部门TOP录音→全员通关培训",
                      "建立跨部门'对标机制':月度最佳实践分享",
                      f"末位部门({worst['dept_name']})主管参加标杆部门驻点学习1周"],
                refs=["O06:六西格玛-变异控制", "T06:可复制的销售力"],
                scope="dept", dept_name=worst["dept_name"], gap_key="high_top20"
            )

        return pc_cv

    # ──── 对撞8: 建信转化 × 电销自有转化 → 协同效率 ────
    def _collide_jx_x_own_conversion(self, depts):
        """
        来源: 预测收入SDR/BDR体系 + 关键对话
        跨渠道信任传递效率检测
        """
        for d in depts:
            own_conv = d["conversion_rate"]
            jx_conv = d["jx_conv_rate"]
            if jx_conv < own_conv * 0.6 and d["jx_transfer_in"] > 30:
                rev = round(d["jx_transfer_in"] * (own_conv - jx_conv) / 100 *
                            d["avg_deal_amount"])
                self._add_finding(
                    "entity_x_entity", "建信→电销信任折损",
                    f"{d['dept_name']} 自有转化{own_conv}%，建信资源转化仅{jx_conv}%"
                    f"(不足自有的60%)。信任传递严重折损。",
                    rev, "P1",
                    evidence=[f"自有转化{own_conv}%", f"建信转化{jx_conv}%",
                              f"日转入{d['jx_transfer_in']}条"],
                    recs=["CRM强制附带画像标签+核心抗拒点",
                          "建信→电销交接前进行3分钟电话预热",
                          "落实双算机制激励建信销售做好铺垫"],
                    refs=["S05:预测收入-SDR/BDR体系", "L08:关键对话"],
                    scope="dept", dept_name=d["dept_name"], gap_key="jx_low_conv"
                )

    # ──── 对撞9: 漏斗 × 标杆 → 瓶颈定位 ────
    def _collide_funnel_x_benchmark(self, summary):
        """
        来源: Convoso漏斗模型 + TOC约束理论
        找到漏斗最薄弱环节 = 最高ROI修复点(瓶颈决定系统产出)
        """
        funnel = [
            ("分配→拨打", summary["dial_count"] / (summary["allocated"] or 1),
             3.0, "拨打倍率"),
            ("拨打→接通", summary["link_1d_num"] / (summary["dial_count"] or 1) * 100,
             15, "接通/拨打%"),
            ("接通→深沟", summary["deep_talk"] / (summary["link_1d_num"] or 1) * 100,
             20, "深沟/接通%"),
            ("深沟→签单", summary["signed_deals"] / (summary["deep_talk"] or 1) * 100,
             10, "签单/深沟%"),
        ]

        worst = min(funnel, key=lambda x: x[1] / (x[2] or 1))
        self._add_finding(
            "funnel_x_benchmark", "漏斗瓶颈",
            f"漏斗最薄弱环节: {worst[0]}(当前{worst[1]:.1f}，标杆{worst[2]})。"
            f"根据TOC约束理论，优先修复此环节可获最高边际ROI。",
            0, "P0",
            evidence=[f"{s}: 当前{v:.1f} vs 标杆{b}" for s, v, b, _ in funnel],
            recs=[f"集中资源修复'{worst[0]}'环节",
                  "建立漏斗日监控看板，每日追踪各环节转化率"],
            refs=["O04:目标-TOC约束理论", "A01:增长黑客-AARRR漏斗"]
        )

        return funnel

    # ──── 对撞10: 趋势 × 波动 → 稳定性检测 ────
    def _collide_trend_x_volatility(self, trends):
        """
        来源: 信号与噪声 + 反脆弱
        日间波动过大说明系统脆弱性高，需要建立稳定器
        """
        if len(trends) < 3:
            return

        revs = [t["total_revenue"] for t in trends]
        rev_mean = statistics.mean(revs)
        rev_std = statistics.stdev(revs) if len(revs) > 1 else 0
        rev_cv = round(rev_std / (rev_mean or 1), 3)

        if rev_cv > 0.15:
            min_day = min(trends, key=lambda t: t["total_revenue"])
            max_day = max(trends, key=lambda t: t["total_revenue"])
            swing = round((max_day["total_revenue"] - min_day["total_revenue"]) /
                          (rev_mean or 1) * 100, 1)
            self._add_finding(
                "metric_x_time", "营收波动过大",
                f"7日营收CV={rev_cv}(>0.15)，最高{max_day['dt'][-5:]} "
                f"¥{max_day['total_revenue']:,.0f} vs 最低{min_day['dt'][-5:]} "
                f"¥{min_day['total_revenue']:,.0f}，振幅{swing}%。系统脆弱性高。",
                round(rev_std * 0.5), "P2",
                evidence=[f"营收CV={rev_cv}", f"振幅{swing}%"],
                recs=["建立营收基准线，偏离>10%自动预警",
                      "分析高峰日vs低谷日的活动量/资源质量差异",
                      "杠铃策略:稳定基础盘+激进突破试验"],
                refs=["DA03:信号与噪声-预测思维",
                      "DA05:反脆弱-杠铃策略"]
            )

    # ──── 对撞11: 新人 × 全员 → 培训投入回报 ────
    def _collide_new_hire_x_overall(self, summary, persons):
        """来源: 销售加速公式 + GROW教练模型"""
        new_hires = [p for p in persons if p["tenure_months"] <= 3]
        if not new_hires:
            return

        new_avg_ai = sum(p["ai_score"] for p in new_hires) / len(new_hires)
        all_avg_ai = sum(p["ai_score"] for p in persons) / len(persons) if persons else 0

        if new_avg_ai < all_avg_ai * 0.8:
            gap = round(all_avg_ai - new_avg_ai, 1)
            self._add_finding(
                "metric_x_entity", "新人AI评分断层",
                f"新人(≤3月)AI均分{new_avg_ai:.1f}，比全员{all_avg_ai:.1f}低{gap}分，"
                f"差距{round(gap/all_avg_ai*100)}%。话术技能传承不足。",
                round(len(new_hires) * gap * 50), "P1",
                evidence=[f"新人AI均分{new_avg_ai:.1f}", f"全员AI均分{all_avg_ai:.1f}"],
                recs=["建立标杆话术库:按场景分类的'黄金话术'集",
                      "新人入职第一周强制完成AI模拟通关",
                      "指定AI评分>80的师傅进行1对1辅导"],
                refs=["S06:销售加速公式", "L16:高绩效教练"]
            )

    # ──── 对撞12: 拨打×接通×营收 三维对撞 ────
    def _collide_dials_x_connects_x_revenue(self, depts):
        """
        来源: 多维数据碰撞(三维对撞)
        拨打量高+接通率高+营收低 = 转化端问题
        拨打量低+接通率低+营收高 = 精准打法但有天花板
        """
        for d in depts:
            od = d["on_duty"] or 1
            dials_pp = d["dial_count"] / od
            cr = d["connect_rate"]
            pc = d["per_capita_revenue"]
            avg_pc = statistics.mean([x["per_capita_revenue"] for x in depts])

            if dials_pp > 50 and cr > 42 and pc < avg_pc * 0.75:
                self._add_finding(
                    "metric_x_metric", "高活动·高接通·低营收",
                    f"{d['dept_name']} 人均拨打{dials_pp:.0f}通、接通率{cr}%均达标，"
                    f"但人均产值¥{pc:,.0f}仅为均值{round(pc/avg_pc*100)}%。"
                    f"问题锁定在转化环节:深沟→签单的转化话术需加强。",
                    round((avg_pc - pc) * od * 0.2), "P0",
                    evidence=[f"拨打{dials_pp:.0f}通>50", f"接通率{cr}%>42%",
                              f"人均产值¥{pc:,.0f}<均值75%"],
                    recs=["该部门不缺活动量和触达，需聚焦转化话术",
                          "安排标杆部门转化TOP3对该部门进行现场辅导",
                          "分析该部门'深沟→签单'环节的具体断裂点"],
                    refs=["S01:SPIN Selling-需求回报", "S08:成交高于一切"],
                    scope="dept", dept_name=d["dept_name"], gap_key="high_activity_low_rev"
                )

    # ──── 对撞13: 持续性检测 → 管理动作缺失预警 ────
    def _collide_persistence_detection(self, depts, trends):
        """
        来源: 绩效管理 + TOC约束理论
        检测10天内部门关键指标是否持续低于红线且无改善趋势。
        连续>=7天无改善 → P0升级 + 绩效挂钩处罚建议。
        """
        if len(trends) < 5:
            return

        red_lines = {"cr": 43, "dr": 18, "conv": 1.0}

        by_dept_trend = defaultdict(list)
        for t in trends:
            if "dept_trends" in t:
                for dt in t["dept_trends"]:
                    by_dept_trend[dt["dept_name"]].append(dt)

        for d in depts:
            dn = d["dept_name"]
            cr_below_count = sum(1 for t in trends if t.get("cr", 50) < 43)

            if d["connect_rate"] < 43 and cr_below_count >= 5:
                mgr = self.dept_managers.get(dn, "")
                mgr_str = f"({mgr})" if mgr else ""
                days = cr_below_count
                self._add_finding(
                    "metric_x_time", f"持续不达标预警",
                    f"{dn}{mgr_str} 接通率已连续约{days}天低于43%红线，"
                    f"当前{d['connect_rate']}%，无明显改善趋势。"
                    f"管理者可能未采取有效干预措施。",
                    round(d["allocated"] * 0.03 * d["avg_deal_amount"]), "P0",
                    evidence=[f"当前接通率{d['connect_rate']}%<43%",
                              f"趋势数据显示约{days}天持续低于红线"],
                    recs=[f"今日发出正式预警通知给{mgr or '部门负责人'}",
                          "连续3日仍无管理动作(数据无改善波动)，"
                          "绩效分数扣减5分/日，直接体现薪酬变化",
                          "要求提交书面改善计划:排查号码标记+调整外呼时段+每日复盘",
                          "抄送上级领导邮件通知"],
                    refs=["PE02:关键绩效指标-红线管理", "L02:OKR工作法-对齐"],
                    scope="dept", dept_name=dn, gap_key="persistent_no_improve"
                )

    def _validate_rules(self):
        """验证对撞规则是否满足"""
        if self.collision_count < 5:
            self._add_finding(
                "rule_validation", "对撞数量不足",
                f"当前仅完成{self.collision_count}组对撞，未达到最低5组要求。"
                f"数据可能不足以支撑全面分析。",
                0, "P2"
            )
        if len(self.collision_types_used) < 3:
            self._add_finding(
                "rule_validation", "对撞类型覆盖不足",
                f"仅覆盖{len(self.collision_types_used)}种对撞类型，"
                f"需至少3种。当前类型: {', '.join(self.collision_types_used)}",
                0, "P2"
            )

    def get_summary(self):
        return {
            "total_collisions": self.collision_count,
            "collision_types": list(self.collision_types_used),
            "findings_by_priority": {
                "P0": len([f for f in self.findings if f.priority == "P0"]),
                "P1": len([f for f in self.findings if f.priority == "P1"]),
                "P2": len([f for f in self.findings if f.priority == "P2"]),
            },
            "total_revenue_impact": sum(f.revenue_impact for f in self.findings),
            "rules_satisfied": self.collision_count >= 5 and len(self.collision_types_used) >= 3
        }


class LogicCollisionEngine:
    """
    逻辑对撞引擎

    核心方法论:
    - 假设×证据: 先提假设，再用数据验证或推翻
    - 因果×结果: 正向推导+反向追溯，看是否一致
    - 规律×例外: 找一般规律，专门搜索例外
    - 标杆×现实: 用标杆碰撞现实，量化差距
    - 多视角对撞: 管理层/一线/客户/数据 四视角碰撞

    规则: 每次分析至少构建3组假设对撞链
    """

    def __init__(self):
        self._load_rules()
        self.hypotheses: list[dict] = []
        self.causal_chains: list[dict] = []
        self.findings: list[CollisionFinding] = []

    def _load_rules(self):
        rules_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "knowledge_base", "frameworks", "logic_collision_rules.json"
        )
        if os.path.exists(rules_path):
            with open(rules_path, "r", encoding="utf-8") as f:
                self.rules = json.load(f)
        else:
            self.rules = {}

    def execute(self, summary, depts, trends, persons, data_findings):
        """执行全部逻辑对撞分析"""
        self.hypotheses = []
        self.causal_chains = []
        self.findings = []

        self._build_and_test_hypotheses(summary, depts, trends, persons)
        self._build_causal_chains(summary, depts, trends)
        self._rule_exception_analysis(summary, depts, persons)
        self._multi_perspective_collision(summary, depts)
        self._cross_validate_with_data_findings(data_findings, summary, depts)

        self._validate_rules()

        return self.findings, self.hypotheses, self.causal_chains

    def _add_finding(self, collision_type, tag, description, revenue_impact,
                     priority, evidence=None, recs=None, refs=None):
        self.findings.append(CollisionFinding(
            collision_type=collision_type,
            tag=tag,
            description=description,
            revenue_impact=revenue_impact,
            priority=priority,
            evidence=evidence or [],
            recommendations=recs or [],
            knowledge_refs=refs or []
        ))

    # ──── 假设×证据对撞 ────
    def _build_and_test_hypotheses(self, S, depts, trends, persons):
        """
        来源: 精益数据分析OMTM + 信号与噪声贝叶斯思维
        先建立假设，再用数据验证
        """
        # 假设1: 营收增长/下降的主要驱动力
        if len(trends) >= 2:
            last = trends[-1]
            prev = trends[-2]
            rev_change = last["total_revenue"] - prev["total_revenue"]
            cr_change = last["cr"] - prev["cr"]
            conv_change = last["conv"] - prev["conv"]
            pc_change = last["pc"] - prev["pc"]

            h1 = {
                "id": "H1",
                "hypothesis": f"营收{'增长' if rev_change > 0 else '下降'}的主驱动力是接通率变化",
                "support_evidence": [],
                "reject_evidence": [],
                "verdict": "",
                "alternative": ""
            }

            if abs(cr_change) > 1.5:
                h1["support_evidence"].append(f"接通率变动{cr_change:+.1f}pp，幅度显著")
            else:
                h1["reject_evidence"].append(f"接通率变动仅{cr_change:+.1f}pp，幅度不大")

            alloc_change = last["allocated"] - prev["allocated"]
            if abs(alloc_change) > 50:
                h1["reject_evidence"].append(f"分配量变动{alloc_change:+d}条，可能是资源端驱动")

            if len(h1["reject_evidence"]) > len(h1["support_evidence"]):
                h1["verdict"] = "推翻"
                h1["alternative"] = (
                    f"营收变动主因可能是: "
                    f"{'分配量变化' if abs(alloc_change)>50 else ''} "
                    f"{'转化率变化' if abs(conv_change)>0.05 else ''} "
                    f"{'人均产值变化' if abs(pc_change)>200 else ''}"
                ).strip()
            else:
                h1["verdict"] = "支持"

            self.hypotheses.append(h1)

        # 假设2: TOP20%集中度过高是因为底部员工能力不足
        h2 = {
            "id": "H2",
            "hypothesis": "TOP20%占比过高是因为底部员工销售能力不足",
            "support_evidence": [],
            "reject_evidence": [],
            "verdict": "",
            "alternative": ""
        }

        if S.get("t20", 0) > 50:
            bot_persons = sorted(persons, key=lambda p: p["revenue"])[:int(len(persons) * 0.3)]
            top_persons = sorted(persons, key=lambda p: p["revenue"], reverse=True)[:int(len(persons) * 0.2)]

            bot_ai = sum(p["ai_score"] for p in bot_persons) / len(bot_persons) if bot_persons else 0
            top_ai = sum(p["ai_score"] for p in top_persons) / len(top_persons) if top_persons else 0

            if top_ai - bot_ai > 15:
                h2["support_evidence"].append(
                    f"TOP20% AI均分{top_ai:.1f}，BOTTOM30% AI均分{bot_ai:.1f}，"
                    f"差距{top_ai-bot_ai:.1f}分，能力差距显著")
            else:
                h2["reject_evidence"].append(
                    f"TOP20% AI均分{top_ai:.1f} vs BOTTOM30% {bot_ai:.1f}，"
                    f"差距仅{top_ai-bot_ai:.1f}分，能力差距不大")

            bot_dials = sum(p["dial_count"] for p in bot_persons) / len(bot_persons) if bot_persons else 0
            top_dials = sum(p["dial_count"] for p in top_persons) / len(top_persons) if top_persons else 0

            if top_dials > bot_dials * 1.3:
                h2["support_evidence"].append(
                    f"TOP人均拨打{top_dials:.0f}通 vs BOTTOM {bot_dials:.0f}通，活动量差距明显")
                h2["alternative"] = "不仅是能力问题，也是勤奋度/活动量问题"
            else:
                h2["reject_evidence"].append(
                    f"拨打量接近(TOP {top_dials:.0f} vs BOT {bot_dials:.0f})，非活动量问题")

            if len(h2["reject_evidence"]) >= len(h2["support_evidence"]):
                h2["verdict"] = "部分推翻"
                if not h2["alternative"]:
                    h2["alternative"] = "底部员工能力不差但转化效率低，可能是'挖需求→谈方案'环节缺失"
            else:
                h2["verdict"] = "支持"

            self.hypotheses.append(h2)

            rev_impact = round(len(bot_persons) * (S["pc"] * 0.7 - (
                sum(p["revenue"] for p in bot_persons) / len(bot_persons)
            )) * 0.3) if bot_persons else 0

            self._add_finding(
                "hypothesis_x_evidence", f"假设验证: {h2['verdict']}",
                f"假设'{h2['hypothesis']}' → {h2['verdict']}。"
                f"{'替代解释: ' + h2['alternative'] if h2['alternative'] else ''}",
                max(0, rev_impact), "P1",
                evidence=h2["support_evidence"] + h2["reject_evidence"],
                recs=["针对底部30%进行分类诊断:是能力问题还是意愿问题",
                      "能力问题→话术通关+AI模拟训练；意愿问题→激励机制+淘汰预警"],
                refs=["S02:挑战式销售", "L03:Q12敬业度"]
            )

        # 假设3: 退费率高是因为过度承诺
        h3 = {
            "id": "H3",
            "hypothesis": "退费率高是因为电销过度承诺而非服务问题",
            "support_evidence": [],
            "reject_evidence": [],
            "verdict": "",
            "alternative": ""
        }

        high_refund_depts = [d for d in depts if d["refund_rate"] > 6]
        low_refund_depts = [d for d in depts if d["refund_rate"] <= 4]

        if high_refund_depts and low_refund_depts:
            hr_avg_signed = sum(d["signed_deals"] for d in high_refund_depts) / len(high_refund_depts)
            lr_avg_signed = sum(d["signed_deals"] for d in low_refund_depts) / len(low_refund_depts)

            if hr_avg_signed > lr_avg_signed * 1.1:
                h3["support_evidence"].append(
                    f"高退费部门均签单{hr_avg_signed:.0f}笔 > 低退费部门{lr_avg_signed:.0f}笔，"
                    f"支持'冲签单导致过度承诺'")
            else:
                h3["reject_evidence"].append("高退费部门签单量并不高于低退费部门")

            hr_avg_ai = sum(d["avg_ai_score"] for d in high_refund_depts) / len(high_refund_depts)
            lr_avg_ai = sum(d["avg_ai_score"] for d in low_refund_depts) / len(low_refund_depts)

            if hr_avg_ai > lr_avg_ai:
                h3["support_evidence"].append(
                    f"高退费部门AI均分{hr_avg_ai:.1f}反而更高，说明话术激进但不准确")
            else:
                h3["reject_evidence"].append(
                    f"高退费部门AI均分{hr_avg_ai:.1f}更低，可能是整体能力问题")
                h3["alternative"] = "退费可能不是过度承诺，而是客服跟进不足或产品匹配问题"

            h3["verdict"] = "支持" if len(h3["support_evidence"]) > len(h3["reject_evidence"]) else "待定"
            self.hypotheses.append(h3)

    # ──── 因果链对撞 ────
    def _build_causal_chains(self, S, depts, trends):
        """
        来源: TOC约束理论 + 系统之美(反馈回路)
        正向推导 + 反向追溯，看因果链是否一致
        """
        # 营收因果链
        rev_chain = {
            "name": "营收因果链",
            "direction": "正向",
            "nodes": [
                {
                    "name": "资源输入",
                    "value": f"分配{S['allocated']:,}条(率{S.get('alloc_rate', 0)*100:.0f}%)",
                    "status": "normal" if S["allocated"] > S["on_duty"] * 12 else "warning"
                },
                {
                    "name": "触达效率",
                    "value": f"接通{S['cr']}% · 拨打{S['dial_count']:,}",
                    "status": "warning" if S["cr"] < 43 else "normal"
                },
                {
                    "name": "会话深度",
                    "value": f"深沟率{S['dr']}% · AI{S['ai']}分",
                    "status": "warning" if S["dr"] < 18 else "normal"
                },
                {
                    "name": "转化产出",
                    "value": f"转化{S['conv']}% · 签单{S['signed_deals']}笔",
                    "status": "warning" if S["conv"] < 1.0 else "normal"
                },
                {
                    "name": "营收结果",
                    "value": f"¥{S['total_revenue']:,.0f} · 人均¥{S['pc']:,}",
                    "status": "normal"
                },
                {
                    "name": "质量保障",
                    "value": f"退费{S['ref_rate']}% · 投诉{S['complaint_count']}件",
                    "status": "warning" if S["ref_rate"] > 5 else "normal"
                }
            ]
        }

        bottleneck_nodes = [n for n in rev_chain["nodes"] if n["status"] == "warning"]
        if bottleneck_nodes:
            rev_chain["bottleneck"] = bottleneck_nodes[0]["name"]
            rev_chain["diagnosis"] = (
                f"因果链瓶颈定位于'{bottleneck_nodes[0]['name']}'环节，"
                f"上游的投入在此处被损耗。优先修复此环节可释放全链产能。"
            )

        self.causal_chains.append(rev_chain)

        # 反向追溯链
        if S["pc"] < 4000:
            reverse_chain = {
                "name": "人均产值偏低-反向追溯",
                "direction": "反向",
                "result": f"人均产值¥{S['pc']:,}偏低",
                "possible_causes": []
            }
            if S["cr"] < 43:
                reverse_chain["possible_causes"].append(
                    f"接通率{S['cr']}%<43% → 触达不足 → 有效会话量不够")
            if S["dr"] < 18:
                reverse_chain["possible_causes"].append(
                    f"深沟率{S['dr']}%<18% → 未能深入沟通 → 需求未充分挖掘")
            if S["ai"] < 70:
                reverse_chain["possible_causes"].append(
                    f"AI均分{S['ai']}<70 → 话术质量低 → 转化能力不足")
            if S.get("t20", 0) > 55:
                reverse_chain["possible_causes"].append(
                    f"TOP20%占比{S['t20']}%>55% → 产能过度集中 → 中腰部拖后腿")

            if reverse_chain["possible_causes"]:
                primary_cause = reverse_chain["possible_causes"][0]
                is_consistent = any(
                    n["status"] == "warning"
                    for n in rev_chain["nodes"]
                )
                reverse_chain["consistency_check"] = (
                    "正反向因果链一致" if is_consistent else "正反向因果链存在偏差，需进一步分析"
                )
                self.causal_chains.append(reverse_chain)

                self._add_finding(
                    "cause_x_effect", "因果链追溯",
                    f"人均产值¥{S['pc']:,}偏低，反向追溯发现"
                    f"{len(reverse_chain['possible_causes'])}个可能原因，"
                    f"主因: {primary_cause.split('→')[0]}。"
                    f"{reverse_chain['consistency_check']}。",
                    0, "P1",
                    evidence=reverse_chain["possible_causes"],
                    recs=["按因果链顺序逐个修复，优先修复最上游瓶颈",
                          "瓶颈修复后重新评估下游指标，避免'头痛医头'"],
                    refs=["O04:目标-TOC约束理论", "O12:系统之美-杠杆点"]
                )

    # ──── 规律×例外对撞 ────
    def _rule_exception_analysis(self, S, depts, persons):
        """
        来源: 统计学的世界 + AB测试(寻找反例)
        找到一般规律后专门搜索例外，通过例外修正规律
        """
        # 规律: 接通率高的部门营收高
        cr_rev_corr = self._check_correlation(
            [d["connect_rate"] for d in depts],
            [d["total_revenue"] for d in depts]
        )

        exceptions = []
        for d in depts:
            avg_cr = statistics.mean([x["connect_rate"] for x in depts])
            avg_rev = statistics.mean([x["total_revenue"] for x in depts])
            if d["connect_rate"] > avg_cr and d["total_revenue"] < avg_rev * 0.85:
                exceptions.append(
                    f"{d['dept_name']}: 接通率{d['connect_rate']}%高于均值"
                    f"但营收仅¥{d['total_revenue']:,.0f}(低于均值15%)")

        if exceptions:
            self._add_finding(
                "rule_x_exception", "规律例外发现",
                f"一般规律'接通率高→营收高'在以下情况被打破: "
                f"{'; '.join(exceptions[:2])}。"
                f"说明接通率不是唯一驱动力，转化效率同等重要。",
                0, "P2",
                evidence=exceptions,
                recs=["修正考核:不能只看接通率，需同时考核有效会话转化率",
                      "建立'效能综合指数'= 接通率×深沟率×转化率的复合指标"],
                refs=["DA10:指标陷阱-度量反噬", "PE03:平衡计分卡"]
            )

    def _check_correlation(self, x_vals, y_vals):
        """简易相关性检测"""
        if len(x_vals) < 3:
            return 0
        n = len(x_vals)
        x_mean = sum(x_vals) / n
        y_mean = sum(y_vals) / n
        cov = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
        x_var = sum((x - x_mean) ** 2 for x in x_vals)
        y_var = sum((y - y_mean) ** 2 for y in y_vals)
        denom = (x_var * y_var) ** 0.5
        return round(cov / denom, 3) if denom else 0

    # ──── 多视角对撞 ────
    def _multi_perspective_collision(self, S, depts):
        """
        来源: 平衡计分卡四维度 + 原则(可信度加权)
        用不同利益相关者视角碰撞同一组数据
        """
        perspectives = {
            "管理层": [],
            "一线员工": [],
            "客户": [],
            "数据": []
        }

        # 管理层视角: ROI/人效/规模
        if S["roi"] < 200:
            perspectives["管理层"].append(
                f"团队ROI {S['roi']}%偏低(<200%)，投入产出比需改善")
        else:
            perspectives["管理层"].append(
                f"团队ROI {S['roi']}%健康(>200%)，可考虑扩大规模")

        # 一线员工视角: 工作量/工具/激励
        dials_pp = S["dial_count"] / (S["on_duty"] or 1)
        if dials_pp > 180:
            perspectives["一线员工"].append(
                f"人均拨打{dials_pp:.0f}通，工作负荷较重，需关注员工倦怠")
        if S.get("t20", 0) > 55:
            perspectives["一线员工"].append(
                f"TOP20%占{S['t20']}%，中腰部员工可能感到'再怎么努力也追不上'")

        # 客户视角: 体验/满意度
        if S["ref_rate"] > 5:
            perspectives["客户"].append(
                f"退费率{S['ref_rate']}%偏高，客户预期与实际服务存在差距")
        if S["complaint_count"] > S["on_duty"] * 0.1:
            perspectives["客户"].append(
                f"投诉{S['complaint_count']}件，可能存在话术过度承诺或服务不到位")

        # 数据视角: 统计异常
        pcs = [d["per_capita_revenue"] for d in depts]
        if len(pcs) > 1:
            cv = round(statistics.stdev(pcs) / (statistics.mean(pcs) or 1), 2)
            if cv > 0.3:
                perspectives["数据"].append(
                    f"部门人均产值CV={cv}，离散度高，数据不稳定")

        # 对撞: 各视角之间是否存在矛盾
        conflicts = []
        if (any("ROI" in p and "健康" in p for p in perspectives["管理层"]) and
                any("退费率" in p for p in perspectives["客户"])):
            conflicts.append("管理层认为ROI健康，但客户端退费率偏高——短期利润以牺牲客户满意度为代价")

        if (any("工作负荷较重" in p for p in perspectives["一线员工"]) and
                any("ROI" in p and "偏低" in p for p in perspectives["管理层"])):
            conflicts.append("员工工作量大但ROI偏低——不是不够努力而是效率有问题")

        if conflicts:
            self._add_finding(
                "multi_perspective", "多视角矛盾",
                "不同利益相关者视角碰撞发现矛盾: " + "; ".join(conflicts),
                0, "P1",
                evidence=[f"{k}: {'; '.join(v)}" for k, v in perspectives.items() if v],
                recs=["建立多维度经营健康度仪表盘，避免单一指标遮蔽问题",
                      "每周经营会议从四个视角轮流汇报:财务/客户/流程/成长"],
                refs=["PE03:平衡计分卡", "L19:原则-可信度加权"]
            )

    # ──── 交叉验证数据对撞结果 ────
    def _cross_validate_with_data_findings(self, data_findings, S, depts):
        """
        用逻辑对撞验证数据对撞的发现是否合理
        """
        p0_findings = [f for f in data_findings if f.priority == "P0"]
        if not p0_findings:
            return

        for finding in p0_findings:
            alt_explanation = self._generate_alternative(finding, S, depts)
            if alt_explanation:
                self._add_finding(
                    "cross_validation", f"验证: {finding.tag}",
                    f"数据对撞发现'{finding.tag}'的替代解释: {alt_explanation}。"
                    f"需进一步数据验证以排除替代解释。",
                    0, "P2",
                    evidence=[f"原始发现: {finding.description[:100]}"],
                    recs=["对P0级发现进行深入根因分析",
                          "用AB测试或自然实验验证因果关系"],
                    refs=["DA09:AB测试", "DA04:思考快与慢-确认偏差"]
                )

    def _generate_alternative(self, finding, S, depts):
        """为数据对撞发现生成替代解释"""
        tag = finding.tag
        if "接通" in tag:
            return "接通率异常也可能是特定时段的运营商限制或节假日效应"
        if "漏斗" in tag:
            return "漏斗瓶颈可能随时间动态变化，需观察至少7日确认是持续性问题"
        if "营收" in tag and "高" in tag:
            return "单日高活动高营收可能是大单效应而非系统性改善"
        return None

    def _validate_rules(self):
        """验证逻辑对撞规则"""
        if len(self.hypotheses) < 3:
            self._add_finding(
                "rule_validation", "假设数量不足",
                f"当前仅建立{len(self.hypotheses)}个假设(需至少3个)。"
                f"数据丰富度可能不足以进行完整逻辑对撞。",
                0, "P2"
            )

    def get_summary(self):
        return {
            "total_hypotheses": len(self.hypotheses),
            "hypotheses_supported": len([h for h in self.hypotheses if h["verdict"] == "支持"]),
            "hypotheses_rejected": len([h for h in self.hypotheses if h["verdict"] == "推翻"]),
            "causal_chains": len(self.causal_chains),
            "findings_count": len(self.findings),
            "rules_satisfied": len(self.hypotheses) >= 3
        }


class CrossDomainCollisionEngine:
    """
    跨领域对撞引擎

    核心方法论(来源: 8大领域×108本书交叉碰撞):
    - 销售×心理学: SPIN提问×损失厌恶, 挑战式销售×锚定效应...
    - 电销×团队管理: 铁军三板斧×OKR, 话术标准化×优势管理...
    - APP增长×交友行业: Hook模型×社交天性, AARRR×进化心理学...
    - 数据分析×运营方法论: 指标陷阱×TOC约束, 贝叶斯×精益迭代...

    规则: 每次分析至少触发3组跨领域对撞
    """

    MATRICES = {
        "sales_x_psychology": {
            "name": "销售×心理学",
            "rules": [
                {
                    "trigger": lambda S, d: S.get("dr", 0) > 15 and S.get("conv", 0) < 1.2,
                    "tag": "SPIN暗示问题×损失厌恶",
                    "desc": "深沟率{dr}%尚可但转化率仅{conv}%，深沟未有效触发客户损失厌恶心理。"
                           "暗示问题('如果继续这样,可能会错过最佳婚恋年龄')触发损失厌恶效果加倍。",
                    "recs": ["话术植入损失厌恶锚点:用'错过/失去/再也'替代'获得/拥有'",
                             "建立'紧迫感话术库':时间窗口+竞争稀缺+年龄焦虑"],
                    "refs": ["S01:SPIN Selling-暗示问题", "C02:怪诞行为学-损失厌恶"],
                    "uplift": "深沟→签单转化率+3pp",
                    "priority": "P1"
                },
                {
                    "trigger": lambda S, d: S.get("avg_deal", 0) < 5500,
                    "tag": "挑战式销售×锚定效应",
                    "desc": "客单价¥{avg_deal:,}偏低，缺少'先教育再报价'的锚定策略。"
                           "先讲行业数据(交友成功率仅3%)再介绍服务，锚定点更高。",
                    "recs": ["通话前60秒植入行业数据教育:匹配成功率/平均寻找时间",
                             "报价时先呈现高价方案(锚定)，再推荐中间档(对比效应)"],
                    "refs": ["S02:挑战式销售-教学裁剪掌控", "C02:怪诞行为学-锚定效应"],
                    "uplift": "客单价+8%",
                    "priority": "P2"
                },
                {
                    "trigger": lambda S, d: S.get("t20", 0) > 50,
                    "tag": "影响力社会认同×从众效应",
                    "desc": "TOP20%占{t20}%业绩，中腰部缺乏'社会认同'驱动力。"
                           "双重社会压力话术'跟你同龄的用户中85%选了这个方案'可提升转化。",
                    "recs": ["中腰部员工配备'社会认同话术卡':同龄人数据+成功案例",
                             "每日晨会分享1个真实成交故事，激活从众效应"],
                    "refs": ["S04:影响力-社会认同", "C07:乌合之众-从众效应"],
                    "uplift": "中腰部转化率+5pp",
                    "priority": "P1"
                },
                {
                    "trigger": lambda S, d: S.get("fc_rate", 0) < 3,
                    "tag": "信任构建×非暴力沟通共情",
                    "desc": "首通转化率仅{fc_rate}%，首次通话缺乏信任基础。"
                           "先听客户倾诉5分钟再推方案='信任+共情=最强签单基础'。",
                    "recs": ["首通SOP:前5分钟共情倾听(不推产品)+后续方案匹配",
                             "录音抽检'打断次数'指标:优秀≤2次/通话"],
                    "refs": ["S07:销售圣经-信任", "C09:非暴力沟通-共情"],
                    "uplift": "首通转化率+2pp",
                    "priority": "P2"
                },
            ]
        },
        "telesale_x_management": {
            "name": "电销×团队管理",
            "rules": [
                {
                    "trigger": lambda S, d: any(x["per_capita_revenue"] > 1.5 *
                        statistics.mean([y["per_capita_revenue"] for y in d]) for x in d) if len(d) > 1 else False,
                    "tag": "话术标准化×优势管理",
                    "desc": "部门间人均产值差距显著，标准化是下限(70%标准话术)，个性化是上限(30%个人风格)。"
                           "可复制的不是'最好的'话术，而是'可学会的'话术。",
                    "recs": ["建立'话术三层架构':基础层(标准化)+策略层(场景化)+个人层(风格化)",
                             "每周提取2条标杆录音→拆解→通关测试→全员推广"],
                    "refs": ["T06:可复制的销售力-SOP", "L03:Q12-优势管理"],
                    "uplift": "中腰部产值+15%",
                    "priority": "P1"
                },
                {
                    "trigger": lambda S, d: S.get("ai", 0) < 75,
                    "tag": "质检AI化×复盘四步法",
                    "desc": "AI均分{ai}未达标(标杆75)，质检发现问题但缺少'复盘→改善'闭环。"
                           "每日AI质检→每周个人复盘→月度团队复盘=持续提升认知。",
                    "recs": ["每日AI质检报告推送到个人(含TOP3改善点)",
                             "每周五个人复盘:本周AI评分变化+改善行动+下周目标",
                             "月度团队复盘:四步法(回顾目标→评估结果→分析原因→总结经验)"],
                    "refs": ["T22:电销新思维-AI质检", "L13:复盘-四步法"],
                    "uplift": "AI评分+5分/季度",
                    "priority": "P1"
                },
                {
                    "trigger": lambda S, d: True,
                    "tag": "狼性PK×内在动机驱动力",
                    "desc": "外在PK(奖金/排名)提供短期刺激，但内在动机(意义/成长/自主)才是持久动力。"
                           "PK奖金+冠军故事+客户感谢信=外在激励×内在意义的完美融合。",
                    "recs": ["每月冠军颁奖增加'客户感谢信/感谢视频'环节",
                             "设置'进步最大奖'(非绝对值)激励中腰部员工"],
                    "refs": ["T09:打造狼性销售团队", "L07:驱动力-自主专精目的"],
                    "uplift": "团队活力+25%",
                    "priority": "P2"
                },
            ]
        },
        "data_x_operations": {
            "name": "数据分析×运营方法论",
            "rules": [
                {
                    "trigger": lambda S, d: True,
                    "tag": "指标陷阱×TOC约束瓶颈",
                    "desc": "考核什么就得到什么(指标陷阱) vs 瓶颈决定系统产出(TOC)。"
                           "指标应对准瓶颈而非分散考核，否则员工优化'被考核的指标'而忽视真正瓶颈。",
                    "recs": ["每月重新评估KPI是否对准当前瓶颈",
                             "警惕'拨打量至上'导致质量下降的指标反噬"],
                    "refs": ["DA10:指标陷阱-度量反噬", "O04:目标-TOC约束理论"],
                    "uplift": "瓶颈修复速度+50%",
                    "priority": "P2"
                },
                {
                    "trigger": lambda S, d: len(d) > 3,
                    "tag": "辛普森悖论×二八法则",
                    "desc": "整体数据可能掩盖局部真相(辛普森悖论)。大盘指标必须下钻到部门/个人级别，"
                           "结合二八法则聚焦TOP20%和BOTTOM30%的差异。",
                    "recs": ["所有大盘报告必须附带部门/个人下钻视图",
                             "每周异常检测:部门指标偏离大盘均值>1.5倍标准差自动预警"],
                    "refs": ["DA07:统计学的世界-辛普森悖论", "PE02:关键绩效指标"],
                    "uplift": "异常发现速度+60%",
                    "priority": "P2"
                },
            ]
        },
        "app_x_dating": {
            "name": "APP增长×交友行业",
            "rules": [
                {
                    "trigger": lambda S, d: True,
                    "tag": "Hook上瘾模型×社交天性连接需求",
                    "desc": "交友APP天然具备Hook模型四要素(触发→行动→不确定酬赏→投入)。"
                           "强化'谁喜欢了我'的悬念设计可利用社交天性的连接需求。",
                    "recs": ["APP端强化'谁看了你/谁喜欢了你'的悬念推送",
                             "电销话术引用APP互动数据:'已有X人对你表示感兴趣'增强价值感知"],
                    "refs": ["A03:上瘾-Hook模型", "D01:社交天性-连接需求"],
                    "uplift": "DAU留存+12%",
                    "priority": "P2"
                },
                {
                    "trigger": lambda S, d: True,
                    "tag": "AARRR漏斗×进化心理学择偶差异",
                    "desc": "男女激活路径应不同(进化心理学):男性→引导发消息(广撒网策略),"
                           "女性→引导完善资料(精筛选策略)。单一激活路径损失一半效率。",
                    "recs": ["电销面向男性客户强调'优质女性资源数量多/匹配效率高'",
                             "电销面向女性客户强调'严格筛选机制/安全可靠/红娘一对一把关'"],
                    "refs": ["A01:增长黑客-AARRR", "D03:进化心理学-择偶差异"],
                    "uplift": "激活率+18%",
                    "priority": "P2"
                },
                {
                    "trigger": lambda S, d: True,
                    "tag": "用户分层运营×孤独经济消费",
                    "desc": "不同年龄段付费逻辑不同:30+走'焦虑→效率'路线(愿意花钱买时间),"
                           "25-走'社交→娱乐'路线(愿意为体验付费)。电销话术需针对性调整。",
                    "recs": ["按年龄段建立差异化话术:30+强调效率/成功率，25-强调社交乐趣/体验",
                             "资源分配优化:高付费潜力客户(30+/高收入)优先分配给TOP销售"],
                    "refs": ["A09:用户增长方法论-分层", "D06:孤独经济-消费画像"],
                    "uplift": "ARPU+22%",
                    "priority": "P1"
                },
            ]
        },
        "turnaround_x_reality": {
            "name": "困境重建×经营现实",
            "rules": [
                {
                    "trigger": lambda S, d: S.get("t20", 0) > 50 and len(d) > 3,
                    "tag": "271法则×自然代谢替代裁员",
                    "desc": "TOP20%占{t20}%业绩，底部30%拖累整体。应避免大规模裁员(增加用人成本风险)，"
                           "应采用'联盟式管理':明确绩效任期→达不到自然淘汰→避免行政对抗。",
                    "recs": ["设定3个月绩效任期:月均产值<团队60%者进入辅导期",
                             "辅导期1个月仍无改善→自然调岗/转岗，避免直接裁员引发索赔",
                             "同步用'进步最大奖'激活中腰部，避免只罚不奖"],
                    "refs": ["R31:打造销售铁军-271法则", "R33:联盟-任期制", "R29:奈飞文化手册"],
                    "uplift": "底部30%产能提升20%或自然代谢",
                    "priority": "P1"
                },
                {
                    "trigger": lambda S, d: True,
                    "tag": "战时CEO×20英里行军",
                    "desc": "珍爱网处于'战时CEO'阶段(Horowitz)，需要快速决策、强力执行。"
                           "但同时需要Collins的'20英里行军'——保持稳定节奏，不急不缓。"
                           "战时≠冲刺，而是在混乱中保持纪律性前进。",
                    "recs": ["每日/每周设定固定数量的推进目标(20英里行军)",
                             "拒绝'大跃进'式KPI：每周改善目标不超过当前值的5%",
                             "管理层每日15分钟站会:红黄绿灯汇报(学Ford)"],
                    "refs": ["R17:创业维艰-战时CEO", "R04:选择卓越-20英里行军", "R08:Ford-One Ford"],
                    "uplift": "执行稳定性+40%，避免崩盘风险",
                    "priority": "P1"
                },
                {
                    "trigger": lambda S, d: S.get("ref_rate", 0) > 4,
                    "tag": "客户成功×品牌修复信任链",
                    "desc": "退费率{ref_rate}%偏高，在行业信任度仅18.7%的大背景下，每一个退费客户都是品牌的'二次伤害'。"
                           "品牌修复路径:先承认问题(行业有乱象)→再证明不同(我们合规)→用成功案例说话(口碑)。",
                    "recs": ["签单后24h发送'行业安全指南+珍爱网合规承诺书'，主动建立信任",
                             "每月收集3个成功案例视频，作为销售素材和品牌资产",
                             "退费客户进行满意度回访:找到退费根因是'过度承诺'还是'服务不达标'"],
                    "refs": ["R34:品牌洗脑-信任重建", "R35:客户成功", "R37:口碑-STEPPS"],
                    "uplift": "退费率降1pp+品牌信任恢复",
                    "priority": "P1"
                },
                {
                    "trigger": lambda S, d: True,
                    "tag": "杠铃策略×现金流红线",
                    "desc": "10亿现金是生命线(反脆弱-杠铃策略)。运营预算90%用于稳健的基本盘(电销+服务)，"
                           "10%用于创新实验(拾花有伴/趣约会/新模式)。"
                           "任何单项投入>500万必须有ICE评分>30的实验数据支撑。",
                    "recs": ["建立'创新实验池':每月最多3个小实验，每个预算<50万",
                             "实验必须设定明确的北极星指标和止损线",
                             "基本盘运营追求'每日正现金流'，不允许寅吃卯粮"],
                    "refs": ["R27:反脆弱-杠铃策略", "R38:增长黑客-ICE评分", "R39:精益创业-MVP"],
                    "uplift": "现金流安全+创新不停滞",
                    "priority": "P2"
                },
                {
                    "trigger": lambda S, d: any(x["per_capita_revenue"] < 1200 for x in d) if d else False,
                    "tag": "飞轮效应×困境六悖论",
                    "desc": "存在人均产值<1200的部门，但困境企业不能简单'加压'。"
                           "飞轮思维:线索→建信→签单→服务→口碑→线索。找到飞轮卡住的环节，"
                           "而非在整条链上同时施压。一次只修一个环节。",
                    "recs": ["诊断飞轮卡点:是线索质量差?建信不到位?话术弱?服务跟不上?",
                             "集中100%改善资源到卡点环节(TOC)，不分散",
                             "每周检查飞轮是否'转得更快了'，而非看绝对值"],
                    "refs": ["R01:从优秀到卓越-飞轮效应", "R05:转动飞轮", "R03:巨人如何倒下"],
                    "uplift": "低产部门产能+25%",
                    "priority": "P1"
                },
            ]
        },
    }

    def __init__(self):
        self._load_matrices()
        self.findings: list[CollisionFinding] = []
        self.collision_count = 0
        self.domains_used = set()

    def _load_matrices(self):
        """加载跨领域对撞矩阵"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "knowledge_base", "frameworks", "collision_matrices.md"
        )
        self.matrices_loaded = os.path.exists(path)

    def execute(self, summary, depts, data_findings, logic_findings):
        """执行跨领域对撞分析"""
        self.findings = []
        self.collision_count = 0
        self.domains_used = set()

        for domain_key, domain in self.MATRICES.items():
            for rule in domain["rules"]:
                try:
                    triggered = rule["trigger"](summary, depts)
                except Exception:
                    triggered = False

                if triggered:
                    desc = rule["desc"].format(**summary)
                    self.findings.append(CollisionFinding(
                        collision_type=f"cross_domain:{domain_key}",
                        tag=rule["tag"],
                        description=desc,
                        revenue_impact=0,
                        priority=rule["priority"],
                        evidence=[rule["uplift"]],
                        recommendations=rule["recs"],
                        knowledge_refs=rule["refs"]
                    ))
                    self.collision_count += 1
                    self.domains_used.add(domain["name"])

        self._enrich_from_data_findings(data_findings, summary)

        return self.findings

    def _enrich_from_data_findings(self, data_findings, S):
        """根据数据对撞发现触发额外的跨领域洞察"""
        for f in data_findings:
            if f.priority == "P0" and "漏斗" in f.tag:
                self.findings.append(CollisionFinding(
                    collision_type="cross_domain:super_collision",
                    tag="漏斗瓶颈×TOC约束×贝叶斯迭代",
                    description=(
                        f"漏斗瓶颈(P0)应用TOC约束理论:集中100%资源修复瓶颈环节，"
                        f"同时用贝叶斯思维设定改善实验的先验概率，快速迭代验证。"
                        f"ICE评分>20的实验优先AB测试。"
                    ),
                    revenue_impact=0,
                    priority="P1",
                    evidence=["TOC:瓶颈决定系统产出", "贝叶斯:先验→实验→后验"],
                    recommendations=[
                        "为瓶颈环节设计3个改善实验，按ICE评分排序",
                        "每个实验设定贝叶斯先验概率(基于知识库经验)，AB测试验证",
                        "周回顾:更新后验概率→调整优先级→迭代下一轮"
                    ],
                    knowledge_refs=["O04:TOC约束理论", "DA02:精益数据分析-OMTM",
                                    "DA09:AB测试实战"]
                ))
                self.collision_count += 1
                self.domains_used.add("超级对撞")

            if "退费" in f.tag or "过度承诺" in f.tag:
                self.findings.append(CollisionFinding(
                    collision_type="cross_domain:super_collision",
                    tag="退费风险×认知失调×沉没成本设计",
                    description=(
                        f"退费问题需从心理学视角解决:签单后48h回访预防'购后认知失调'，"
                        f"同时设计沉没成本机制(首次服务体验/专属资料/匹配报告)让客户"
                        f"感受到已投入的价值，降低退费意愿。"
                    ),
                    revenue_impact=0,
                    priority="P1",
                    evidence=["怪诞行为学:购后认知失调", "影响力:沉没成本效应"],
                    recommendations=[
                        "签单后2h内发送'专属匹配报告'(沉没成本)",
                        "48h内回访确认期望值，及早发现退费苗头",
                        "退费与销售提成绑定考核:退费率>8%的个人提成系数×0.8"
                    ],
                    knowledge_refs=["C02:怪诞行为学-认知失调", "S04:影响力-承诺一致性",
                                    "S15:客户成功-LTV"]
                ))
                self.collision_count += 1
                self.domains_used.add("超级对撞")
                break

    def get_summary(self):
        return {
            "total_collisions": self.collision_count,
            "domains_used": list(self.domains_used),
            "domains_count": len(self.domains_used),
            "findings_count": len(self.findings),
            "matrices_loaded": self.matrices_loaded,
            "findings_by_priority": {
                "P0": len([f for f in self.findings if f.priority == "P0"]),
                "P1": len([f for f in self.findings if f.priority == "P1"]),
                "P2": len([f for f in self.findings if f.priority == "P2"]),
            }
        }


_CROSS_DEPT_KEYWORDS = ["技术部", "行政", "HR", "人力", "IT部", "系统升级", "平台改造", "APP端", "产品部", "研发"]
_BUDGET_KEYWORDS = ["大额投入", "采购", "购买", "升级系统", "新增人员", "招聘", "扩招", "外部顾问"]
_OVERLOAD_KEYWORDS = ["增加拨打量", "加量", "延长工时", "加班", "提高拨打量", "人均拨打提至"]
_COMPLIANCE_RISK_KEYWORDS = ["门店扩张", "高客单价", "快速转化", "逼签", "压单", "强制成交"]


def validate_feasibility(item: dict) -> dict:
    """
    基于珍爱网经营背景红线，校验建议可行性。

    校验维度:
    1. 跨部门依赖度: 是否需要支持部门配合
    2. 资源投入检测: 是否需要大额预算
    3. 组织疲劳度: 是否鞭打快牛
    4. 合规风险: 是否风险回流总部

    Returns: {"feasibility": "high"|"medium"|"low",
              "dependency": "self_contained"|"cross_dept"|"budget_required",
              "risk_notes": str}
    """
    text = f"{item.get('title', '')} {item.get('act', '')} {item.get('detail', '')} {item.get('daily_action', '')}"

    dependency = "self_contained"
    risk_notes = []
    feasibility = "high"

    for kw in _CROSS_DEPT_KEYWORDS:
        if kw in text:
            dependency = "cross_dept"
            risk_notes.append(f"需{kw}配合，跨部门协调成本较高")
            feasibility = "medium"
            break

    for kw in _BUDGET_KEYWORDS:
        if kw in text:
            if dependency == "self_contained":
                dependency = "budget_required"
            risk_notes.append("涉及预算投入，需核算边际ROI，守住现金流红线")
            if feasibility == "high":
                feasibility = "medium"
            break

    for kw in _OVERLOAD_KEYWORDS:
        if kw in text:
            risk_notes.append("⚠ 鞭打快牛预警：要求一线大幅加量，需评估组织疲劳度")
            feasibility = "low"
            break

    for kw in _COMPLIANCE_RISK_KEYWORDS:
        if kw in text:
            risk_notes.append("⚠ 风险回流总部预警：涉及合规敏感操作，违反SaaS隔离原则")
            feasibility = "low"
            break

    if not risk_notes:
        risk_notes.append("弱依赖·强闭环，业务团队可自行推动落地")

    return {
        "feasibility": feasibility,
        "dependency": dependency,
        "risk_notes": "；".join(risk_notes),
    }
