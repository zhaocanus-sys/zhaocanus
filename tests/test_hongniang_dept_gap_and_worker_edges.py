# -*- coding: utf-8 -*-
"""红娘部门管理视角与员工诊断的贴线合同。

全局见面率 0.8/1.0/1.2 和退费率 5/10 已有覆盖。
这里锁的是另一组比较符：部门卡按「见面率 < 0.8 → 退费率 > 8 → 人均」
派发管理视角，员工 TOP/BOTTOM 用独立门槛，能力对比在 1.5/1.1 与
退费 0.7/1.0 处分色，底数为 0 时回退 99 倍而不是除零。
"""
import unittest

from generate_hongniang_full_report import generate_html


def _dept(**overrides):
    row = {
        "dept_name": "深圳红娘一部",
        "staff_new": "10",
        "call_worker": "10",
        "on_vip": "100",
        "jm_n": "10",
        "pay_1d_amt": "100000",
        "pay_1m_amt": "400000",
        "link_time_count": "100",
        "deep_count": "20",
        "love_cnt_m": "1",
        "tousu_n": "0",
        "pay_1d_num": "2",
        "zhenai_back": "0",
    }
    row.update(overrides)
    return row


def _worker(**overrides):
    row = {
        "worker_name": "林晓",
        "dept_name": "深圳红娘一部",
        "jm_n": "0",
        "on_vip": "0",
        "off_vip": "0",
        "link_time_count": "0",
        "jianmian_cs": "100",
        "jianmian_rs": "0",
        "jianmiangd_cs": "100",
        "jianmiangd_rs": "0",
        "love_cnt_m": "0",
        "tousu_n": "0",
        "online_pay_m": "0",
        "xml_pay_m": "0",
        "offline_pay_m": "0",
        "zhenai_back": "0",
        "zhenaigd_back": "0",
    }
    row.update(overrides)
    return row


def _between(html, start, end):
    return html.split(start, 1)[1].split(end, 1)[0]


def _dept_diag(html):
    return _between(html, "部门级诊断（含管理者姓名 + 管理视角缺失推断）", "数据→人的转向")


def _top_workers(html):
    return _between(html, "员工TOP5深度分析", "TOP5 vs BOTTOM5")


def _bot_workers(html):
    return _between(html, "BOTTOM5员工专项诊断", "部门级诊断")


def _compare(html):
    return _between(html, "TOP5 vs BOTTOM5 能力差异对比", "BOTTOM5员工专项诊断")


def _ratio_row(html, label):
    return _compare(html).split(f">{label}</td>", 1)[1].split("</tr>", 1)[0]


class HongniangDeptGapTests(unittest.TestCase):
    def test_gap_priority_worst3_slice_and_catchup_uplift(self):
        html = generate_html(
            [
                _dept(dept_name="深圳红娘一部", staff_new="10", jm_n="7",
                      pay_1d_amt="10000", zhenai_back="9000"),
                _dept(dept_name="厦门红娘一区一部", staff_new="10", jm_n="8",
                      pay_1d_amt="100000", zhenai_back="8100"),
                _dept(dept_name="厦门红娘一区二部", staff_new="10", jm_n="9",
                      pay_1d_amt="20000", zhenai_back="0"),
                _dept(dept_name="厦门红娘二区二部", staff_new="10", jm_n="20",
                      pay_1d_amt="80000", zhenai_back="0"),
            ],
            [],
            [],
            "2026-02-27",
        )
        diag = _dept_diag(html)

        # 7/10 = 0.70。见面率优先于退费，即使该部门退费很高也不改派视角。
        self.assertIn("深圳红娘一部（曹世迪）— 见面安排率 0.70", diag)
        self.assertIn("缺乏VIP资源系统性盘点机制，日程管理粗放", diag)
        # 全局人均 210000/40 = 5250；该部门人均 1000；差额 × 10 人。
        self.assertIn("达均值可+¥42,500/日", diag)

        # 8/10 = 0.80 不再走低见面率；8100/100000 = 8.1% 才进入退费视角。
        self.assertIn("厦门红娘一区一部（温方方（代））— 见面安排率 0.80", diag)
        self.assertIn("对服务承诺合规性监管不足，期望管理失控", diag)

        # 0.90 且退费为 0：落到人均辅导，而不是退费或见面盘点。
        self.assertIn("厦门红娘一区二部（周美）— 见面安排率 0.90", diag)
        self.assertIn("差异化辅导策略缺失，标杆SOP未下沉到全员", diag)

        # 只取见面率最低的 3 个部门。最高部门不进这张卡。
        self.assertNotIn("刘文琴", diag)
        self.assertNotIn("见面安排率 2.00", diag)
        self.assertEqual(diag.count("部门预警"), 3)

    def test_jm_just_under_0_8_keeps_inventory_gap_and_refund_8_falls_through(self):
        under = generate_html(
            [_dept(dept_name="深圳红娘一部", staff_new="100", jm_n="79",
                   pay_1d_amt="100000", zhenai_back="50000")],
            [], [], "2026-02-27",
        )
        under_diag = _dept_diag(under)
        # 79/100 = 0.79，仍低于 0.8，退费 50% 不能抢走视角。
        self.assertIn("见面安排率 0.79", under_diag)
        self.assertIn("缺乏VIP资源系统性盘点机制，日程管理粗放", under_diag)
        self.assertNotIn("对服务承诺合规性监管不足", under_diag)
        self.assertNotIn("差异化辅导策略缺失", under_diag)

        at_refund = generate_html(
            [_dept(staff_new="10", jm_n="8", pay_1d_amt="100000", zhenai_back="8000")],
            [], [], "2026-02-27",
        )
        refund_diag = _dept_diag(at_refund)
        # 0.80 且 8000/100000 = 8.0%。比较符是 > 8，贴线落到人均辅导。
        self.assertIn("深圳红娘一部（曹世迪）— 见面安排率 0.80", refund_diag)
        self.assertIn("差异化辅导策略缺失，标杆SOP未下沉到全员", refund_diag)
        self.assertNotIn("对服务承诺合规性监管不足", refund_diag)
        self.assertNotIn("缺乏VIP资源系统性盘点机制", refund_diag)

    def test_unknown_manager_and_spaced_dept_name_stays_one_team(self):
        unknown = generate_html(
            [_dept(dept_name="杭州红娘九部", staff_new="10", jm_n="5")],
            [], [], "2026-02-27",
        )
        unknown_diag = _dept_diag(unknown)
        self.assertIn("杭州红娘九部（（待确认））— 见面安排率 0.50", unknown_diag)
        self.assertIn("缺乏VIP资源系统性盘点机制，日程管理粗放", unknown_diag)

        merged = generate_html(
            [
                _dept(dept_name="深圳红娘一部 早班", staff_new="10", jm_n="4",
                      pay_1d_amt="50000"),
                _dept(dept_name="深圳红娘一部 晚班", staff_new="10", jm_n="12",
                      pay_1d_amt="50000"),
            ],
            [], [], "2026-02-27",
        )
        merged_diag = _dept_diag(merged)
        # 空格后的班次并入同一部门：16/20 = 0.80，不能拆成 0.40 的低见面率。
        self.assertIn("深圳红娘一部（曹世迪）— 见面安排率 0.80", merged_diag)
        self.assertNotIn("见面安排率 0.40", merged_diag)
        self.assertNotIn("早班", merged_diag)
        self.assertNotIn("晚班", merged_diag)
        self.assertIn("差异化辅导策略缺失，标杆SOP未下沉到全员", merged_diag)
        self.assertNotIn("缺乏VIP资源系统性盘点机制", merged_diag)
        self.assertEqual(merged_diag.count("部门预警"), 1)


class HongniangWorkerReasonTests(unittest.TestCase):
    def test_why_good_includes_each_reason_only_at_its_line(self):
        star = generate_html(
            [_dept()],
            [],
            [_worker(
                jm_n="3",
                jianmian_rs="85",
                jianmiangd_rs="70",
                love_cnt_m="1",
            )],
            "2026-02-27",
        )
        top = _top_workers(star)
        self.assertIn(
            "见面安排频次高；见面确认率强；复见面推进积极；恋爱达成有突破",
            top,
        )
        self.assertNotIn("资源盘点系统化", top)
        # 这些正向门槛都不触发 BOTTOM 问题清单。
        bot = _bot_workers(star)
        self.assertIn("综合评分偏低，需排查具体薄弱环节", bot)
        self.assertNotIn("今日零见面安排", bot)
        self.assertNotIn("邀约话术需优化", bot)
        self.assertNotIn("需排查服务承诺合规性", bot)

        short = generate_html(
            [_dept()],
            [],
            [
                _worker(worker_name="", jm_n="99"),
                _worker(
                    worker_name="林晓",
                    jm_n="2",
                    jianmian_rs="84",
                    jianmiangd_rs="69",
                    love_cnt_m="0",
                ),
            ],
            "2026-02-27",
        )
        short_top = _top_workers(short)
        # 2 < 3、84 < 85、69 < 70、恋爱 0：只剩兜底原因。空姓名行不进榜。
        self.assertIn("资源盘点系统化", short_top)
        self.assertIn("林晓", short_top)
        self.assertNotIn("见面安排频次高", short_top)
        self.assertNotIn("见面确认率强", short_top)
        self.assertNotIn("复见面推进积极", short_top)
        self.assertNotIn("恋爱达成有突破", short_top)
        self.assertNotIn("99", short_top)

    def test_bottom_issues_fire_only_past_each_line(self):
        over = generate_html(
            [_dept()],
            [],
            [_worker(jm_n="0", jianmian_rs="49", zhenai_back="5001")],
            "2026-02-27",
        )
        bot = _bot_workers(over)
        self.assertIn(
            "今日零见面安排，VIP资源完全未服务；"
            "见面确认率仅49%，邀约话术需优化；"
            "退费金额¥5,001，需排查服务承诺合规性",
            bot,
        )
        self.assertNotIn("综合评分偏低", bot)

        line = generate_html(
            [_dept()],
            [],
            [_worker(jm_n="1", jianmian_rs="50", zhenai_back="5000")],
            "2026-02-27",
        )
        line_bot = _bot_workers(line)
        # jm < 1、确认率 < 50、退费 > 5000。贴线三条都不写进问题。
        self.assertIn("综合评分偏低，需排查具体薄弱环节", line_bot)
        self.assertNotIn("今日零见面安排", line_bot)
        self.assertNotIn("邀约话术需优化", line_bot)
        self.assertNotIn("需排查服务承诺合规性", line_bot)
        self.assertNotIn("¥5,000", line_bot)


class HongniangCompareRatioTests(unittest.TestCase):
    def _cohort(self, top_jm, bot_jm, top_refund, bot_refund):
        workers = []
        for i in range(5):
            workers.append(_worker(
                worker_name=f"优{i}",
                jm_n=str(top_jm),
                love_cnt_m="5",
                zhenai_back=str(top_refund),
            ))
        for i in range(5):
            workers.append(_worker(
                worker_name=f"弱{i}",
                jm_n=str(bot_jm),
                love_cnt_m="0",
                zhenai_back=str(bot_refund),
            ))
        return generate_html([_dept()], [], workers, "2026-02-27")

    def test_higher_better_copy_agrees_away_from_the_shared_cutoff(self):
        # 颜色用 >=，文案用 >。1.6 / 1.2 / 1.0 三档两边一致。
        wide = _ratio_row(self._cohort(16, 10, 100, 100), "见面安排数")
        self.assertIn('color:#16a34a">1.6x', wide)
        self.assertIn("差距显著，可通过SOP复制TOP工作模式", wide)

        mid = _ratio_row(self._cohort(12, 10, 100, 100), "见面安排数")
        self.assertIn('color:#d97706">1.2x', mid)
        self.assertIn("差距可控，需强化日常执行", mid)
        self.assertNotIn("差距显著", mid)

        flat = _ratio_row(self._cohort(10, 10, 100, 100), "见面安排数")
        self.assertIn('color:#dc2626">1.0x', flat)
        self.assertIn("差距较小", flat)
        self.assertNotIn("差距可控", flat)
        self.assertNotIn("差距显著", flat)

    def test_refund_ratio_uses_lower_better_colors_and_zero_base_is_99(self):
        better = _ratio_row(self._cohort(3, 1, 700, 1000), "退费总额")
        # 700/1000 = 0.7，含等号为绿色。均值单元格另有固定色，只锁倍数单元格。
        self.assertIn('color:#16a34a">0.7x', better)
        self.assertNotIn('color:#d97706">0.7x', better)
        self.assertNotIn('color:#dc2626">0.7x', better)

        even = _ratio_row(self._cohort(3, 1, 1000, 1000), "退费总额")
        # 1.0 仍算「不差于 BOTTOM」，琥珀色，不是红色。
        self.assertIn('color:#d97706">1.0x', even)
        self.assertNotIn('color:#16a34a">1.0x', even)
        self.assertNotIn('color:#dc2626">1.0x', even)

        worse = _ratio_row(self._cohort(3, 1, 1140, 1000), "退费总额")
        # 1.14 > 1.0，TOP 退费更高，红色。
        self.assertIn('color:#dc2626">1.1x', worse)
        self.assertNotIn('color:#16a34a">1.1x', worse)
        self.assertNotIn('color:#d97706">1.1x', worse)

        zero_base = _ratio_row(self._cohort(3, 1, 100, 0), "退费总额")
        self.assertIn(">100.0元</td>", zero_base)
        self.assertIn(">0.0元</td>", zero_base)
        self.assertIn('color:#dc2626">99.0x', zero_base)
