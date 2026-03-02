# -*- coding: utf-8 -*-
"""情景记忆管理器 — SQLite存储每日报告摘要，支持历史趋势对比"""
import json, sqlite3, os
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "memory.db"


class ReportMemory:
    def __init__(self, db_path=None):
        self.db_path = str(db_path or DB_PATH)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS report_episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team TEXT NOT NULL, date TEXT NOT NULL,
                metrics TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(team, date))""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_team_date ON report_episodes(team, date DESC)")

    def save(self, team, date, metrics: dict):
        with self._conn() as conn:
            conn.execute("""INSERT INTO report_episodes (team, date, metrics)
                VALUES (?, ?, ?) ON CONFLICT(team, date) DO UPDATE SET
                metrics = excluded.metrics, created_at = CURRENT_TIMESTAMP""",
                (team, date, json.dumps(metrics, ensure_ascii=False)))

    def recall(self, team, days=7, before_date=None):
        with self._conn() as conn:
            if before_date:
                rows = conn.execute("SELECT date, metrics FROM report_episodes WHERE team=? AND date<? ORDER BY date DESC LIMIT ?",
                    (team, before_date, days)).fetchall()
            else:
                rows = conn.execute("SELECT date, metrics FROM report_episodes WHERE team=? ORDER BY date DESC LIMIT ?",
                    (team, days)).fetchall()
        return [{"date": r[0], "metrics": json.loads(r[1])} for r in rows]

    def trend_comparison_html(self, team, today_date, today_metrics: dict,
                               metric_labels: dict = None, days=7):
        history = self.recall(team, days=days, before_date=today_date)
        if not history:
            return ""
        if not metric_labels:
            metric_labels = {k: k for k in today_metrics}

        yesterday = history[0] if history else None
        week_data = history[:7]

        html = '<div class="card" style="border-left:4px solid #6366f1;margin-top:18px;">'
        html += '<h2>历史趋势对比（情景记忆）</h2>'
        html += f'<div style="font-size:11px;color:#64748b;margin-bottom:12px;">基于最近 {len(history)} 天的历史数据自动对比</div>'
        html += '<table style="width:100%;border-collapse:collapse;font-size:12px;"><thead><tr style="background:#f1f5f9;">'
        html += '<th style="padding:6px 8px;text-align:left;border-bottom:2px solid #e2e8f0;">指标</th>'
        html += '<th style="padding:6px 8px;text-align:right;border-bottom:2px solid #e2e8f0;">今日</th>'
        if yesterday:
            yd = yesterday["date"]
            yd_d = f"{yd[:4]}-{yd[4:6]}-{yd[6:]}" if len(yd) == 8 else yd
            html += f'<th style="padding:6px 8px;text-align:right;border-bottom:2px solid #e2e8f0;">昨日({yd_d})</th>'
            html += '<th style="padding:6px 8px;text-align:right;border-bottom:2px solid #e2e8f0;">环比</th>'
        if len(week_data) >= 3:
            html += f'<th style="padding:6px 8px;text-align:right;border-bottom:2px solid #e2e8f0;">{len(week_data)}日均值</th>'
            html += '<th style="padding:6px 8px;text-align:right;border-bottom:2px solid #e2e8f0;">vs均值</th>'
        html += '</tr></thead><tbody>'

        for key, label in metric_labels.items():
            tv = today_metrics.get(key, 0) or 0
            html += '<tr style="border-bottom:1px solid #f1f5f9;">'
            html += f'<td style="padding:5px 8px;font-weight:500;">{label}</td>'
            html += f'<td style="padding:5px 8px;text-align:right;">{self._fmt(tv)}</td>'
            if yesterday:
                yv = yesterday["metrics"].get(key, 0) or 0
                chg = self._chg(tv, yv)
                c = self._tc(chg, key)
                a = "↑" if chg > 0 else "↓" if chg < 0 else "→"
                html += f'<td style="padding:5px 8px;text-align:right;">{self._fmt(yv)}</td>'
                html += f'<td style="padding:5px 8px;text-align:right;color:{c};font-weight:600;">{a}{abs(chg):.1f}%</td>'
            if len(week_data) >= 3:
                vals = [ep["metrics"].get(key, 0) or 0 for ep in week_data]
                avg = sum(vals) / len(vals) if vals else 0
                ca = self._chg(tv, avg)
                cc = self._tc(ca, key)
                aa = "↑" if ca > 0 else "↓" if ca < 0 else "→"
                html += f'<td style="padding:5px 8px;text-align:right;">{self._fmt(avg)}</td>'
                html += f'<td style="padding:5px 8px;text-align:right;color:{cc};font-weight:600;">{aa}{abs(ca):.1f}%</td>'
            html += '</tr>'
        html += '</tbody></table></div>'
        return html

    @staticmethod
    def _chg(new, old):
        if old == 0: return 0 if new == 0 else 100
        return (new - old) / abs(old) * 100

    @staticmethod
    def _tc(pct, key=""):
        neg_good = key in ("refund_rate", "refund", "order_fail_rate")
        if neg_good:
            return "#16a34a" if pct < -5 else "#dc2626" if pct > 5 else "#64748b"
        return "#16a34a" if pct > 5 else "#dc2626" if pct < -5 else "#64748b"

    @staticmethod
    def _fmt(val):
        if isinstance(val, float):
            if abs(val) >= 10000: return f"{val/10000:.1f}万"
            if abs(val) >= 1: return f"{val:.1f}"
            return f"{val:.2f}"
        return str(val)
