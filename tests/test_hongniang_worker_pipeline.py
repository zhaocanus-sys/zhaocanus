import sys
import unittest
from unittest.mock import call, patch

import generate_hongniang_full_report as report


class HongniangWorkerAggregationTests(unittest.TestCase):
    def test_hourly_rows_are_aggregated_before_ranking(self):
        rows = [
            {
                "worker_name": "甲员工",
                "dept_name": "深圳红娘一部",
                "jm_n": "3",
                "jm_all": "4",
                "on_vip": "20",
                "off_vip": "10",
                "link_time_count": "8",
                "jianmian_cs": "4",
                "jianmian_rs": "2",
                "jianmiangd_cs": "2",
                "jianmiangd_rs": "1",
                "love_cnt_m": "1",
                "tousu_n": "0",
                "online_pay_m": "1,000.50",
                "xml_pay_m": "200",
                "offline_pay_m": "300",
                "zhenai_back": "10",
                "zhenaigd_back": "5",
            },
            {
                "worker_name": "乙员工",
                "dept_name": "厦门红娘一区一部",
                "jm_n": "1",
                "on_vip": "10",
                "jianmian_cs": "2",
                "jianmian_rs": "1",
                "online_pay_m": "800",
            },
            {
                "worker_name": "甲员工",
                "dept_name": "深圳红娘一部",
                "jm_n": "2",
                "jm_all": "3",
                "on_vip": "10",
                "off_vip": "10",
                "link_time_count": "7",
                "jianmian_cs": "1",
                "jianmian_rs": "1",
                "jianmiangd_cs": "2",
                "jianmiangd_rs": "1",
                "love_cnt_m": "2",
                "tousu_n": "1",
                "online_pay_m": "500",
                "offline_pay_m": "100",
                "zhenai_back": "2",
                "zhenaigd_back": "3",
            },
            {"worker_name": "", "jm_n": "999", "online_pay_m": "999999"},
        ]

        workers = report.build_worker_data(rows)

        self.assertEqual([w["worker_name"] for w in workers], ["甲员工", "乙员工"])
        top = workers[0]
        self.assertEqual(top["dept_name"], "深圳红娘一部")
        self.assertEqual(top["jm_n"], 5)
        self.assertEqual(top["jm_all"], 7)
        self.assertEqual(top["link_time_count"], 15)
        self.assertAlmostEqual(top["total_rev"], 2100.5)
        self.assertEqual(top["total_refund"], 20)
        self.assertAlmostEqual(top["jm_rate"], 1.0)
        self.assertAlmostEqual(top["confirm_rate"], 60.0)
        self.assertAlmostEqual(top["reappt_rate"], 50.0)
        self.assertAlmostEqual(top["score"], 110.0)

    def test_zero_activity_worker_keeps_finite_zero_rates(self):
        workers = report.build_worker_data([
            {"worker_name": "零活动员工", "dept_name": "深圳红娘一部"}
        ])

        self.assertEqual(len(workers), 1)
        worker = workers[0]
        self.assertEqual(worker["total_rev"], 0)
        self.assertEqual(worker["jm_rate"], 0)
        self.assertEqual(worker["confirm_rate"], 0)
        self.assertEqual(worker["reappt_rate"], 0)
        self.assertEqual(worker["score"], 0)


class HongniangReportMainTests(unittest.TestCase):
    @patch.object(report, "send_report_email", return_value=True)
    @patch.object(report, "export_html", return_value="/tmp/Hongniang_Full_2026-03-01.html")
    @patch.object(report, "generate_html", return_value="<html>report</html>")
    @patch.object(report, "query")
    def test_main_routes_daily_and_hourly_data_across_month_boundary(
        self, query_mock, generate_html_mock, export_html_mock, email_mock
    ):
        today_rows = [{"dept_name": "深圳红娘一部"}]
        previous_rows = [{"dept_name": "厦门红娘一区一部"}]
        hourly_rows = [{"worker_name": "甲员工"}]
        query_mock.side_effect = [
            {"rows": today_rows},
            {"rows": previous_rows},
            {"rows": hourly_rows},
        ]

        with (
            patch.object(sys, "argv", ["generate_hongniang_full_report.py", "--date", "2026-03-01"]),
            patch.object(report, "DATE", "20260227"),
            patch.object(report, "DATE_DISPLAY", "2026-02-27"),
        ):
            report.main()

        self.assertEqual(
            query_mock.call_args_list,
            [
                call("hongniang", "daily", "20260301"),
                call("hongniang", "daily", "20260228"),
                call("hongniang", "hourly", "20260301"),
            ],
        )
        generate_html_mock.assert_called_once_with(
            today_rows, previous_rows, hourly_rows, "2026-03-01"
        )
        export_html_mock.assert_called_once_with(
            "<html>report</html>",
            "Hongniang_Full_2026-03-01.html",
            open_browser=True,
        )
        email_mock.assert_called_once_with(
            "💑 电话红娘全量体检报告 2026-03-01",
            "<html>report</html>",
        )


if __name__ == "__main__":
    unittest.main()
