import unittest

from generate_jianxin_full_report import (
    agg_jianxin,
    build_channel_data,
    build_dept_data,
    build_worker_data,
)


class JianxinAggregatorTests(unittest.TestCase):
    def test_summary_uses_weighted_funnel_rates_and_money_totals(self):
        rows = [
            {
                "assign_1d_num": 60,
                "send_msg_1d_num": 80,
                "reply_1d_num": 20,
                "wechat_add_1d_num": 90,
                "transfer_1d_num": 14,
                "pay_1d_num": 2,
                "pay_1d_amt": "7,000",
                "pay_1m_amt": "10,000",
                "worker_nums": 4,
                "new_worker_num": 1,
            },
            {
                "assign_1d_num": 40,
                "send_msg_1d_num": 20,
                "reply_1d_num": 10,
                "wechat_add_1d_num": 40,
                "transfer_1d_num": 6,
                "pay_1d_num": 2,
                "pay_1d_amt": "5,000",
                "pay_1m_amt": "8,000",
                "worker_nums": 2,
                "new_worker_num": 1,
            },
        ]

        result = agg_jianxin(rows)

        self.assertEqual(12_000, result["pay_amt"])
        self.assertEqual(18_000, result["pay_m"])
        self.assertEqual(30, result["proactive"])
        self.assertEqual(2_000, result["per_capita"])
        self.assertEqual(5, result["per_capita_proactive"])
        self.assertAlmostEqual(30, result["reply_rate"])
        self.assertAlmostEqual(130, result["wechat_rate"])
        self.assertAlmostEqual(20 / 130 * 100, result["transfer_rate"])
        self.assertAlmostEqual(20, result["pay_rate"])

    def test_summary_zero_denominators_and_negative_proactive_are_safe(self):
        result = agg_jianxin(
            [
                {
                    "assign_1d_num": 10,
                    "wechat_add_1d_num": 4,
                    "pay_1d_amt": 100,
                }
            ]
        )

        self.assertEqual(0, result["proactive"])
        self.assertEqual(0, result["per_capita_proactive"])
        self.assertEqual(0, result["reply_rate"])
        self.assertEqual(40, result["wechat_rate"])
        self.assertEqual(0, result["pay_rate"])
        self.assertEqual(0, result["per_capita"])

    def test_department_and_channel_rollups_group_and_rank_rows(self):
        rows = [
            {
                "dept_name": "建信二部",
                "channel_name": "渠道A",
                "worker_nums": 2,
                "assign_1d_num": 10,
                "send_msg_1d_num": 8,
                "reply_1d_num": 2,
                "wechat_add_1d_num": 12,
                "transfer_1d_num": 3,
                "pay_1d_num": 1,
                "pay_1d_amt": 100,
                "pay_1m_amt": 200,
            },
            {
                "dept_name": "建信二部",
                "channel_name": "渠道A",
                "worker_nums": 1,
                "assign_1d_num": 5,
                "send_msg_1d_num": 2,
                "reply_1d_num": 1,
                "wechat_add_1d_num": 6,
                "transfer_1d_num": 2,
                "pay_1d_num": 1,
                "pay_1d_amt": 50,
                "pay_1m_amt": 100,
            },
            {
                "dept_name": "未配置部门",
                "channel_name": "渠道B",
                "worker_nums": 2,
                "assign_1d_num": 20,
                "send_msg_1d_num": 10,
                "reply_1d_num": 5,
                "wechat_add_1d_num": 25,
                "transfer_1d_num": 5,
                "pay_1d_num": 2,
                "pay_1d_amt": 300,
                "pay_1m_amt": 500,
            },
        ]

        departments = build_dept_data(rows)
        channels = build_channel_data(rows)

        self.assertEqual(["未配置部门", "建信二部"], [d["dept_name"] for d in departments])
        configured = departments[1]
        self.assertEqual("刘源", configured["manager"])
        self.assertEqual(3, configured["workers"])
        self.assertEqual(150, configured["pay_amt"])
        self.assertEqual(3, configured["proactive"])
        self.assertAlmostEqual(30, configured["reply_rate"])

        self.assertEqual(["渠道B", "渠道A"], [c["channel_name"] for c in channels])
        self.assertEqual(15, channels[1]["trigger"])
        self.assertEqual(18, channels[1]["add"])
        self.assertEqual(150, channels[1]["pay_amt"])

    def test_worker_rollup_merges_duplicate_rows_and_ranks_by_score(self):
        rows = [
            {
                "worker_id": "worker-a",
                "name": "员工甲",
                "dept_name": "建信二部",
                "transfer_1d_num": 2,
                "pay_1d_amt": 1_000,
                "wechat_add_1d_num": 5,
                "reply_1d_num": 4,
                "send_msg_1d_num": 8,
                "assign_1d_num": 3,
                "pay_1m_amt": 2_000,
            },
            {
                "worker_id": "worker-a",
                "name": "员工甲",
                "dept_name": "建信二部",
                "transfer_1d_num": 1,
                "pay_1d_amt": 500,
                "wechat_add_1d_num": 3,
                "reply_1d_num": 2,
                "send_msg_1d_num": 2,
                "assign_1d_num": 2,
                "pay_1m_amt": 1_000,
            },
            {
                "worker_id": "worker-b",
                "name": "员工乙",
                "dept_name": "建信三部",
                "pay_1d_amt": 10_000,
            },
            {"name": "", "pay_1d_amt": 99_999},
        ]

        workers = build_worker_data(rows)

        self.assertEqual(["员工乙", "员工甲"], [w["name"] for w in workers])
        worker_a = workers[1]
        self.assertEqual(1_500, worker_a["pay_amt"])
        self.assertEqual(3_000, worker_a["pay_m"])
        self.assertEqual(3, worker_a["transfer"])
        self.assertEqual(3, worker_a["proactive"])
        self.assertAlmostEqual(60, worker_a["reply_rate"])
        self.assertAlmostEqual(37.5, worker_a["transfer_rate"])


if __name__ == "__main__":
    unittest.main()
