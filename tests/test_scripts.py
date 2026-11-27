"""数据层与工具函数回归测试：python3 -m unittest discover -s tests -v"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "timus-app-data" / "scripts"
PACK = ROOT / "skills" / "timus-app-data" / "references" / "timus-team.yaml"
sys.path.insert(0, str(SCRIPTS))

import date_util  # noqa: E402
import point_util  # noqa: E402
from data_tool import append_pack, query  # noqa: E402
from pack_lib import PackError, load_pack  # noqa: E402


class DataLayerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.pack = Path(self.temp.name) / "pack.yaml"
        shutil.copyfile(PACK, self.pack)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _real_app(self) -> None:
        text = self.pack.read_text(encoding="utf-8")
        text = text.replace("TODO_APP_A", "REAL_APP_A").replace("TODO_TEAM_CODE_A", "REAL_TEAM_A")
        self.pack.write_text(text, encoding="utf-8")

    def _script(self, name: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPTS / name), *args], capture_output=True, text=True)

    def test_pack_requires_team_code(self) -> None:
        self.assertEqual(load_pack(str(self.pack))["apps"]["TODO_APP_A"]["team_code"], "TODO_TEAM_CODE_A")
        text = self.pack.read_text(encoding="utf-8").replace("team_code: TODO_TEAM_CODE_A\n", "")
        self.pack.write_text(text, encoding="utf-8")
        with self.assertRaises(PackError):
            load_pack(str(self.pack))

    def test_list_alias_returns_json(self) -> None:
        proc = self._script("data_tool.py", "--pack", str(self.pack), "list", "--app", "B")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["apps"][0]["app"], "TODO_APP_B")

    def test_resolve_exposes_mcp_params(self) -> None:
        proc = self._script("data_tool.py", "--pack", str(self.pack), "resolve", "table",
                            "--app", "B", "--name", "customer", "--allow-demo")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual((data["app_name"], data["table_name"], data["platform_table"]),
                         ("TODO_TEAM_CODE_B", "客户", "客户"))
        self.assertNotIn("platform", data)

    def test_resolve_field_uses_unambiguous_key(self) -> None:
        proc = self._script("data_tool.py", "--pack", str(self.pack), "resolve", "field",
                            "--app", "B", "--table", "customer", "--name", "sys.customer_name", "--allow-demo")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["field"], "sys.customer_name")
        self.assertEqual(data["platform_field"], "S.客户")
        self.assertNotIn("platform", data)

    def test_resolve_rejects_demo_params_without_opt_in(self) -> None:
        proc = self._script("data_tool.py", "--pack", str(self.pack), "resolve", "table",
                            "--app", "B", "--name", "customer")
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        self.assertIn("示例配置", proc.stderr)

    def test_query_accepts_field_alias(self) -> None:
        pack = load_pack(str(self.pack))
        rows = query(pack, "TODO_APP_A", "member", ["角色=财务"], ["sys.member_name"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["fields"]["sys.member_name"], "左左")

    def test_readonly_field_rejected(self) -> None:
        self._real_app()
        pack = load_pack(str(self.pack))
        with self.assertRaises(PackError):
            append_pack(str(self.pack), pack, "REAL_APP_A", "member", [{"sys.member_id": "X"}])

    def test_append_pack_local_marker_and_roundtrip(self) -> None:
        self._real_app()
        pack = load_pack(str(self.pack))
        result = append_pack(str(self.pack), pack, "REAL_APP_A", "member", [{"sys.member_name": "新成员"}])
        self.assertFalse(result["platformWritten"])
        record_id = result["localRecordIds"][0]
        reloaded = load_pack(str(self.pack))
        row = reloaded["apps"]["REAL_APP_A"]["records"]["member"][record_id]
        self.assertEqual(row["sys.member_name"], "新成员")

    def test_invalid_value_rejected(self) -> None:
        self._real_app()
        pack = load_pack(str(self.pack))
        with self.assertRaises(PackError):
            append_pack(str(self.pack), pack, "REAL_APP_A", "member", [{"sys.member_name": "坏#值"}])


class UtilTests(unittest.TestCase):
    def test_point_split_sum(self) -> None:
        result = point_util.split("10", ["1", "2", "3"])
        self.assertEqual(sum(item["cents"] for item in result["items"]), 1000)

    def test_point_split_minimum(self) -> None:
        with self.assertRaises(point_util.PointError):
            point_util.split("0.01", ["1", "1"])

    def test_date_range_rejects_reverse(self) -> None:
        with self.assertRaises(ValueError):
            date_util._range_payload(date(2026, 1, 2), 1, 0)


class CliContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)
        self.pack = self.dir / "pack.yaml"
        shutil.copyfile(PACK, self.pack)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _script(self, name: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPTS / name), *args], capture_output=True, text=True)

    def _write_payload(self, title: str = "确认预览") -> Path:
        path = self.dir / "payload.json"
        path.write_text(json.dumps({"title": title, "columns": [{"key": "name", "label": "名称"}],
                                    "rows": [{"name": "甲"}], "badges": []}, ensure_ascii=False), encoding="utf-8")
        return path

    def test_build_html_renders_and_escapes(self) -> None:
        payload = self._write_payload("</script><b>标题</b>")
        output = self.dir / "page.html"
        proc = self._script("build_html.py", "--payload", str(payload), "--output", str(output))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        text = output.read_text(encoding="utf-8")
        self.assertIn("<\\/script", text)
        self.assertNotIn("__DATA_JSON__", text)
        self.assertEqual(json.loads(proc.stdout)["rows"], 1)

    def test_build_html_rejects_outside_output_and_overwrite(self) -> None:
        payload = self._write_payload()
        outside = Path("/etc/timus_agent_template_review.html")
        proc = self._script("build_html.py", "--payload", str(payload), "--output", str(outside))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("输出路径", proc.stderr)

        output = self.dir / "page.html"
        output.write_text("existing", encoding="utf-8")
        args = ("--payload", str(payload), "--output", str(output))
        self.assertEqual(self._script("build_html.py", *args).returncode, 2)
        forced = self._script("build_html.py", *args, "--force")
        self.assertEqual(forced.returncode, 0, forced.stderr)

    def test_build_html_rejects_template_without_placeholders(self) -> None:
        payload = self._write_payload()
        template = self.dir / "bad.tpl"
        template.write_text("<html></html>", encoding="utf-8")
        proc = self._script("build_html.py", "--payload", str(payload), "--output",
                            str(self.dir / "page.html"), "--template", str(template))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("占位符", proc.stderr)

    def test_add_data_cli_success_and_error_contract(self) -> None:
        text = self.pack.read_text(encoding="utf-8")
        self.pack.write_text(text.replace("TODO_APP_A", "REAL_APP_A")
                             .replace("TODO_TEAM_CODE_A", "REAL_TEAM_A"), encoding="utf-8")
        good = self._script("add_data.py", "--pack", str(self.pack), "--app", "REAL_APP_A",
                            "--table", "member", "--row", "sys.member_name=新人")
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertFalse(json.loads(good.stdout)["platformWritten"])

        bad = self._script("add_data.py", "--pack", str(self.pack), "--app", "REAL_APP_A",
                           "--table", "member", "--row", "sys.member_name=坏#值")
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(bad.stdout, "")
        self.assertTrue(bad.stderr)

    def test_util_cli_minimal_paths(self) -> None:
        points = self._script("point_util.py", "normalize", "6.567")
        self.assertEqual(points.returncode, 0, points.stderr)
        self.assertEqual(json.loads(points.stdout)["text"], "6.57")
        days = self._script("date_util.py", "options", "--base", "2026-01-01", "--count", "2")
        self.assertEqual(days.returncode, 0, days.stderr)
        self.assertEqual(len(json.loads(days.stdout)), 2)


if __name__ == "__main__":
    unittest.main()
