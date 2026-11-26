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

DEFAULT_DATA = SKILLS / "timus-app-maintenance" / "references" / "timus-team-data.yaml"
DEFAULT_SCHEMA = SKILLS / "timus-app-maintenance" / "references" / "timus-team-schema.yaml"


def main() -> None:
    parser = argparse.ArgumentParser(description="批量添加本地基础数据")
    parser.add_argument("--data", default=str(DEFAULT_DATA), help="基础数据 YAML 路径")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA), help="表头元数据路径（字段校验）")
    parser.add_argument("--table", required=True, help="目标表")
    parser.add_argument("--set", dest="items", action="append", required=True,
                        metavar="字段=值|字段=值", help="一条记录；可重复多条")
    args = parser.parse_args()
    try:
        result = append(
            cast(str, args.data), cast(str, args.schema), cast(str, args.table),
            cast(list[str], args.items),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (DataError, OSError) as err:
        print("参数错误：{}".format(err), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
