#!/usr/bin/env python3
"""把 payload JSON 渲染为自包含 HTML 页面。纯标准库。"""
from __future__ import annotations

import argparse
import html
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
DEFAULT_TEMPLATE = HERE.parent / "assets" / "app.html.tpl"


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="生成 Timus 数据页面",
        epilog="payload: {title, columns:[{key,label?}], rows:[{}], subtitle?, badges?, editable?, tableTitle?, tableHint?, note?}",
    )
    parser.add_argument("--payload", required=True, help="页面数据 JSON")
    parser.add_argument("--output", required=True, help="输出 HTML 路径（须在项目目录 / 当前目录 / 临时目录内）")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="模板路径")
    parser.add_argument("--force", action="store_true", help="允许覆盖已存在的输出文件")
    args = parser.parse_args()

    try:
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        template = Path(args.template).read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError) as err:
        print("读取失败：{}".format(err), file=sys.stderr)
        return 2

    if not isinstance(payload, dict) or not payload.get("title"):
        print("payload 须为对象且包含 title", file=sys.stderr)
        return 2
    rows = payload.get("rows", [])
    columns = payload.get("columns", [])
    if not isinstance(rows, list) or not isinstance(columns, list):
        print("rows / columns 须为数组", file=sys.stderr)
        return 2
    if not all(isinstance(row, dict) for row in rows):
        print("rows[] 每项须为对象", file=sys.stderr)
        return 2
    if not all(isinstance(c, dict) and isinstance(c.get("key"), str) and c["key"] for c in columns):
        print("columns[] 每项须含非空字符串 key", file=sys.stderr)
        return 2
    badges = payload.get("badges", [])
    if not isinstance(badges, list) or not all(
        isinstance(b, dict) and "label" in b and "value" in b for b in badges
    ):
        print("badges[] 每项须含 label 与 value", file=sys.stderr)
        return 2
    if "__TITLE__" not in template or "__DATA_JSON__" not in template:
        print("模板缺少 __TITLE__ 或 __DATA_JSON__ 占位符", file=sys.stderr)
        return 2

    data = (json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))
    page = template.replace("__TITLE__", html.escape(str(payload["title"]))).replace("__DATA_JSON__", data)
    output = Path(args.output).expanduser().resolve()
    roots = (WORKSPACE, Path.cwd().resolve(), Path(tempfile.gettempdir()).resolve())
    if not any(_inside(output, root) for root in roots):
        print("输出路径须在项目目录 / 当前目录 / 临时目录内：{}".format(output), file=sys.stderr)
        return 2
    if output.exists() and not args.force:
        print("输出文件已存在，如需覆盖请加 --force：{}".format(output), file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8")
    print(json.dumps({"output": str(output), "rows": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
