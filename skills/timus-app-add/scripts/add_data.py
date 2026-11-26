#!/usr/bin/env python3
"""基础数据批量添加：解析参数后调用 data_tool.append。纯标准库。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import cast

SKILLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILLS / "timus-app-maintenance" / "scripts"))

from data_tool import DataError, append  # pyright: ignore[reportMissingImports]

DEFAULT_PACK = SKILLS / "timus-app-maintenance" / "references" / "timus-team.yaml"


def main() -> None:
    parser = argparse.ArgumentParser(description="批量添加本地基础数据")
    parser.add_argument("--pack", default=str(DEFAULT_PACK), help="语义包 YAML 路径（表头元数据 + 本地记录）")
    parser.add_argument("--app", required=True, help="目标应用（本地应用名或 app_name）")
    parser.add_argument("--table", required=True, help="目标应用下的表")
    parser.add_argument("--set", dest="items", action="append", required=True,
                        metavar="字段=值|字段=值", help="一条记录；可重复多条")
    args = parser.parse_args()
    try:
        result = append(
            cast(str, args.pack), cast(str, args.app), cast(str, args.table), cast(list[str], args.items),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (DataError, OSError) as err:
        print("参数错误：{}".format(err), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
