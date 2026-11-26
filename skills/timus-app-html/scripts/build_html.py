#!/usr/bin/env python3
"""把 payload JSON 渲染为自包含 HTML 页面。纯标准库。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = HERE.parent / "assets" / "app.html.tpl"


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 Timus 数据页面")
    parser.add_argument("--payload", required=True, help="页面数据 JSON")
    parser.add_argument("--output", required=True, help="输出 HTML 路径")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="模板路径")
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

    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace("__TITLE__", str(payload["title"])).replace("__DATA_JSON__", data)
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    print("已生成 {}（{} 行）".format(output, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
