"""Regression coverage for AnalysisPipeline._pull_data top/bottom performers.

Covers:
- Empty person set yields empty top/bottom lists
- Fewer than 10 persons: both slices return the full ordered set
- More than 10 persons: top10 is highest revenue, bot10 is lowest revenue

Deterministic stdlib unittest with an in-memory SQLite fixture; no network.
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from agent_system.engines.analysis_pipeline import AnalysisPipeline


DAILY_COLS = (
    "report_date", "dept_name", "head_count", "on_duty", "new_hire",
    "new_hire_month_avg", "allocated", "alloc_rate", "dial_count", "link_1d_num",
    "connect_rate", "avg_call_dur", "avg_connect_dur", "deep_talk",
    "deep_talk_rate", "avg_deep_dur", "avg_ai_score", "first_call_conv",
    "first_call_conv_rate", "signed_deals", "total_revenue", "avg_deal_amount",
    "max_deal", "per_capita_revenue", "conversion_rate", "refund_count",
    "refund_amount", "refund_rate", "complaint_count", "jx_transfer_in",
    "jx_signed", "jx_conv_rate", "pool_in", "pool_retrieval", "pool_signed",
    "pool_conv_rate", "top20_pct", "bottom30_pct", "peak_hour_revenue",
    "offpeak_hour_revenue", "team_roi",
)

PERSON_COLS = (
    "report_date", "dept_name", "rep_name", "tenure_months", "dial_count",
    "link_1d_num", "avg_call_dur", "avg_connect_dur", "deep_talk", "ai_score",
    "signed_deals", "revenue", "refund", "complaint", "peak_revenue",
    "offpeak_revenue", "rank_dept",
)


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"CREATE TABLE ts_daily ({', '.join(f'{c} REAL' if c not in ('report_date','dept_name') else f'{c} TEXT' for c in DAILY_COLS)})"
    )
    conn.execute(
        f"CREATE TABLE ts_person ({', '.join(f'{c} REAL' if c not in ('report_date','dept_name','rep_name') else f'{c} TEXT' for c in PERSON_COLS)})"
    )
    conn.commit()


def _insert_daily(conn: sqlite3.Connection, date: str, dept: str = "电销一部") -> None:
    values = {
        "report_date": date,
        "dept_name": dept,
        "head_count": 10,
        "on_duty": 8,
        "new_hire": 1,
        "new_hire_month_avg": 500,
        "allocated": 100,
        "alloc_rate": 0.9,
        "dial_count": 300,
        "link_1d_num": 45,
        "connect_rate": 45,
        "avg_call_dur": 120,
        "avg_connect_dur": 80,
        "deep_talk": 10,
        "deep_talk_rate": 22,
        "avg_deep_dur": 300,
        "avg_ai_score": 80,
        "first_call_conv": 2,
        "first_call_conv_rate": 4,
        "signed_deals": 3,
        "total_revenue": 9000,
        "avg_deal_amount": 3000,
        "max_deal": 5000,
        "per_capita_revenue": 1125,
        "conversion_rate": 3,
        "refund_count": 0,
        "refund_amount": 0,
        "refund_rate": 0,
        "complaint_count": 0,
        "jx_transfer_in": 0,
        "jx_signed": 0,
        "jx_conv_rate": 0,
        "pool_in": 0,
        "pool_retrieval": 0,
        "pool_signed": 0,
        "pool_conv_rate": 0,
        "top20_pct": 40,
        "bottom30_pct": 10,
        "peak_hour_revenue": 5000,
        "offpeak_hour_revenue": 4000,
        "team_roi": 50,
    }
    cols = ", ".join(DAILY_COLS)
    placeholders = ", ".join("?" for _ in DAILY_COLS)
    conn.execute(
        f"INSERT INTO ts_daily ({cols}) VALUES ({placeholders})",
        [values[c] for c in DAILY_COLS],
    )


def _insert_person(
    conn: sqlite3.Connection,
    date: str,
    name: str,
    revenue: float,
    dept: str = "电销一部",
) -> None:
    values = {
        "report_date": date,
        "dept_name": dept,
        "rep_name": name,
        "tenure_months": 6,
        "dial_count": 40,
        "link_1d_num": 8,
        "avg_call_dur": 100,
        "avg_connect_dur": 70,
        "deep_talk": 2,
        "ai_score": 75,
        "signed_deals": 1 if revenue > 0 else 0,
        "revenue": revenue,
        "refund": 0,
        "complaint": 0,
        "peak_revenue": revenue * 0.6,
        "offpeak_revenue": revenue * 0.4,
        "rank_dept": 1,
    }
    cols = ", ".join(PERSON_COLS)
    placeholders = ", ".join("?" for _ in PERSON_COLS)
    conn.execute(
        f"INSERT INTO ts_person ({cols}) VALUES ({placeholders})",
        [values[c] for c in PERSON_COLS],
    )


class PullDataPerformersTests(unittest.TestCase):
    DATE = "2026-02-27"

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self._tmpdir.name) / "performers.db")
        self.conn = sqlite3.connect(self.db_path)
        _create_schema(self.conn)
        _insert_daily(self.conn, self.DATE)
        self.conn.commit()
        self.pipeline = AnalysisPipeline(self.db_path)

    def tearDown(self):
        self.conn.close()
        self._tmpdir.cleanup()

    def _pull(self):
        return self.pipeline._pull_data(self.DATE, [self.DATE])

    def test_empty_persons_yield_empty_top_and_bottom(self):
        _, _, _, top10, bot10, _, persons = self._pull()

        self.assertEqual([], persons)
        self.assertEqual([], top10)
        self.assertEqual([], bot10)

    def test_fewer_than_ten_persons_returns_full_set_for_both_slices(self):
        # Five people ordered by revenue DESC in SQL; both slices must keep all five.
        revenues = [5000, 4000, 3000, 2000, 1000]
        for i, rev in enumerate(revenues, start=1):
            _insert_person(self.conn, self.DATE, f"rep-{i}", rev)
        self.conn.commit()

        _, _, _, top10, bot10, _, persons = self._pull()

        self.assertEqual(5, len(persons))
        self.assertEqual(5, len(top10))
        self.assertEqual(5, len(bot10))
        self.assertEqual([f"rep-{i}" for i in range(1, 6)], [p["rep_name"] for p in top10])
        self.assertEqual([f"rep-{i}" for i in range(1, 6)], [p["rep_name"] for p in bot10])
        self.assertEqual(top10, bot10)
        self.assertEqual(persons, top10)

    def test_more_than_ten_persons_splits_highest_and_lowest(self):
        # 15 people: revenue 1500,1400,...,100 so SQL ORDER BY revenue DESC is stable.
        for i in range(15):
            rev = 1500 - i * 100
            _insert_person(self.conn, self.DATE, f"rep-{i:02d}", rev)
        self.conn.commit()

        _, _, _, top10, bot10, _, persons = self._pull()

        self.assertEqual(15, len(persons))
        self.assertEqual(10, len(top10))
        self.assertEqual(10, len(bot10))

        self.assertEqual(
            [f"rep-{i:02d}" for i in range(10)],
            [p["rep_name"] for p in top10],
        )
        self.assertEqual(
            [f"rep-{i:02d}" for i in range(5, 15)],
            [p["rep_name"] for p in bot10],
        )
        self.assertEqual(1500, top10[0]["revenue"])
        self.assertEqual(600, top10[-1]["revenue"])
        self.assertEqual(1000, bot10[0]["revenue"])
        self.assertEqual(100, bot10[-1]["revenue"])

        # Middle five appear in both slices under the current [:10]/[-10:] contract.
        overlap = {p["rep_name"] for p in top10} & {p["rep_name"] for p in bot10}
        self.assertEqual({f"rep-{i:02d}" for i in range(5, 10)}, overlap)


if __name__ == "__main__":
    unittest.main()
