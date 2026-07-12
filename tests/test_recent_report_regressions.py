# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch

import generate_app_full_report as app_report
import generate_hongniang_full_report as hongniang_report
import generate_telesale_full_report as telesale_report


def _app_row(**overrides):
    row = {
        "amt": "100000",
        "pay_num": "100",
        "active_members": "2000",
        "refund_money": "2500",
        "pay_num_new": "30",
        "retain_1d": "120",
        "retain_7d": "80",
        "order_cnt": "400",
        "order_pay": "100",
        "reg_num_m": "1000",
        "pay_num_m": "200",
        "pay_amt_m": "500000",
        "mems": "300",
        "zhenxin_member": "85000",
        "super_member_full": "8000",
        "live_guard": "3000",
        "super_member_plus": "2000",
        "zhenai_coin": "1000",
        "super_remind": "500",
        "star_privilege": "300",
        "super_recommend": "200",
        "other": "0",
        "pay_amt": "100000",
    }
    row.update(overrides)
    return row


class AppReportRegressionTest(unittest.TestCase):
    def test_agg_app_computes_core_kpi_rates(self):
        metrics = app_report.agg_app([_app_row()])

        self.assertEqual(metrics["total_rev"], 100000.0)
        self.assertEqual(metrics["arpu"], 1000.0)
        self.assertEqual(metrics["pay_rate"], 5.0)
        self.assertEqual(metrics["refund_rate"], 2.5)
        self.assertEqual(metrics["retain_rate_1d"], 40.0)
        self.assertEqual(metrics["order_conv"], 25.0)

    def test_main_fetches_today_previous_and_exact_10_day_window(self):
        calls = []

        def fake_daily(team, date=None, page=1, size=500):
            calls.append((team, date))
            return {"rows": []}

        argv = ["generate_app_full_report.py", "--date", "2026-02-27"]
        with patch.object(app_report.sys, "argv", argv), \
                patch.object(app_report, "daily", side_effect=fake_daily), \
                patch.object(app_report, "generate_html", return_value="<html></html>"), \
                patch.object(app_report, "export_html", return_value="/tmp/app.html"), \
                patch.object(app_report, "send_report_email", return_value=True):
            app_report.main()

        expected = [
            ("app", "20260227"),
            ("app", "20260226"),
        ] + [("app", f"202602{day:02d}") for day in range(18, 28)]
        self.assertEqual(calls, expected)


class TelesaleReportRegressionTest(unittest.TestCase):
    def test_generate_html_does_not_leak_fstring_escape_artifact(self):
        today_rows = [{
            "dept_name": "电销一部",
            "worker_nums": "10",
            "pay_1d_amt": "30000",
            "callout_1d_num": "1000",
            "link_1d_num": "200",
            "linkmems_deeptalk_10_1d_num": "80",
            "pay_1d_num": "8",
            "pay_1m_amt": "200000",
            "new_worker_num": "1",
            "ai_score": "80",
        }]
        prev_rows = [dict(today_rows[0], pay_1d_amt="25000")]

        html = telesale_report.generate_html(today_rows, prev_rows, "2026-02-27")

        self.assertNotIn("{{}age{}", html)
        self.assertIn("上周帮助一位客户在3周内见面4次", html)


class HongniangReportRegressionTest(unittest.TestCase):
    def test_refund_channels_and_department_manager_are_aggregated(self):
        rows = [{
            "dept_name": "深圳红娘一部 一组",
            "pay_1d_amt": "50000",
            "pay_1m_amt": "500000",
            "jm_n": "5",
            "jm_all": "10",
            "staff_new": "5",
            "call_worker": "4",
            "on_vip": "30",
            "allot_yes": "20",
            "link_time_count": "100",
            "deep_count": "40",
            "love_cnt_m": "2",
            "tousu_n": "1",
            "pay_1d_num": "3",
            "zhenai_back": "1000",
            "zhenaigd_back": "2000",
            "zhenai_hz_back": "3000",
            "zhenai_xfh_back": "4000",
            "zhenai_md_back": "0",
        }]

        metrics = hongniang_report.agg_hongniang(rows)
        depts = hongniang_report.build_dept_data(rows)

        self.assertEqual(metrics["total_refund"], 10000.0)
        self.assertEqual(metrics["refund_rate"], 20.0)
        self.assertEqual(depts[0]["dept_name"], "深圳红娘一部")
        self.assertEqual(depts[0]["manager"], "曹世迪")
        self.assertEqual(depts[0]["total_refund"], 10000.0)


if __name__ == "__main__":
    unittest.main()
