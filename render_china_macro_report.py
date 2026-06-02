"""
HTML 渲染器：把 generate_china_macro_report.py 的数据结构渲染成报告
输出：reports/China_Enterprise_Living_Diagnosis_2026-06-01.html
"""
import os
import datetime as dt
from generate_china_macro_report import (
    REPORT_DATE, REPORT_TITLE, SUBTITLE,
    ENTERPRISE_DATA, PEOPLE_DATA, ZHENAI_IMPACT,
    STRATEGIC_PATHS, ZHAO_REVIEW,
)

COLOR_MAP = {
    "red": ("#ff4b4b", "#fff3f3"),
    "yellow": ("#f9a825", "#fffbe6"),
    "green": ("#00c853", "#e8f8ee"),
}


def card(title, value, ref, trend, color, verdict, source):
    border, bg = COLOR_MAP.get(color, COLOR_MAP["yellow"])
    return f"""
    <div class="card" style="border-top-color:{border};">
        <div class="card-title">{title}</div>
        <div class="card-value" style="color:{border};">{value}</div>
        <div class="card-ref">{ref}</div>
        <div class="card-trend">{trend}</div>
        <div class="card-verdict" style="background:{bg};border-left:4px solid {border};">{verdict}</div>
        <div class="card-source">📎 {source}</div>
    </div>"""


def section_grid(title, subtitle, items_dict):
    cards_html = "\n".join(
        card(d["title"], d["value"], d["ref"], d["trend"], d["color"], d["verdict"], d["source"])
        for d in items_dict.values()
    )
    return f"""
    <section>
        <h2>{title}</h2>
        <p class="section-sub">{subtitle}</p>
        <div class="grid">{cards_html}</div>
    </section>"""


def impact_table(items):
    rows = "\n".join(
        f"""<tr>
            <td>{it['weight']}</td>
            <td><b>{it['macro']}</b></td>
            <td>{it['channel']}</td>
            <td style="color:#b71c1c;">{it['zhenai']}</td>
        </tr>"""
        for it in items
    )
    return f"""
    <section>
        <h2>三、宏观 → 珍爱网传导映射</h2>
        <p class="section-sub">把上面的国家数据，翻译成对珍爱网经营的具体影响。</p>
        <table class="impact-table">
            <thead><tr>
                <th style="width:8%;">权重</th>
                <th style="width:28%;">宏观信号</th>
                <th style="width:24%;">传导路径</th>
                <th style="width:40%;">对珍爱网的具体影响</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </section>"""


def strategy_paths(paths):
    cards = []
    for p in paths:
        logic_html = "".join(f"<li>{x}</li>" for x in p["logic"])
        red_html = "".join(f"<li>{x}</li>" for x in p["fit_redlines"])
        c = f"""
        <div class="path-card">
            <div class="path-name">{p['name']}</div>
            <div class="path-thesis">📌 核心主张：{p['thesis']}</div>
            <div class="path-block">
                <div class="path-block-title">推演逻辑</div>
                <ol>{logic_html}</ol>
            </div>
            <div class="path-block">
                <div class="path-block-title">红线一致性自检</div>
                <ul class="redline">{red_html}</ul>
            </div>
            <div class="path-kpi">
                <div><span class="lbl">预估收益</span><span class="val">{p['expected']}</span></div>
                <div><span class="lbl">风险等级</span><span class="val">{p['risk']}</span></div>
            </div>
        </div>"""
        cards.append(c)
    return f"""
    <section>
        <h2>四、三条战略路径推演</h2>
        <p class="section-sub">基于上述宏观+经营数据，为下一步给出三条可选路径，按推荐度排序。</p>
        {"".join(cards)}
    </section>"""


def zhao_review(rv):
    rows = "".join(
        f"""<div class="qa">
            <div class="q">❓ 质疑 {i+1}：{q}</div>
            <div class="a">✅ 应对：{a}</div>
        </div>"""
        for i, (q, a) in enumerate(rv["doubts"])
    )
    return f"""
    <section>
        <h2>五、虚拟赵总质疑 & 应对</h2>
        <p class="section-sub">按"虚拟赵总"规则，重大方案输出前先自我质疑，逐条回应。</p>
        {rows}
        <div class="final-decision">📣 请赵总决断：建议 T+0 立即启动 <b>路径A（存量深耕）</b>；T+30天根据A的成效在 B/C 中二选一加码。</div>
    </section>"""


def header():
    return f"""
    <div class="header">
        <h1>{REPORT_TITLE}</h1>
        <p class="sub">{SUBTITLE}</p>
        <div class="meta">
            <span>报告日期：{REPORT_DATE.strftime('%Y-%m-%d')}</span>
            <span>编制：智慧助理 Linh</span>
            <span>呈：赵总</span>
            <span>抄送：田小英</span>
        </div>
    </div>"""


def executive_summary():
    return """
    <section class="exec-summary">
        <h2>📌 执行摘要 · 一页看完</h2>
        <ol>
            <li><b>大盘：温和扩张但暗流涌动。</b>制造业PMI 50.3%、规上工业利润+18.2%看上去不错，但服务业PMI跌破荣枯线（49.4%）、长江商学院BCI仅46.9，反映出<b>"政府投资型行业向好、民营消费型行业承压"</b>的鲜明分化。</li>
            <li><b>居民：捂紧钱包+主动去杠杆。</b>Q1住户存款新增7.68万亿，但消费贷净减1,640亿。"赚得多花得少"，<b>大额非必需消费（高客单婚恋）首当其冲</b>。</li>
            <li><b>就业：青年群体仍是重灾区。</b>16-24岁失业率16.3%（高于上年同期15.8%），25-29岁7.4%，<b>正是珍爱网核心客群</b>，这是高客单转化阻力的根本原因。</li>
            <li><b>婚恋赛道：2025反弹是脉冲，2026继续下行。</b>2025年676.3万对（+10.76%）是新《婚姻登记条例》刺激+疫情积压释放，2026 Q1立即回落-6.24%创新低。<b>结构性下行不可逆</b>。</li>
            <li><b>结构性机会：二婚客群池在扩。</b>2025协议离婚274.3万对（+12.2万），叠加诉讼离婚约90万，是高净值、高决策力、低投诉风险的优质客群。</li>
            <li><b>战略结论：</b>从"广撒网拉新"切换到"存量深耕+客群分层"，下一步首推<b>路径A（公海盘活+中腰部补强）</b>，零额外预算、3个月见效。</li>
        </ol>
    </section>"""


def render():
    css = """
    body{font-family:'PingFang SC','Microsoft YaHei',sans-serif;background:#f4f7f9;color:#2c3e50;margin:0;padding:24px;line-height:1.6;}
    .container{max-width:1280px;margin:0 auto;}
    .header{background:linear-gradient(135deg,#c0392b 0%,#8e2820 100%);color:white;padding:36px;border-radius:12px;margin-bottom:24px;box-shadow:0 6px 16px rgba(0,0,0,.12);}
    .header h1{margin:0 0 8px;font-size:30px;}
    .header .sub{margin:0 0 16px;opacity:.92;font-size:16px;}
    .header .meta{display:flex;gap:24px;flex-wrap:wrap;font-size:13px;opacity:.85;}
    section{background:#fff;padding:28px;border-radius:12px;margin-bottom:20px;box-shadow:0 2px 6px rgba(0,0,0,.05);}
    h2{margin:0 0 6px;font-size:22px;color:#1a1a1a;border-bottom:2px solid #e0e0e0;padding-bottom:10px;}
    .section-sub{color:#777;font-size:14px;margin:8px 0 20px;}
    .exec-summary{background:linear-gradient(135deg,#fff8e1 0%,#fff3c4 100%);border-left:6px solid #f39c12;}
    .exec-summary ol{padding-left:24px;}
    .exec-summary li{margin-bottom:10px;font-size:15px;}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;}
    .card{background:#fff;padding:18px;border-radius:10px;border-top:4px solid #ddd;box-shadow:0 1px 3px rgba(0,0,0,.06);}
    .card-title{font-size:14px;color:#666;margin-bottom:6px;}
    .card-value{font-size:28px;font-weight:700;margin-bottom:4px;}
    .card-ref{font-size:12px;color:#888;margin-bottom:4px;}
    .card-trend{font-size:13px;color:#444;margin-bottom:10px;font-weight:600;}
    .card-verdict{padding:10px;border-radius:6px;font-size:13px;line-height:1.5;color:#333;margin-bottom:8px;}
    .card-source{font-size:11px;color:#999;font-style:italic;}
    .impact-table{width:100%;border-collapse:collapse;margin-top:12px;font-size:14px;}
    .impact-table th{background:#34495e;color:white;padding:10px;text-align:left;}
    .impact-table td{padding:12px 10px;border-bottom:1px solid #eee;vertical-align:top;}
    .impact-table tr:hover{background:#fafafa;}
    .path-card{background:linear-gradient(180deg,#fafbff 0%,#fff 100%);border:1px solid #e0e6f0;border-radius:10px;padding:22px;margin-bottom:18px;}
    .path-name{font-size:18px;font-weight:700;color:#2c3e50;margin-bottom:8px;}
    .path-thesis{background:#e8f4fd;border-left:4px solid #2196f3;padding:10px 14px;margin-bottom:14px;font-size:14px;color:#0d47a1;border-radius:4px;}
    .path-block{margin-bottom:12px;}
    .path-block-title{font-weight:700;color:#34495e;margin-bottom:6px;font-size:14px;}
    .path-block ol,.path-block ul{margin:0;padding-left:22px;font-size:14px;color:#444;}
    .path-block ol li,.path-block ul li{margin-bottom:4px;}
    .redline li{list-style:none;margin-left:-18px;margin-bottom:5px;}
    .path-kpi{display:flex;gap:30px;background:#fff8e1;padding:12px 18px;border-radius:6px;border:1px dashed #f39c12;font-size:14px;}
    .path-kpi .lbl{color:#999;margin-right:8px;}
    .path-kpi .val{color:#c0392b;font-weight:700;}
    .qa{background:#f9f9f9;padding:14px;border-radius:8px;margin-bottom:12px;border-left:4px solid #95a5a6;}
    .qa .q{color:#c0392b;font-weight:600;margin-bottom:6px;font-size:14px;}
    .qa .a{color:#2c3e50;font-size:14px;}
    .final-decision{background:linear-gradient(135deg,#27ae60 0%,#1e8449 100%);color:white;padding:18px 22px;border-radius:8px;margin-top:16px;font-size:16px;font-weight:600;text-align:center;}
    .footer{text-align:center;color:#888;margin-top:30px;font-size:12px;line-height:1.8;}
    """

    body = (
        header()
        + executive_summary()
        + section_grid(
            "一、企业生存境况（8项核心指标）",
            "解读维度：景气、利润、信心、出清、负债。最新公开数据截至 2026年4月。",
            ENTERPRISE_DATA,
        )
        + section_grid(
            "二、民众生活境况（11项核心指标）",
            "解读维度：收入、消费、就业、储蓄、婚恋人口。Q1为权威官方统计。",
            PEOPLE_DATA,
        )
        + impact_table(ZHENAI_IMPACT)
        + strategy_paths(STRATEGIC_PATHS)
        + zhao_review(ZHAO_REVIEW)
    )

    footer = """
    <div class="footer">
        本报告由智慧助理 Linh 自动汇编，所有数据来自国家统计局、民政部、央行、市场监管总局、财新、长江商学院等权威公开渠道。<br/>
        每项数据卡片下方均标注📎来源，可追溯。建议每月初固定刷新一次，与珍爱网经营数据对照阅读。<br/>
        <b>下一次自动刷新预定：2026-07-01</b>
    </div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{REPORT_TITLE}</title>
<style>{css}</style>
</head>
<body>
<div class="container">
{body}
{footer}
</div>
</body>
</html>"""

    out_path = f"reports/China_Enterprise_Living_Diagnosis_{REPORT_DATE.strftime('%Y-%m-%d')}.html"
    os.makedirs("reports", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


if __name__ == "__main__":
    path = render()
    print(f"✅ 报告已生成：{path}")
    print(f"   文件大小：{os.path.getsize(path)/1024:.1f} KB")
