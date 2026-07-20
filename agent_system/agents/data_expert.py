"""
数据专家智能体 v2.0 (Data Expert Agent)

核心能力:
1. 数据对撞 (Data Collision) - 12种多维数据交叉碰撞模型
2. 逻辑对撞 (Logic Collision) - 假设验证/因果链/规律例外/多视角碰撞
3. 跨领域对撞 (Cross-Domain Collision) - 8大领域×108本书理论交叉碰撞
4. 领域知识 - 108本专业书籍融合: 8大领域覆盖
5. 量化诊断 - 所有发现必须量化业务影响+可执行建议

强制规则(每次分析自动执行):
- 数据对撞: ≥5组, 覆盖≥3种对撞类型
- 逻辑对撞: ≥3组假设对撞链
- 跨领域对撞: ≥3组跨领域碰撞
- 三引擎交叉验证

调用方式:
    from agent_system import DataExpert

    expert = DataExpert(db_path="zhenai_ts_v4.db")
    report = expert.analyze(date="2026-02-27")
    expert.run_full_pipeline("2026-02-27")
"""

import os
import json
import statistics
import webbrowser
from datetime import datetime

from agent_system.actions.email_sender import send_report_email
from agent_system.engines.analysis_pipeline import AnalysisPipeline, AnalysisReport


# 负责人来自电销经理团队日报/电销区域小时报（厦门一区→一部，深圳一区→二部...）
DEPT_MANAGERS = {
    "电销一部": "何丹丹",   # 厦门电销一区
    "电销二部": "赵梅",     # 深圳电销一区
    "电销三部": "朱晓园",   # 深圳电销二区
    "电销四部": "宋晓鹏",   # 深圳电销三区
    "电销五部": "吴胜悍",   # 深圳电销五区
    "电销六部": "游云清",   # 西安电销一区
    "电销七部": "",         # 深圳老人区（待确认）
    "电销八部": "",         # 深圳新人区（待确认）
}


class DataExpert:
    """
    数据专家智能体 v2.1

    融合108本专业书籍×8大领域知识:
    销售精通/电话销售/APP增长/交友行业/团队管理/数据分析/客户心理/运营方法论

    三引擎架构: 数据对撞 + 逻辑对撞 + 跨领域对撞
    经营红线: 反鞭打快牛 + 弱依赖强闭环 + 现金流红线 + 风险隔离 + 组织疲劳度评估
    管理规则: 全局/部门级分栏 + 管理者姓名关联 + 时间维度建议 + 持续不改善升级处罚 + 可行性校验
    """

    VERSION = "2.2.0"
    AGENT_NAME = "数据专家"

    def __init__(self, db_path: str, dept_managers: dict = None):
        if not os.path.isabs(db_path):
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                db_path
            )
        self.db_path = db_path
        self.managers = dept_managers or DEPT_MANAGERS
        self.pipeline = AnalysisPipeline(db_path, dept_managers=self.managers)
        self._load_knowledge_base()

    def _load_knowledge_base(self):
        """加载知识库索引"""
        kb_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "knowledge_base", "book_index.json"
        )
        if os.path.exists(kb_path):
            with open(kb_path, "r", encoding="utf-8") as f:
                self.knowledge_base = json.load(f)
            meta = self.knowledge_base.get("knowledge_base_meta", {})
            self.total_books = meta.get("total_books", 0)
            self.domains = meta.get("domains", 0)
        else:
            self.knowledge_base = {}
            self.total_books = 0
            self.domains = 0

    def analyze(self, date: str, dates_range: list = None) -> AnalysisReport:
        """
        执行完整数据分析

        自动执行:
        1. 数据拉取(3次SQL)
        2. 数据对撞(≥5组)
        3. 逻辑对撞(≥3组假设)
        4. 量化改善建议
        5. 组装报告

        Args:
            date: 分析日期 "YYYY-MM-DD"
            dates_range: 趋势日期范围(默认自动推算7日)

        Returns:
            AnalysisReport 完整分析报告
        """
        report = self.pipeline.run(date, dates_range)
        return report

    def get_executive_summary(self, report: AnalysisReport) -> str:
        """生成高管摘要"""
        S = report.summary
        dc = report.data_collision_summary
        lc = report.logic_collision_summary
        cd = report.cross_domain_summary
        all_f = report.get_all_findings_sorted()
        p0 = [f for f in all_f if f.priority == "P0"]

        summary = f"""
{'='*56}
  数据专家诊断摘要 v{self.VERSION} - {report.date}
{'='*56}

>> 大盘概况
  营收: Y{S['total_revenue']/10000:.1f}万 (环比{S.get('rev_dod',0):+.1f}%)
  人均产值: Y{S['pc']:,} | 转化率: {S['conv']}% | 接通率: {S['cr']}%
  签单: {S['signed_deals']}笔 | 退费率: {S['ref_rate']}%

>> 三引擎对撞诊断
  [引擎1] 数据对撞: {dc['total_collisions']}组 ({', '.join(dc['collision_types'][:4])})
  [引擎2] 逻辑对撞: {lc['total_hypotheses']}组假设 (支持{lc['hypotheses_supported']}/推翻{lc['hypotheses_rejected']}) + {lc['causal_chains']}条因果链
  [引擎3] 跨领域对撞: {cd.get('total_collisions',0)}组 ({', '.join(cd.get('domains_used',[])[:4])})
  ---
  总发现: {len(all_f)}项 (P0:{len(p0)}项)

>> P0级紧急问题
"""
        for f in p0:
            summary += f"  * {f.tag}: {f.description[:80]}\n"

        summary += "\n>> TOP3改善建议\n"
        for i, item in enumerate(report.improvements[:3]):
            summary += f"  {i+1}. [{item['p']}] {item['title']}: {item['cur']}->{item['tgt']} (日增Y{item['rev']:,})\n"

        summary += f"""
>> 总改善潜力: +Y{report.total_uplift:,}/日 (+Y{report.total_uplift*30/10000:.1f}万/月)

>> 知识库: {self.total_books}本专业书籍 x {self.domains}个领域
  三引擎: 数据对撞(12种) + 逻辑对撞(5种) + 跨领域对撞(4大矩阵)
{'='*56}
"""
        return summary

    def render_html(self, report: AnalysisReport) -> str:
        """渲染HTML分析报告"""
        S = report.summary
        depts = report.departments
        trends = report.trends
        all_findings = report.get_all_findings_sorted()

        def arrow(v):
            if v > 0:
                return f'<span style="color:#16a34a;font-size:12px;">▲+{v:.1f}%</span>'
            if v < 0:
                return f'<span style="color:#dc2626;font-size:12px;">▼{v:.1f}%</span>'
            return '<span style="color:#94a3b8;font-size:12px;">—</span>'

        def spark(vals, color="#dc2626", h=36, w=100):
            if not vals:
                return ""
            mn, mx = min(vals), max(vals)
            rng = mx - mn or 1
            pts = []
            step = w / max(len(vals) - 1, 1)
            for i, v in enumerate(vals):
                pts.append(f"{round(i * step, 1)},{round(h - (v - mn) / rng * (h - 6), 1)}")
            return (f'<svg width="{w}" height="{h}" style="vertical-align:middle;">'
                    f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" '
                    f'stroke-width="1.5" stroke-linejoin="round"/></svg>')

        rev_sp = spark([t["total_revenue"] for t in trends], "#dc2626")
        cr_sp = spark([t["cr"] for t in trends], "#2563eb")
        pc_sp = spark([t["pc"] for t in trends], "#d97706")
        conv_sp = spark([t["conv"] for t in trends], "#16a34a")

        # 部门排名
        dept_rows = ""
        for i, d in enumerate(depts):
            bg = "#f8fafc" if i % 2 == 0 else "#fff"
            cr_c = "#dc2626" if d["connect_rate"] < 43 else "#333"
            t20_c = "#dc2626" if d["top20_pct"] > 55 else "#d97706" if d["top20_pct"] > 50 else "#16a34a"
            dept_rows += f'''<tr style="background:{bg};">
<td style="padding:9px 12px;font-weight:600;">{d['dept_name']}</td>
<td style="padding:9px 6px;text-align:right;font-weight:700;">¥{d['total_revenue']:,.0f}</td>
<td style="padding:9px 6px;text-align:right;">¥{d['per_capita_revenue']:,.0f}</td>
<td style="padding:9px 6px;text-align:center;color:{cr_c};">{d['connect_rate']}%</td>
<td style="padding:9px 6px;text-align:center;">{d['deep_talk_rate']}%</td>
<td style="padding:9px 6px;text-align:center;">{d['avg_ai_score']}</td>
<td style="padding:9px 6px;text-align:center;">{d['conversion_rate']}%</td>
<td style="padding:9px 6px;text-align:center;">{d['signed_deals']}</td>
<td style="padding:9px 6px;text-align:center;color:{t20_c};">{d['top20_pct']}%</td>
<td style="padding:9px 6px;text-align:center;">{d['refund_rate']}%</td>
<td style="padding:9px 6px;text-align:center;">{d['team_roi']}%</td>
</tr>'''

        # 趋势
        th = "".join(
            f'<th style="padding:7px;text-align:center;color:#94a3b8;font-size:11px;'
            f'font-weight:400;border-bottom:1px solid #f1f5f9;">{t["dt"][-5:]}</th>'
            for t in trends
        )

        def tr_row(label, key, fmt=",.0f", pre="¥", pct=False):
            cells = ""
            vals = [t[key] for t in trends]
            mx = max(vals) if vals else 0
            for t in trends:
                v = t[key]
                s = f"{v:.1f}%" if pct else f"{pre}{v:{fmt}}"
                bold = "font-weight:600;color:#dc2626;" if v == mx else ""
                cells += f'<td style="padding:7px;text-align:center;font-size:12px;{bold}">{s}</td>'
            return f'<tr><td style="padding:7px 12px;font-size:12px;color:#64748b;">{label}</td>{cells}</tr>'

        # 分离全局级与部门级发现
        dc_count = len(report.data_collision_findings)
        lc_count = len(report.logic_collision_findings)

        def render_finding_card(f):
            bg = {"P0": "#fef2f2", "P1": "#fffbeb", "P2": "#eff6ff"}.get(f.priority, "#f8fafc")
            bc = {"P0": "#dc2626", "P1": "#d97706", "P2": "#2563eb"}.get(f.priority, "#94a3b8")
            if f.collision_type.startswith("cross_domain"):
                engine_badge, engine_color = "跨领域", "#7c3aed"
            elif f.collision_type in ("metric_x_metric", "metric_x_time", "metric_x_entity",
                                      "entity_x_entity", "funnel_x_benchmark"):
                engine_badge, engine_color = "数据对撞", "#6366f1"
            else:
                engine_badge, engine_color = "逻辑对撞", "#059669"

            refs_html = ""
            if f.knowledge_refs:
                refs_html = ('<div style="font-size:10px;color:#94a3b8;margin-top:4px;">'
                             f'📚 {" · ".join(f.knowledge_refs[:3])}</div>')
            recs_html = ""
            if f.recommendations:
                recs_items = "".join(f'<li>{r}</li>' for r in f.recommendations[:3])
                recs_html = (f'<div style="font-size:11px;color:#475569;margin-top:6px;">'
                             f'<ul style="margin:0;padding-left:16px;">{recs_items}</ul></div>')
            mgr_html = ""
            if f.manager_name and f.management_gap:
                mgr_html = (f'<div style="font-size:11px;color:#b45309;margin-top:6px;'
                            f'padding:6px 10px;background:#fef3c7;border-radius:4px;">'
                            f'<strong>管理视角评估 [{f.manager_name}]</strong>: {f.management_gap}</div>')

            return f'''<div style="padding:14px 16px;margin-bottom:10px;border-radius:8px;
background:{bg};border-left:3px solid {bc};">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
<div>
<span style="font-size:10px;font-weight:700;color:#fff;background:{bc};
padding:1px 8px;border-radius:4px;margin-right:6px;">{f.priority}</span>
<span style="font-size:9px;color:#fff;background:{engine_color};
padding:1px 6px;border-radius:3px;margin-right:6px;">{engine_badge}</span>
<span style="font-size:13px;font-weight:600;color:#1e293b;">{f.tag}</span>
</div>
{f'<span style="font-size:13px;font-weight:700;color:#dc2626;">+¥{f.revenue_impact:,}/日</span>' if f.revenue_impact > 0 else ''}
</div>
<div style="font-size:12px;color:#475569;line-height:1.6;">{f.description}</div>
{recs_html}{mgr_html}{refs_html}</div>'''

        global_findings = [f for f in all_findings if f.scope == "global"]
        dept_findings = [f for f in all_findings if f.scope == "dept"]

        global_html = "".join(render_finding_card(f) for f in global_findings)

        from collections import defaultdict as _dd
        dept_grouped = _dd(list)
        for f in dept_findings:
            dept_grouped[f.dept_name].append(f)

        dept_sections_html = ""
        for dn in sorted(dept_grouped.keys()):
            mgr = self.managers.get(dn, "")
            mgr_label = f" · 负责人: {mgr}" if mgr else ""
            cards = "".join(render_finding_card(f) for f in dept_grouped[dn])
            dept_sections_html += f'''<div style="margin-bottom:16px;">
<div style="font-size:13px;font-weight:700;color:#0f172a;padding:8px 12px;
background:#f1f5f9;border-radius:6px;margin-bottom:8px;">
{dn}{mgr_label}</div>
{cards}</div>'''

        # 假设验证
        hypo_html = ""
        for h in report.hypotheses:
            verdict_color = {"支持": "#16a34a", "推翻": "#dc2626"}.get(h["verdict"], "#d97706")
            support = "<br>".join(f'✓ {e}' for e in h.get("support_evidence", []))
            reject = "<br>".join(f'✗ {e}' for e in h.get("reject_evidence", []))
            hypo_html += f'''<div style="padding:12px;margin-bottom:8px;border-radius:8px;
background:#f8fafc;border:1px solid #e2e8f0;">
<div style="font-size:13px;font-weight:600;color:#1e293b;margin-bottom:6px;">
{h["id"]}: {h["hypothesis"]}
<span style="font-size:11px;font-weight:700;color:{verdict_color};
margin-left:8px;padding:1px 8px;background:{verdict_color}22;border-radius:4px;">{h["verdict"]}</span>
</div>
<div style="font-size:11px;color:#475569;line-height:1.6;">
{f'<div style="color:#16a34a;">{support}</div>' if support else ''}
{f'<div style="color:#dc2626;">{reject}</div>' if reject else ''}
{f'<div style="color:#d97706;margin-top:3px;">替代解释: {h["alternative"]}</div>' if h.get("alternative") else ''}
</div></div>'''

        # 因果链
        chain_html = ""
        for chain in report.causal_chains:
            if chain.get("direction") == "正向":
                nodes_html = ""
                for node in chain.get("nodes", []):
                    nc = "#dc2626" if node["status"] == "warning" else "#16a34a"
                    nodes_html += (
                        f'<div style="display:inline-flex;align-items:center;margin-right:4px;">'
                        f'<div style="padding:6px 12px;border-radius:6px;border:2px solid {nc};'
                        f'font-size:11px;"><strong>{node["name"]}</strong><br>'
                        f'<span style="color:#64748b;font-size:10px;">{node["value"]}</span></div>'
                        f'<span style="margin:0 4px;color:#94a3b8;">→</span></div>'
                    )
                chain_html += f'''<div style="margin-bottom:12px;">
<div style="font-size:12px;font-weight:600;color:#1e293b;margin-bottom:6px;">{chain["name"]}</div>
<div style="overflow-x:auto;white-space:nowrap;">{nodes_html}</div>
{f'<div style="font-size:11px;color:#dc2626;margin-top:6px;">⚡ {chain.get("diagnosis","")}</div>' if chain.get("diagnosis") else ''}
</div>'''

        # 漏斗
        funnel_html = ""
        for stage, val, bench, unit in report.funnel:
            pct = min(100, max(8, val / (bench or 1) * 50))
            c = "#dc2626" if val < bench * 0.8 else "#d97706" if val < bench else "#16a34a"
            funnel_html += f'''<div style="margin-bottom:12px;">
<div style="display:flex;justify-content:space-between;font-size:12px;color:#64748b;margin-bottom:3px;">
<span>{stage}</span><span>{val:.1f} (标杆 {bench})</span></div>
<div style="background:#f1f5f9;border-radius:3px;height:8px;">
<div style="background:{c};height:8px;border-radius:3px;width:{pct}%;"></div></div></div>'''

        # 改善建议(含时间维度执行指令)
        imp_html = ""
        for item in report.improvements:
            bc = {"P0": "#dc2626", "P1": "#d97706", "P2": "#2563eb"}.get(item["p"], "#94a3b8")
            refs_str = ""
            if item.get("refs"):
                refs_str = f'<div style="font-size:10px;color:#94a3b8;margin-top:2px;">📚 {" · ".join(item["refs"][:2])}</div>'

            deploy = item.get("deploy_date", "")
            target = item.get("target_entity", "")
            daily = item.get("daily_action", "")
            dur = item.get("duration_days", 0)
            ms = item.get("milestone", "")

            time_html = ""
            if deploy and daily:
                time_html = f'''<div style="margin-top:8px;padding:8px 10px;background:#f0fdf4;
border-radius:6px;border:1px solid #bbf7d0;font-size:11px;color:#166534;">
<div style="font-weight:700;margin-bottom:3px;">执行指令</div>
<div>部署日期: {deploy} | 对象: {target}</div>
<div>每日执行: {daily}</div>
<div>坚持周期: {dur}天 | 里程碑: {ms}</div>
</div>'''

            feas = item.get("feasibility", "high")
            dep = item.get("dependency", "self_contained")
            rnotes = item.get("risk_notes", "")
            feas_color = {"high": "#16a34a", "medium": "#d97706", "low": "#dc2626"}.get(feas, "#94a3b8")
            feas_label = {"high": "高可行", "medium": "中可行", "low": "低可行"}.get(feas, feas)
            dep_label = {"self_contained": "自闭环", "cross_dept": "跨部门依赖", "budget_required": "需预算"}.get(dep, dep)
            feasibility_html = f'''<div style="margin-top:6px;padding:6px 10px;background:{feas_color}11;
border-radius:5px;border:1px solid {feas_color}33;font-size:11px;display:flex;align-items:center;gap:8px;">
<span style="font-weight:700;color:{feas_color};white-space:nowrap;">可行性: {feas_label}</span>
<span style="color:#64748b;">|</span>
<span style="color:#475569;">{dep_label}</span>
<span style="color:#64748b;">|</span>
<span style="color:#64748b;">{rnotes}</span>
</div>'''

            imp_html += f'''<div style="display:flex;gap:14px;padding:16px 0;
border-bottom:1px solid #f1f5f9;align-items:flex-start;">
<div style="min-width:32px;height:32px;background:{bc};color:#fff;border-radius:6px;
display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;">{item["p"]}</div>
<div style="flex:1;min-width:0;">
<div style="font-size:14px;font-weight:600;color:#1e293b;margin-bottom:4px;">{item["title"]}</div>
<div style="font-size:12px;color:#64748b;margin-bottom:3px;">{item["cur"]} → {item["tgt"]}</div>
<div style="font-size:12px;color:#475569;">{item["act"]}</div>
<div style="font-size:11px;color:#94a3b8;margin-top:2px;">{item["detail"]}</div>
{time_html}{feasibility_html}{refs_str}
</div>
<div style="min-width:90px;text-align:right;">
<div style="font-size:10px;color:#94a3b8;">日增量</div>
<div style="font-size:16px;font-weight:700;color:#dc2626;">+¥{item["rev"]:,}</div>
<div style="font-size:10px;color:#94a3b8;">月+¥{item["rev"]*30/10000:.1f}万</div>
</div></div>'''

        # 司龄分析
        tenure_html = ""
        for bucket in ["新人(≤3月)", "成长期(4-12月)", "成熟期(1-2年)", "老员工(>2年)"]:
            if bucket in report.tenure_analysis:
                t = report.tenure_analysis[bucket]
                tenure_html += f'''<tr><td style="padding:8px 12px;">{bucket}</td>
<td style="padding:8px;text-align:center;">{t['count']}人</td>
<td style="padding:8px;text-align:right;font-weight:600;">¥{t['avg_rev']:,}</td>
<td style="padding:8px;text-align:center;">{t['avg_ai']}</td>
<td style="padding:8px;text-align:center;">{t.get('avg_dials','-')}</td></tr>'''

        # 个人排名
        def person_rows(ps, top=True):
            r = ""
            for i, p in enumerate(ps):
                bg = "#f8fafc" if i % 2 == 0 else "#fff"
                c = "#16a34a" if top else "#94a3b8"
                r += f'''<tr style="background:{bg};"><td style="padding:7px 10px;">{i + 1}</td>
<td style="padding:7px 6px;">{p['rep_name']}</td>
<td style="padding:7px 6px;">{p['dept_name']}</td>
<td style="padding:7px 6px;text-align:center;">{p['tenure_months']}月</td>
<td style="padding:7px 6px;text-align:right;color:{c};font-weight:600;">¥{p['revenue']:,.0f}</td>
<td style="padding:7px 6px;text-align:center;">{p['signed_deals']}</td>
<td style="padding:7px 6px;text-align:center;">{p['ai_score']}</td>
<td style="padding:7px 6px;text-align:center;">{p['deep_talk']}</td></tr>'''
            return r

        # 新人追踪
        new_rows = ""
        for n in report.new_hire_stats:
            ratio = round(n["new_avg"] / (n["pc"] or 1) * 100, 1)
            c = "#dc2626" if ratio < 50 else "#d97706" if ratio < 70 else "#16a34a"
            new_rows += (
                f'<tr><td style="padding:7px 12px;">{n["dept_name"]}</td>'
                f'<td style="padding:7px;text-align:center;">{n["new_hire"]}人</td>'
                f'<td style="padding:7px;text-align:right;">¥{n["new_avg"]:,.0f}</td>'
                f'<td style="padding:7px;text-align:right;">¥{n["pc"]:,.0f}</td>'
                f'<td style="padding:7px;text-align:center;color:{c};font-weight:600;">'
                f'{ratio}%</td></tr>'
            )

        dc_sum = report.data_collision_summary
        lc_sum = report.logic_collision_summary
        cd_sum = report.cross_domain_summary

        # 跨领域对撞卡片
        cross_domain_html = ""
        for f in report.cross_domain_findings:
            bg = {"P0": "#fef2f2", "P1": "#fdf4ff", "P2": "#f0fdf4"}.get(f.priority, "#f8fafc")
            bc = {"P0": "#dc2626", "P1": "#a855f7", "P2": "#22c55e"}.get(f.priority, "#94a3b8")
            domain_label = f.collision_type.replace("cross_domain:", "")
            refs_html = ""
            if f.knowledge_refs:
                refs_html = ('<div style="font-size:10px;color:#94a3b8;margin-top:4px;">'
                             f'📚 {" · ".join(f.knowledge_refs[:3])}</div>')
            recs_items = "".join(f'<li>{r}</li>' for r in f.recommendations[:3])
            recs_html = (f'<div style="font-size:11px;color:#475569;margin-top:6px;">'
                         f'<ul style="margin:0;padding-left:16px;">{recs_items}</ul></div>')
            uplift_html = ""
            if f.evidence:
                uplift_html = (f'<span style="font-size:11px;color:#a855f7;font-weight:600;">'
                               f'{f.evidence[0]}</span>')

            cross_domain_html += f'''<div style="padding:14px 16px;margin-bottom:10px;border-radius:8px;
background:{bg};border-left:3px solid {bc};">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
<div>
<span style="font-size:10px;font-weight:700;color:#fff;background:{bc};
padding:1px 8px;border-radius:4px;margin-right:6px;">{f.priority}</span>
<span style="font-size:9px;color:#fff;background:#7c3aed;
padding:1px 6px;border-radius:3px;margin-right:6px;">跨领域</span>
<span style="font-size:13px;font-weight:600;color:#1e293b;">{f.tag}</span>
</div>
{uplift_html}
</div>
<div style="font-size:12px;color:#475569;line-height:1.6;">{f.description}</div>
{recs_html}{refs_html}</div>'''

        total_findings = len(all_findings)

        html = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>数据专家诊断 v{self.VERSION} - {report.date}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#f8fafc;color:#1e293b;font-family:-apple-system,"PingFang SC","Helvetica Neue","Microsoft YaHei",sans-serif;line-height:1.5}}
.wrap{{max-width:900px;margin:0 auto;padding:20px 16px}}
.card{{background:#fff;border-radius:10px;padding:24px;margin-bottom:16px;box-shadow:0 1px 2px rgba(0,0,0,.04)}}
.card h2{{font-size:15px;font-weight:700;color:#0f172a;margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid #f1f5f9}}
table{{width:100%;border-collapse:collapse}}
th{{font-size:11px;color:#94a3b8;font-weight:500;padding:8px 6px;text-align:center;border-bottom:1px solid #e2e8f0}}
th:first-child{{text-align:left;padding-left:12px}}
</style></head>
<body><div class="wrap">

<!-- HEADER -->
<div style="background:linear-gradient(135deg,#0f172a,#1e293b);border-radius:12px;padding:28px 32px;margin-bottom:16px;color:#fff;">
<div style="display:flex;justify-content:space-between;align-items:flex-start;">
<div>
<div style="font-size:11px;color:#64748b;letter-spacing:3px;">DATA EXPERT AGENT · V{self.VERSION} · THREE-ENGINE</div>
<div style="font-size:24px;font-weight:700;margin:6px 0 4px;">数据专家诊断报告</div>
<div style="font-size:13px;color:#94a3b8;">
{report.date} · 电销{len(depts)}部门 · {S['head_count']}人(在岗{S['on_duty']}) · 总发现{total_findings}项
</div>
</div>
<div style="text-align:right;">
<div style="font-size:10px;color:#64748b;">知识库</div>
<div style="font-size:18px;font-weight:700;">{self.total_books}</div>
<div style="font-size:10px;color:#64748b;">本 · {self.domains}领域</div>
</div>
</div>
<div style="margin-top:14px;padding-top:10px;border-top:1px solid #334155;">
<div style="display:flex;gap:12px;flex-wrap:wrap;">
<div style="padding:4px 12px;background:#6366f122;border-radius:6px;font-size:11px;color:#818cf8;">
  数据对撞 {dc_sum['total_collisions']}组</div>
<div style="padding:4px 12px;background:#05966922;border-radius:6px;font-size:11px;color:#34d399;">
  逻辑对撞 {lc_sum['total_hypotheses']}假设 · {lc_sum['causal_chains']}因果链</div>
<div style="padding:4px 12px;background:#a855f722;border-radius:6px;font-size:11px;color:#c084fc;">
  跨领域对撞 {cd_sum.get('total_collisions',0)}组 · {cd_sum.get('domains_count',0)}领域</div>
</div>
<div style="font-size:10px;color:#475569;margin-top:8px;">
方法论: SPIN Selling + 挑战式销售 + TOC约束 + 六西格玛 + Hook上瘾模型 + 进化心理学 + 贝叶斯迭代 + 损失厌恶
</div>
</div></div>

<!-- KPI -->
<div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap;">
<div style="flex:1;min-width:140px;background:#fff;border-radius:10px;padding:18px;box-shadow:0 1px 2px rgba(0,0,0,.04);">
<div style="font-size:10px;color:#94a3b8;letter-spacing:1px;">总营收</div>
<div style="font-size:24px;font-weight:800;color:#dc2626;margin:4px 0;">¥{S['total_revenue']/10000:.1f}<span style="font-size:12px;font-weight:400;">万</span></div>
<div>{arrow(S.get('rev_dod',0))}</div><div style="margin-top:6px;">{rev_sp}</div></div>
<div style="flex:1;min-width:140px;background:#fff;border-radius:10px;padding:18px;box-shadow:0 1px 2px rgba(0,0,0,.04);">
<div style="font-size:10px;color:#94a3b8;letter-spacing:1px;">人均产值</div>
<div style="font-size:24px;font-weight:800;color:#0f172a;margin:4px 0;">¥{S['pc']:,}</div>
<div>{arrow(S.get('pc_dod',0))}</div><div style="margin-top:6px;">{pc_sp}</div></div>
<div style="flex:1;min-width:140px;background:#fff;border-radius:10px;padding:18px;box-shadow:0 1px 2px rgba(0,0,0,.04);">
<div style="font-size:10px;color:#94a3b8;letter-spacing:1px;">接通率</div>
<div style="font-size:24px;font-weight:800;color:{'#dc2626' if S['cr']<43 else '#16a34a'};margin:4px 0;">{S['cr']}%</div>
<div style="font-size:11px;">红线43% {'⚠' if S['cr']<43 else '✓'}</div><div style="margin-top:6px;">{cr_sp}</div></div>
<div style="flex:1;min-width:140px;background:#fff;border-radius:10px;padding:18px;box-shadow:0 1px 2px rgba(0,0,0,.04);">
<div style="font-size:10px;color:#94a3b8;letter-spacing:1px;">转化率</div>
<div style="font-size:24px;font-weight:800;color:#0f172a;margin:4px 0;">{S['conv']}%</div>
<div style="font-size:11px;">签单{S['signed_deals']}笔</div><div style="margin-top:6px;">{conv_sp}</div></div>
</div>

<!-- 经营背景提示条 -->
<div style="background:linear-gradient(135deg,#f0f9ff,#e0f2fe);border-radius:10px;padding:14px 20px;margin-bottom:16px;
border:1px solid #0ea5e944;display:flex;align-items:center;gap:14px;">
<div style="font-size:28px;">📊</div>
<div style="flex:1;">
<div style="font-size:12px;font-weight:700;color:#0c4a6e;margin-bottom:3px;">
建议原则: 弱依赖 · 强闭环 · 轻投入 · 快见效</div>
<div style="font-size:11px;color:#075985;line-height:1.6;">
所有改善建议均经可行性校验，优先推荐业务团队可自行落地的方案，确保务实可执行。
</div>
</div>
</div>

<!-- 漏斗 -->
<div class="card">
<h2>转化漏斗 (Dial→Connect→Conversation→Close)</h2>
{funnel_html}
</div>

<!-- 全局诊断(全部门级别) -->
<div class="card">
<h2>🔬 全局诊断 · {len(global_findings)}项发现(全部门级别汇总)</h2>
<div style="font-size:11px;color:#64748b;margin-bottom:12px;">
以下发现基于全部门数据汇总分析，属于团队整体层面问题，非针对单一部门。
</div>
{global_html}
</div>

<!-- 部门级诊断(按部门+负责人) -->
<div class="card">
<h2>📋 部门级诊断 · {len(dept_findings)}项发现(按部门归属)</h2>
<div style="font-size:11px;color:#64748b;margin-bottom:12px;">
以下发现针对具体部门，关联负责人姓名，并推断管理视角缺失。
</div>
{dept_sections_html}
</div>

<!-- 假设验证 -->
<div class="card">
<h2>🧠 假设验证台(逻辑对撞核心)</h2>
{hypo_html}
</div>

<!-- 因果链 -->
<div class="card">
<h2>⛓ 因果链追溯</h2>
{chain_html}
</div>

<!-- 跨领域对撞 -->
<div class="card">
<h2>🌐 跨领域对撞 · {cd_sum.get('total_collisions',0)}组碰撞 × {cd_sum.get('domains_count',0)}个领域</h2>
<div style="display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap;">
{''.join(f'<span style="padding:4px 10px;background:#7c3aed22;border-radius:4px;font-size:10px;color:#7c3aed;">{d}</span>' for d in cd_sum.get('domains_used',[]))}
</div>
{cross_domain_html}
</div>

<!-- 7日趋势 -->
<div class="card" style="overflow-x:auto;">
<h2>7日趋势</h2>
<table style="min-width:600px;"><thead><tr>
<th style="text-align:left;padding-left:12px;">指标</th>{th}</tr></thead><tbody>
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
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;
padding-bottom:8px;border-bottom:1px solid #f1f5f9;">
<h2 style="margin:0;padding:0;border:0;">改善建议与增量预估</h2>
<div style="background:#fef2f2;padding:4px 14px;border-radius:16px;font-size:12px;">
全部落地 <strong style="color:#dc2626;font-size:16px;margin:0 4px;">
+¥{report.total_uplift:,}/日</strong> (月+¥{report.total_uplift*30/10000:.1f}万)
</div></div>
{imp_html}
</div>

<!-- 司龄分析 -->
<div class="card">
<h2>司龄-产能成长曲线</h2>
<table><thead><tr>
<th style="text-align:left;padding-left:12px;">阶段</th>
<th>人数</th><th style="text-align:right;">人均产值</th><th>AI均分</th><th>人均拨打</th>
</tr></thead><tbody>{tenure_html}</tbody></table>
<div style="font-size:11px;color:#94a3b8;margin-top:8px;">
* 产能曲线：新人爬坡→成长期冲刺→成熟期巅峰→老员工可能衰减。关注断崖和倦怠点。</div>
</div>

<!-- 部门排名 -->
<div class="card" style="overflow-x:auto;">
<h2>部门排名(按营收降序)</h2>
<table style="font-size:12px;min-width:800px;"><thead><tr>
<th style="text-align:left;padding-left:12px;">部门</th><th style="text-align:right;">营收</th>
<th style="text-align:right;">人均</th><th>接通率</th><th>深沟率</th><th>AI</th>
<th>转化率</th><th>签单</th><th>TOP20%</th><th>退费率</th><th>ROI</th>
</tr></thead><tbody>{dept_rows}</tbody></table></div>

<!-- 新人追踪 -->
<div class="card">
<h2>新人成长追踪</h2>
<table style="font-size:12px;"><thead><tr>
<th style="text-align:left;padding-left:12px;">部门</th><th>新人数</th>
<th style="text-align:right;">新人均产</th><th style="text-align:right;">全员均产</th>
<th>达标率</th></tr></thead><tbody>{new_rows}</tbody></table>
</div>

<!-- TOP & BOTTOM -->
<div class="card" style="overflow-x:auto;">
<h2>个人 TOP10</h2>
<table style="font-size:12px;"><thead><tr>
<th>#</th><th style="text-align:left;">姓名</th><th style="text-align:left;">部门</th>
<th>司龄</th><th style="text-align:right;">营收</th><th>签单</th><th>AI</th><th>深沟</th>
</tr></thead><tbody>{person_rows(report.top_performers)}</tbody></table></div>

<div class="card" style="overflow-x:auto;">
<h2>个人 BOTTOM10</h2>
<table style="font-size:12px;"><thead><tr>
<th>#</th><th style="text-align:left;">姓名</th><th style="text-align:left;">部门</th>
<th>司龄</th><th style="text-align:right;">营收</th><th>签单</th><th>AI</th><th>深沟</th>
</tr></thead><tbody>{person_rows(report.bottom_performers, False)}</tbody></table></div>

<!-- 因果链综合诊断 -->
<div class="card">
<h2>因果链综合诊断</h2>
<div style="font-size:13px;line-height:1.9;color:#475569;">
<strong style="color:#0f172a;">资源端</strong> 日分配{S['allocated']:,}条 · 分配率{S['alloc_rate']*100:.0f}%<br>
<strong style="color:#0f172a;">触达端</strong> 拨打{S['dial_count']:,}次(人均{S['dial_count']//S['on_duty']}通) · 接通{S['link_1d_num']:,}通({S['cr']}%)<br>
<strong style="color:#0f172a;">转化端</strong> 深沟{S['deep_talk']:,}通(深沟率{S['dr']}%) · AI均分{S['ai']} · 转化{S['conv']}%<br>
<strong style="color:#0f172a;">产出端</strong> 签单{S['signed_deals']}笔 · 客单价¥{S['avg_deal']:,} · 总营收¥{S['total_revenue']:,.0f} · 人均¥{S['pc']:,}<br>
<strong style="color:#0f172a;">质量端</strong> 退费{S['refund_count']}笔(¥{S['refund_amount']:,.0f} · {S['ref_rate']}%) · 投诉{S['complaint_count']}件<br>
<strong style="color:#0f172a;">协同端</strong> 建信转入{S['jx_transfer_in']}条→{S['jx_signed']}单({S['jx_cr']}%) · 公海{S['pool_retrieval']}条→{S['pool_signed']}单({S['p_cr']}%)<br>
<strong style="color:#0f172a;">效率端</strong> 黄金时段{S['peak_pct']}%营收 · 部门CV={report.pc_cv} · TOP20%占{S['t20']}%
</div></div>

<div style="text-align:center;color:#cbd5e1;font-size:10px;padding:16px 0;">
数据专家智能体 v{self.VERSION} · {report.date}
· 三引擎: 数据对撞({dc_sum['total_collisions']}组) + 逻辑对撞({lc_sum['total_hypotheses']}组假设)
+ 跨领域对撞({cd_sum.get('total_collisions',0)}组 · {cd_sum.get('domains_count',0)}领域)
· 知识库{self.total_books}本 · {self.domains}个领域
</div>
</div></body></html>'''

        return html

    def export(self, report: AnalysisReport, filename: str = None,
               open_browser: bool = True) -> str:
        """导出HTML报告"""
        if filename is None:
            filename = f"DataExpert_Report_{report.date}.html"

        if not os.path.isabs(filename):
            filename = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                filename
            )

        html = self.render_html(report)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)

        if open_browser:
            webbrowser.open("file://" + os.path.realpath(filename))

        return filename

    def get_findings_json(self, report: AnalysisReport) -> list:
        """获取所有发现的JSON格式(供主程序调用)"""
        all_f = report.get_all_findings_sorted()
        return [f.to_dict() for f in all_f]

    def get_improvements_json(self, report: AnalysisReport) -> list:
        """获取改善建议JSON格式(供主程序调用)"""
        return report.improvements

    def send_email(self, report: AnalysisReport, to: str = "zhao.can@zhenai.com",
                   cc: str = "xiaoying.tian@zhenai.com") -> bool:
        """通过SMTP发送报告邮件"""
        S = report.summary
        a = "↑" if S.get("rev_dod", 0) > 0 else "↓"
        subj = (f"【电销体检】{report.date[-5:].replace('-','月')}日 — "
                f"¥{S['total_revenue']/10000:.1f}万({a}{abs(S.get('rev_dod',0))}%) "
                f"人均¥{S['pc']:,} 接通{S['cr']}% "
                f"[数据对撞{report.data_collision_summary['total_collisions']}组"
                f"+逻辑对撞{report.logic_collision_summary['total_hypotheses']}组]")

        html = self.render_html(report)
        return send_report_email(subj, html, to=to, cc=cc)

    def run_full_pipeline(self, date: str, send_mail: bool = True,
                          open_browser: bool = True) -> AnalysisReport:
        """一键运行完整流程：分析→报告→邮件"""
        print(f"{'═'*50}")
        print(f"  数据专家智能体 v{self.VERSION}")
        print(f"  知识库: {self.total_books}本 · {self.domains}个领域")
        print(f"{'═'*50}")

        print(f"\n[1/4] 数据分析 + 三引擎对撞...")
        report = self.analyze(date)
        dc = report.data_collision_summary
        lc = report.logic_collision_summary
        cd = report.cross_domain_summary
        S = report.summary
        print(f"  营收 ¥{S['total_revenue']/10000:.1f}万 | 人均 ¥{S['pc']:,} | 接通 {S['cr']}%")
        print(f"  [引擎1] 数据对撞: {dc['total_collisions']}组")
        print(f"  [引擎2] 逻辑对撞: {lc['total_hypotheses']}组假设 + {lc['causal_chains']}因果链")
        print(f"  [引擎3] 跨领域对撞: {cd.get('total_collisions',0)}组 × {cd.get('domains_count',0)}领域")
        print(f"  总发现: {len(report.get_all_findings_sorted())}项 | "
              f"改善建议: {len(report.improvements)}条")

        # 校验
        assert all("电销" in d["dept_name"] for d in report.departments), "非电销部门数据泄漏"
        dept_sum = sum(d["total_revenue"] for d in report.departments)
        assert abs(dept_sum - S["total_revenue"]) < 1, "营收校验失败"
        print("  数据校验 ✓")

        print(f"\n[2/4] 生成HTML报告...")
        path = self.export(report, f"DataExpert_{date}.html", open_browser=open_browser)
        print(f"  {path}")

        if send_mail:
            print(f"\n[3/4] 发送邮件...")
            ok = self.send_email(report)
            print(f"  {'成功' if ok else '失败'}")
        else:
            print(f"\n[3/4] 跳过邮件发送")

        print(f"\n[4/4] 高管摘要:")
        print(self.get_executive_summary(report))

        return report

    def __repr__(self):
        return (f"<DataExpert v{self.VERSION} "
                f"知识库={self.total_books}本/{self.domains}领域 "
                f"引擎=数据对撞+逻辑对撞>")
