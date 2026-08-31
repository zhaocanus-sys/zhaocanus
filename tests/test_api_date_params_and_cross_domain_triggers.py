"""Regression coverage for API date-param construction and leftover CrossDomain triggers.

PR #114 locked health() path suffixes and _req exception envelopes.
daily / query / ad_daily / ad_report still had no date-param contract:
omitting `date` must drop the key (not send date=None); page/page_size
and query table_role must always be present. A swapped path or leaked
None date would pull the wrong day into every 10-day report window.

CrossDomain leftover triggers (not locked as primary in PR #81/#111/#114):
- 辛普森悖论×二八法则 when len(depts)>3; silent at 3
- 271法则×自然代谢 when t20>50 and len>3; silent at t20==50 or 3 depts
- 飞轮效应×困境六悖论 when any per_capita_revenue<1200; silent at ==1200
- 客户成功×品牌修复 when ref_rate>4; silent at ==4
- a raising trigger is swallowed so one bad rule cannot abort execute()

Always-on cards (狼性PK / Hook / 杠铃 / 用户分层 / 战时CEO / AARRR)
are asserted only as background, not as the primary lock.

Does not import generate_telesale_full_report.
Does not lock parallel_fetch([]) (PR #53), persistence global count
(PR #48), APP sparkline mapping, or shop double-count.
Does not lock CrossDomain missing-key format() crash (PR #111).

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest
from unittest.mock import MagicMock, patch

from agent_system.actions.api_client import (
    ad_daily,
    ad_report,
    daily,
    me,
    query,
    tables,
    trend,
)
from agent_system.engines.collision_engine import CrossDomainCollisionEngine


def _full_summary(**overrides):
    """Complete format keys so leftover rules do not KeyError on .format."""
    summary = {
        "dr": 10.0,
        "conv": 2.0,
        "avg_deal": 6000,
        "t20": 40,
        "fc_rate": 5.0,
        "ai": 80,
        "ref_rate": 2.0,
    }
    summary.update(overrides)
    return summary


def _depts(*pcs):
    return [{"dept_name": f"电销{i}部", "per_capita_revenue": pc} for i, pc in enumerate(pcs, 1)]


def _tags(engine):
    return {f.tag for f in engine.findings}


class ApiDateParamTests(unittest.TestCase):
    def _ok_request(self):
        resp = MagicMock()
        resp.json.return_value = {"rows": [], "row_count": 0}
        resp.raise_for_status = MagicMock()
        return resp

    def test_daily_omits_date_unless_provided(self):
        with patch(
            "agent_system.actions.api_client.requests.request",
            return_value=self._ok_request(),
        ) as req:
            daily("telesale")
            daily("jianxin", date="20260831", page=2, size=50)
        bare_params = req.call_args_list[0].kwargs["params"]
        dated_params = req.call_args_list[1].kwargs["params"]
        self.assertEqual({"page": 1, "page_size": 500}, bare_params)
        self.assertNotIn("date", bare_params)
        self.assertEqual(
            {"page": 2, "page_size": 50, "date": "20260831"},
            dated_params,
        )
        self.assertTrue(req.call_args_list[0].args[1].endswith("/api/v1/team/telesale/daily"))
        self.assertTrue(req.call_args_list[1].args[1].endswith("/api/v1/team/jianxin/daily"))

    def test_query_always_sends_table_role(self):
        with patch(
            "agent_system.actions.api_client.requests.request",
            return_value=self._ok_request(),
        ) as req:
            query("shop", "hourly")
            query("app", "daily", date="20260830", page=3, size=20)
        bare = req.call_args_list[0].kwargs["params"]
        dated = req.call_args_list[1].kwargs["params"]
        self.assertEqual(
            {"page": 1, "page_size": 500, "table_role": "hourly"},
            bare,
        )
        self.assertNotIn("date", bare)
        self.assertEqual(
            {"page": 3, "page_size": 20, "table_role": "daily", "date": "20260830"},
            dated,
        )
        self.assertTrue(req.call_args_list[0].args[1].endswith("/api/v1/team/shop/query"))

    def test_ad_and_aux_paths_keep_optional_date(self):
        with patch(
            "agent_system.actions.api_client.requests.request",
            return_value=self._ok_request(),
        ) as req:
            ad_daily()
            ad_daily(date="20260831")
            ad_report("rid-9")
            ad_report("rid-9", date="20260831", page=4, size=10)
            trend("hongniang", days=10)
            tables("app")
            me()
        params = [c.kwargs.get("params") for c in req.call_args_list]
        paths = [c.args[1] for c in req.call_args_list]
        self.assertEqual({}, params[0])
        self.assertEqual({"date": "20260831"}, params[1])
        self.assertEqual({"page": 1, "page_size": 500}, params[2])
        self.assertNotIn("date", params[2])
        self.assertEqual(
            {"page": 4, "page_size": 10, "date": "20260831"},
            params[3],
        )
        self.assertEqual({"days": 10}, params[4])
        self.assertTrue(paths[0].endswith("/api/v1/advertising/daily"))
        self.assertTrue(paths[2].endswith("/api/v1/advertising/report/rid-9"))
        self.assertTrue(paths[4].endswith("/api/v1/team/hongniang/trend"))
        self.assertTrue(paths[5].endswith("/api/v1/team/app/tables"))
        self.assertTrue(paths[6].endswith("/auth/me"))

    def test_header_uses_configured_api_key(self):
        with patch(
            "agent_system.actions.api_client.api_config",
            return_value={"api_key": "test-key-only"},
        ), patch(
            "agent_system.actions.api_client.requests.request",
            return_value=self._ok_request(),
        ) as req:
            daily("app")
        self.assertEqual(
            {"X-API-Key": "test-key-only"},
            req.call_args.kwargs["headers"],
        )
        self.assertEqual(30, req.call_args.kwargs["timeout"])
        self.assertEqual("GET", req.call_args.args[0])


class CrossDomainRemainingTriggerTests(unittest.TestCase):
    def test_simpson_fires_only_above_three_depts(self):
        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(), _depts(3000, 3000, 3000, 3000), [], [])
        self.assertIn("辛普森悖论×二八法则", _tags(engine))

        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(), _depts(3000, 3000, 3000), [], [])
        self.assertNotIn("辛普森悖论×二八法则", _tags(engine))

    def test_rule_271_needs_both_concentration_and_dept_count(self):
        four = _depts(3000, 3000, 3000, 3000)
        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(t20=50.1), four, [], [])
        rule_271 = [f for f in engine.findings if f.tag == "271法则×自然代谢替代裁员"]
        self.assertEqual(1, len(rule_271))
        self.assertIn("TOP20%占50.1%业绩", rule_271[0].description)

        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(t20=50), four, [], [])
        self.assertNotIn("271法则×自然代谢替代裁员", _tags(engine))

        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(t20=60), _depts(3000, 3000, 3000), [], [])
        self.assertNotIn("271法则×自然代谢替代裁员", _tags(engine))

    def test_flywheel_fires_below_1200_and_is_silent_at_threshold(self):
        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(), _depts(1199, 4000), [], [])
        fly = [f for f in engine.findings if f.tag == "飞轮效应×困境六悖论"]
        self.assertEqual(1, len(fly))
        self.assertEqual("P1", fly[0].priority)
        self.assertIn("人均产值<1200", fly[0].description)

        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(), _depts(1200, 4000), [], [])
        self.assertNotIn("飞轮效应×困境六悖论", _tags(engine))

    def test_brand_repair_fires_above_four_percent_refund(self):
        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(ref_rate=4.1), _depts(3000), [], [])
        brand = [f for f in engine.findings if f.tag == "客户成功×品牌修复信任链"]
        self.assertEqual(1, len(brand))
        self.assertEqual("P1", brand[0].priority)
        self.assertIn("退费率4.1%偏高", brand[0].description)
        self.assertIn("行业安全指南", " ".join(brand[0].recommendations))

        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(ref_rate=4), _depts(3000), [], [])
        self.assertNotIn("客户成功×品牌修复信任链", _tags(engine))

    def test_raising_trigger_is_swallowed_and_other_rules_still_run(self):
        engine = CrossDomainCollisionEngine()
        broken = {"dept_name": "电销一部"}  # missing per_capita_revenue
        engine.execute(_full_summary(), [broken, broken], [], [])
        tags = _tags(engine)
        self.assertNotIn("话术标准化×优势管理", tags)
        self.assertNotIn("飞轮效应×困境六悖论", tags)
        self.assertIn("战时CEO×20英里行军", tags)
        self.assertIn("杠铃策略×现金流红线", tags)


if __name__ == "__main__":
    unittest.main()
