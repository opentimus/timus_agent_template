#!/usr/bin/env python3
"""业务工具脚本单元测试（两包同一份）：point_util 数值口径 + date_util 日期口径。"""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
sys.path.insert(0, str(TESTS))
import pkg_config as cfg  # noqa: E402

sys.path.insert(0, str(ROOT / "skills" / cfg.SCHEMA_SKILL / "scripts"))
import date_util  # noqa: E402
import point_util  # noqa: E402


class NormalizeTest(unittest.TestCase):
    def test_integer(self) -> None:
        self.assertEqual(point_util.normalize("20")["text"], "20.00")
        self.assertEqual(point_util.normalize("20")["value"], 20.0)

    def test_one_decimal(self) -> None:
        self.assertEqual(point_util.normalize("6.5")["text"], "6.50")

    def test_round_half_up(self) -> None:
        self.assertEqual(point_util.normalize("6.567")["text"], "6.57")

    def test_half_boundary(self) -> None:
        # Decimal ROUND_HALF_UP：20.005 -> 20.01（float 会得到 20.00 的边界歧义）
        self.assertEqual(point_util.normalize("20.005")["text"], "20.01")

    def test_leading_dot(self) -> None:
        self.assertEqual(point_util.normalize(".5")["text"], "0.50")

    def test_zero_rejected(self) -> None:
        with self.assertRaises(point_util.PointError):
            point_util.normalize("0")
        with self.assertRaises(point_util.PointError):
            point_util.normalize("0.00")

    def test_negative_rejected(self) -> None:
        with self.assertRaises(point_util.PointError):
            point_util.normalize("-3")

    def test_scientific_rejected(self) -> None:
        with self.assertRaises(point_util.PointError):
            point_util.normalize("1e3")

    def test_text_rejected(self) -> None:
        with self.assertRaises(point_util.PointError):
            point_util.normalize("abc")
        with self.assertRaises(point_util.PointError):
            point_util.normalize("")


class SplitTest(unittest.TestCase):
    def test_weighted(self) -> None:
        out = point_util.split("3", ["1", "2"])
        self.assertEqual([i["text"] for i in out["items"]], ["1.00", "2.00"])
        self.assertEqual(out["sum"], "3.00")

    def test_three_items(self) -> None:
        out = point_util.split("6", ["3", "2", "1"])
        self.assertEqual([i["text"] for i in out["items"]], ["3.00", "2.00", "1.00"])
        self.assertEqual(out["sum"], "6.00")

    def test_equal_split_tail(self) -> None:
        # 0.30 / 3 均分 → 0.10 每条，Σ = 0.30
        out = point_util.split("0.30", ["1", "1", "1"])
        self.assertEqual([i["text"] for i in out["items"]], ["0.10", "0.10", "0.10"])
        self.assertEqual(out["sum"], "0.30")

    def test_tail_absorbed_by_last(self) -> None:
        # 1.00 按 1:1:1 拆 → 0.33/0.33/0.34，尾差全部落到最后一条
        out = point_util.split("1", ["1", "1", "1"])
        self.assertEqual([i["text"] for i in out["items"]], ["0.33", "0.33", "0.34"])
        self.assertEqual(out["sum"], "1.00")

    def test_below_minimum_rejected(self) -> None:
        # 加权悬殊时小权重项会落到 0.00，必须报错而不是写 0
        with self.assertRaises(point_util.PointError):
            point_util.split("0.10", ["91", "1"])

    def test_bad_weight_rejected(self) -> None:
        for weight in ("0", "-1", "1.5", "a"):
            with self.assertRaises(point_util.PointError):
                point_util.split("3", [weight])

    def test_empty_weight_rejected(self) -> None:
        with self.assertRaises(point_util.PointError):
            point_util.split("3", [])


class FlowNumberTest(unittest.TestCase):
    def test_pair_adjacent(self) -> None:
        out = point_util.next_pair("TIN")
        primary = int(out["primary"].split("-")[1])
        secondary = int(out["secondary"].split("-")[1])
        self.assertEqual(secondary, primary + 1)
        self.assertTrue(out["primary"].startswith("TIN-"))

    def test_pair_prefix_case(self) -> None:
        self.assertTrue(point_util.next_pair("tpay")["primary"].startswith("TPAY-"))

    def test_bad_prefix_rejected(self) -> None:
        for prefix in ("", "T1N", "TIN-", "TI N"):
            with self.assertRaises(point_util.PointError):
                point_util.next_pair(prefix)

    def test_batch_shape_and_unique(self) -> None:
        out = point_util.next_batch("TPAY", 3)
        numbers = out["numbers"]
        self.assertEqual(len(numbers), 3)
        self.assertEqual(len(set(numbers)), 3)
        self.assertTrue(numbers[0].endswith("-01"))
        self.assertTrue(numbers[2].endswith("-03"))
        self.assertTrue(all(n.startswith("TPAY-" + out["stamp"] + "-") for n in numbers))

    def test_batch_count_rejected(self) -> None:
        with self.assertRaises(point_util.PointError):
            point_util.next_batch("TPAY", 0)


class DateUtilTest(unittest.TestCase):
    BASE = date(2026, 11, 20)

    def test_options_count_and_weekday(self) -> None:
        items = date_util._options(self.BASE, 3)
        self.assertEqual([i["date"] for i in items], ["2026-11-20", "2026-11-21", "2026-11-22"])
        self.assertEqual(items[0]["weekday"], "周五")

    def test_nth_day_is_one_based(self) -> None:
        payload = date_util._range_payload(self.BASE, 1, 2)
        self.assertEqual(payload["start_date"], "2026-11-20")
        self.assertEqual(payload["end_date"], "2026-11-21")

    def test_datetime_format(self) -> None:
        payload = date_util._range_payload(self.BASE, 1, 1)
        self.assertEqual(payload["start_datetime"], "2026-11-20 00:00:00")

    def test_zero_day_rejected(self) -> None:
        with self.assertRaises(ValueError):
            date_util._nth_day(self.BASE, 0)

    def test_end_before_start_rejected(self) -> None:
        with self.assertRaises(ValueError):
            date_util._range_payload(self.BASE, 3, 2)

    def test_cross_month(self) -> None:
        payload = date_util._range_payload(date(2026, 11, 30), 1, 3)
        self.assertEqual(payload["end_date"], "2026-12-02")

    def test_leap_year(self) -> None:
        payload = date_util._range_payload(date(2028, 2, 28), 1, 2)
        self.assertEqual(payload["end_date"], "2028-02-29")

    def test_parse_task(self) -> None:
        self.assertEqual(date_util._parse_task("环境部署|1|2"), ("环境部署", 1, 2))
        with self.assertRaises(ValueError):
            date_util._parse_task("环境部署|1")
        with self.assertRaises(ValueError):
            date_util._parse_task("|1|2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
