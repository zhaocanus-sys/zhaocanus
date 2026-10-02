# -*- coding: utf-8 -*-
"""红娘员工见面安排率的 VIP 分母下限。

jm_rate = 见面场次 / max((在线VIP+下线VIP) / 10, 1)。
不足 10 个 VIP 时分母按 1 计，空资源池同样不按 0.1 放大。
已有小时聚合用例用的是 50 个 VIP，下限不生效，改掉 floor 或漏计下线 VIP 仍会得到 1.0。
"""
import unittest

import generate_hongniang_full_report as report


def _worker(name, jm_n, on_vip=0, off_vip=0):
    return {
        "worker_name": name,
        "dept_name": "深圳红娘一部",
        "jm_n": jm_n,
        "on_vip": on_vip,
        "off_vip": off_vip,
    }


class HongniangWorkerVipRateFloorTests(unittest.TestCase):
    def test_jm_rate_floor_holds_until_vip_pool_exceeds_ten(self):
        workers = {
            w["worker_name"]: w
            for w in report.build_worker_data([
                _worker("九人池", 4, on_vip=9),
                _worker("十人池", 4, on_vip=10),
                _worker("十一人池", 4, on_vip=6, off_vip=5),
                _worker("空池", 4, on_vip=0, off_vip=0),
            ])
        }

        self.assertAlmostEqual(workers["九人池"]["jm_rate"], 4.0)
        self.assertAlmostEqual(workers["十人池"]["jm_rate"], 4.0)
        self.assertAlmostEqual(workers["十一人池"]["jm_rate"], 4 / 1.1)
        self.assertAlmostEqual(workers["空池"]["jm_rate"], 4.0)
        # 6 个在线 VIP 单独仍在下限内；加上 5 个下线才越过 10。
        self.assertNotAlmostEqual(workers["十一人池"]["jm_rate"], 4.0)


if __name__ == "__main__":
    unittest.main()
