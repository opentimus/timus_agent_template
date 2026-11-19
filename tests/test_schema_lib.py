#!/usr/bin/env python3
"""schema_lib 类型层单元测试（两包同一份，零第三方依赖）。

只测「类型层」职责：语义包解析、表 / 字段清单、可写性拒绝、取值类型校验。
业务数值口径（正数、两位小数、拆分）在 test_util.py，不在此处重复。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
sys.path.insert(0, str(TESTS))
import pkg_config as cfg  # noqa: E402

sys.path.insert(0, str(ROOT / "skills" / cfg.SCHEMA_SKILL / "scripts"))
import schema_lib  # noqa: E402

SCHEMA_PATH = str(ROOT / "skills" / cfg.SCHEMA_SKILL / "references" / cfg.SCHEMA_FILE)


class SchemaLibTest(unittest.TestCase):
    schema: dict = {}

    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = schema_lib.load_schema(SCHEMA_PATH)

    def _first(self, field_type: str, writable: bool = True) -> tuple[str, str]:
        """返回第一个匹配类型的 (表名, 字段名)；找不到则 skip。"""
        policy = self.schema["type_policy"]
        for table, fields in self.schema["fields"].items():
            for name, ftype in fields.items():
                if ftype == field_type and (policy.get(ftype) == "writable") == writable:
                    return table, name
        self.skipTest("语义包中没有 {} 字段".format(field_type))

    # ---------- 语义包结构 ----------
    def test_tables_and_fields_consistent(self) -> None:
        self.assertEqual(set(self.schema["tables"]), set(self.schema["fields"]))

    def test_required_tables_present(self) -> None:
        self.assertEqual(set(self.schema["tables"]), set(cfg.REQUIRED_TABLES))

    def test_team_code(self) -> None:
        self.assertEqual(self.schema["meta"]["team_code"], cfg.APP_CODE)

    def test_every_table_has_field(self) -> None:
        for table in cfg.REQUIRED_TABLES:
            self.assertTrue(schema_lib.list_fields(self.schema, table), table)

    def test_list_tables_matches(self) -> None:
        names = {t["name"] for t in schema_lib.list_tables(self.schema)}
        self.assertEqual(names, set(cfg.REQUIRED_TABLES))

    def test_writable_flag_follows_policy(self) -> None:
        policy = self.schema["type_policy"]
        for table in cfg.REQUIRED_TABLES:
            for item in schema_lib.list_fields(self.schema, table):
                self.assertEqual(item["writable"], policy.get(item["type"]) == "writable", item["name"])

    # ---------- 可写性 ----------
    def test_text_field_writable(self) -> None:
        table, name = self._first("Text")
        args = schema_lib.build_arguments(self.schema, table, [(name, "示例值")])
        self.assertEqual(args["app_name"], cfg.APP_CODE)
        self.assertEqual(args["table_name"], table)
        self.assertEqual(args["fields"], [{"name": name, "value": "示例值"}])

    def test_readonly_rejected(self) -> None:
        for ftype in ("AutoNumber", "Lookup", "User", "CreatedTime", "Formula"):
            try:
                table, name = self._first(ftype, writable=False)
            except unittest.SkipTest:
                continue
            with self.assertRaises(schema_lib.SchemaError, msg=ftype):
                schema_lib.build_arguments(self.schema, table, [(name, "x")])

    # ---------- 参数校验 ----------
    def test_unknown_table_rejected(self) -> None:
        with self.assertRaises(schema_lib.SchemaError):
            schema_lib.build_arguments(self.schema, "不存在的表", [("S.客户", "x")])

    def test_unknown_field_rejected(self) -> None:
        table, name = self._first("Text")
        with self.assertRaises(schema_lib.SchemaError):
            schema_lib.build_arguments(self.schema, table, [(name + "_不存在", "x")])

    def test_duplicate_set_rejected(self) -> None:
        table, name = self._first("Text")
        with self.assertRaises(schema_lib.SchemaError):
            schema_lib.build_arguments(self.schema, table, [(name, "A"), (name, "B")])

    def test_empty_set_rejected(self) -> None:
        with self.assertRaises(schema_lib.SchemaError):
            schema_lib.build_arguments(self.schema, cfg.REQUIRED_TABLES[0], [])

    # ---------- Number 类型层（不套业务口径）----------
    def _number(self, raw: str) -> object:
        table, name = self._first("Number")
        args = schema_lib.build_arguments(self.schema, table, [(name, raw)])
        return args["fields"][0]["value"]

    def test_number_integer(self) -> None:
        self.assertEqual(self._number("20"), 20)

    def test_number_decimal(self) -> None:
        self.assertEqual(self._number("6.5"), 6.5)

    def test_number_scientific(self) -> None:
        self.assertEqual(self._number("1e3"), 1000.0)

    def test_number_negative_allowed_at_type_layer(self) -> None:
        # 正负是业务口径（point_util），类型层不拒绝
        self.assertEqual(self._number("-3"), -3)

    def test_number_text_rejected(self) -> None:
        with self.assertRaises(schema_lib.SchemaError):
            self._number("abc")

    # ---------- DateTime 格式 ----------
    def test_datetime_needs_full_format(self) -> None:
        try:
            table, name = self._first("DateTime")
        except unittest.SkipTest:
            return
        with self.assertRaises(schema_lib.SchemaError):
            schema_lib.build_arguments(self.schema, table, [(name, "2026-11-20")])
        with self.assertRaises(schema_lib.SchemaError):
            schema_lib.build_arguments(self.schema, table, [(name, "2026-11-20T00:00:00")])
        with self.assertRaises(schema_lib.SchemaError):
            schema_lib.build_arguments(self.schema, table, [(name, "2026-02-30 00:00:00")])
        args = schema_lib.build_arguments(self.schema, table, [(name, "2026-11-20 00:00:00")])
        self.assertEqual(args["fields"][0]["value"], "2026-11-20 00:00:00")


if __name__ == "__main__":
    unittest.main(verbosity=2)
