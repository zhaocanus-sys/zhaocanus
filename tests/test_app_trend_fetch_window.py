# -*- coding: utf-8 -*-
"""The 10-day APP trend pull lives in main(), not in build_trend_data.

These tests lock the fetch contract introduced when the report stopped
trusting a single trend endpoint: ten inclusive calendar days ending on
the report date, each row stamped with the queried date so a stale
ftime cannot land on the wrong bar.
"""
import datetime
import sys
import unittest
from unittest.mock import patch

import generate_app_full_report as app


def _expected_dates(date_yyyymmdd):
    base = datetime.datetime.strptime(date_yyyymmdd, "%Y%m%d")
    return [
        (base - datetime.timedelta(days=delta)).strftime("%Y%m%d")
        for delta in range(9, -1, -1)
    ]


class AppTrendFetchWindowTests(unittest.TestCase):
    def setUp(self):
        self._date = app.DATE
        self._display = app.DATE_DISPLAY
        self._argv = sys.argv[:]

    def tearDown(self):
        app.DATE = self._date
        app.DATE_DISPLAY = self._display
        sys.argv = self._argv

    def _run(self, argv, payloads, email_ok=True):
        calls = []

        def fake_daily(team, date=None, page=1, size=500):
            calls.append((team, date))
            rows = payloads(date) if callable(payloads) else payloads.get(date, [])
            return {"rows": [dict(r) for r in rows]}

        exported = {}
        mailed = {}

        def fake_export(html, filename, open_browser=True):
            exported["html"] = html
            exported["filename"] = filename
            exported["open_browser"] = open_browser
            return "/tmp/" + filename

        def fake_mail(subject, html):
            mailed["subject"] = subject
            mailed["html"] = html
            return email_ok

        sys.argv = argv
        with patch.object(app, "daily", fake_daily), \
                patch.object(app, "export_html", fake_export), \
                patch.object(app, "send_report_email", fake_mail):
            app.main()
        return calls, exported, mailed

    def test_leap_year_window_stamps_ftime_and_sums_same_day(self):
        """2024-03-01 must include Feb 29 and ignore payload ftime."""
        def payloads(date):
            if date == "20240301":
                return [
                    {"amt": 10000, "pay_num": 2, "active_members": 10,
                     "refund_money": 0, "retain_1d": 0, "ftime": "19990101"},
                    {"amt": 5000, "pay_num": 1, "active_members": 5,
                     "refund_money": 0, "retain_1d": 0, "ftime": "20200101"},
                ]
            day = int(date[-2:])
            return [{
                "amt": day * 100,
                "pay_num": 1,
                "active_members": 10,
                "refund_money": 0,
                "retain_1d": 0,
                "ftime": "19990101",
            }]

        calls, exported, mailed = self._run(
            ["generate_app_full_report.py", "--date", "2024-03-01"], payloads)

        expected = _expected_dates("20240301")
        self.assertEqual(expected[0], "20240221")
        self.assertIn("20240229", expected)
        self.assertEqual(expected[-1], "20240301")
        self.assertEqual({d for team, d in calls}, set(expected))
        self.assertTrue(all(team == "app" for team, _ in calls))

        html = exported["html"]
        self.assertEqual(exported["filename"], "APP_Full_2024-03-01.html")
        self.assertTrue(exported["open_browser"])
        self.assertEqual(mailed["subject"], "📱 APP全量体检报告 2024-03-01")
        self.assertIs(mailed["html"], html)
        self.assertIn(">02-21<", html)
        self.assertIn(">02-29<", html)
        self.assertIn(">03-01<", html)
        self.assertNotIn(">02-20<", html)
        self.assertNotIn("1999-01-01", html)
        self.assertNotIn(">01-01<", html)
        # 10000+5000 stamped onto Mar 1, not split across the fake ftimes.
        self.assertIn("¥1.5万", html)
        self.assertIn("20.0%付", html)

    def test_non_leap_and_year_boundary_windows(self):
        calls, exported, _ = self._run(
            ["prog", "--date", "20230301"], lambda date: [{
                "amt": 1000, "pay_num": 1, "active_members": 10,
                "ftime": "19990101",
            }])
        expected = _expected_dates("20230301")
        self.assertEqual(expected[0], "20230220")
        self.assertNotIn("20230229", expected)
        self.assertEqual({d for _, d in calls}, set(expected))
        self.assertIn(">02-20<", exported["html"])
        self.assertNotIn(">02-19<", exported["html"])
        self.assertNotIn(">02-29<", exported["html"])

        calls, exported, mailed = self._run(
            ["prog", "--date", "2026-01-01"], lambda date: [{
                "amt": 2000, "pay_num": 1, "active_members": 4,
                "ftime": "bogus",
            }])
        expected = _expected_dates("20260101")
        self.assertEqual(expected[0], "20251223")
        self.assertEqual(expected[-1], "20260101")
        self.assertEqual(len(expected), 10)
        self.assertEqual({d for _, d in calls}, set(expected))
        html = exported["html"]
        self.assertIn(">12-23<", html)
        self.assertIn(">01-01<", html)
        self.assertNotIn(">12-22<", html)
        self.assertEqual(exported["filename"], "APP_Full_2026-01-01.html")
        self.assertEqual(mailed["subject"], "📱 APP全量体检报告 2026-01-01")

    def test_missing_date_value_keeps_default_and_empty_payload_exports(self):
        calls, exported, mailed = self._run(
            ["prog", "--date"], lambda date: [])
        self.assertEqual(app.DATE, "20260227")
        expected = _expected_dates("20260227")
        self.assertEqual(expected[0], "20260218")
        self.assertEqual(expected[-1], "20260227")
        self.assertEqual({d for _, d in calls}, set(expected))
        self.assertIn("暂无数据", exported["html"])
        self.assertEqual(exported["filename"], "APP_Full_2026-02-27.html")
        self.assertEqual(mailed["subject"], "📱 APP全量体检报告 2026-02-27")
        self.assertIn("暂无数据", mailed["html"])

    def test_api_error_object_and_mail_failure_do_not_raise(self):
        calls = []

        def fake_daily(team, date=None, page=1, size=500):
            calls.append(date)
            if date == "20260227":
                return {"error": "timeout", "rows": [], "row_count": 0}
            return None

        sys.argv = ["prog"]
        with patch.object(app, "daily", fake_daily), \
                patch.object(app, "export_html", return_value="/tmp/x.html") as exp, \
                patch.object(app, "send_report_email", return_value=False) as mail:
            app.main()
        self.assertEqual(set(calls), set(_expected_dates("20260227")))
        html = exp.call_args[0][0]
        self.assertIn("暂无数据", html)
        self.assertEqual(exp.call_args.kwargs["open_browser"], True)
        self.assertEqual(mail.call_count, 1)
        self.assertEqual(mail.call_args[0][0], "📱 APP全量体检报告 2026-02-27")
        self.assertIn("暂无数据", mail.call_args[0][1])


class AppTrendAndFunnelEdgeTests(unittest.TestCase):
    def test_zero_revenue_trend_bar_does_not_divide_by_zero(self):
        html = app.generate_html(
            [{
                "amt": 1000, "pay_num": 10, "active_members": 100,
                "refund_money": 0, "mems": 10, "retain_1d": 5,
                "zhenxin_member": 100,
            }],
            [],
            [
                {"ftime": "20260226", "amt": 0, "pay_num": 0,
                 "active_members": 0, "refund_money": 0, "retain_1d": 0},
                {"ftime": "20260227", "amt": 0, "pay_num": 0,
                 "active_members": 0, "refund_money": 0, "retain_1d": 0},
            ],
            "2026-02-27",
        )
        self.assertIn(">02-26<", html)
        self.assertIn(">02-27<", html)
        self.assertEqual(html.count("width:0%;background:#3b82f6;height:14px"), 1)
        self.assertEqual(html.count("width:0%;background:#0f172a;height:14px"), 1)
        self.assertEqual(html.count("0.0%付"), 2)

    def test_funnel_pay_rate_turns_red_only_below_3(self):
        def border(pay_num, active):
            html = app.generate_html(
                [{
                    "amt": 1000, "pay_num": pay_num, "active_members": active,
                    "refund_money": 0, "mems": 10, "retain_1d": 5,
                    "zhenxin_member": 100,
                }],
                [], [], "2026-02-27",
            )
            rate = pay_num / active * 100
            # The flow line repeats this text; only the funnel chip prefixes it this way.
            label = f'font-weight:600">付费率{rate:.1f}%({pay_num:,}人)'
            i = html.index(label)
            j = html.rfind("border:3px solid ", 0, i)
            return html[j:j + len("border:3px solid #dc2626")]

        self.assertEqual(border(29, 1000), "border:3px solid #dc2626")
        self.assertEqual(border(30, 1000), "border:3px solid #d97706")
