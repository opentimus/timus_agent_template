#!/usr/bin/env python3
"""把语义包中的表名与字段值编译成 timus-runtime 连接器的工具参数。

降级 / 查询工具：录入热路径直接构造参数，字段不确定或写入报错时才用它复核。
两包共用同一份代码，语义包内容各自独立。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import cast

# 本文件按脚本方式执行（python3 .../resolve_schema.py），同目录模块需隐式相对导入
import schema_lib  # pyright: ignore[reportImplicitRelativeImport]

DEFAULT_SCHEMA = Path(__file__).resolve().parents[1] / "references" / "timus-team-schema.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate apaas_add_record arguments from the Timus SPMP schema."
    )
    _ = parser.add_argument("--schema", default=str(DEFAULT_SCHEMA), help="语义包 YAML 路径")
    _ = parser.add_argument("--list-tables", action="store_true", help="列出所有表单")
    _ = parser.add_argument("--list-fields", action="store_true", help="列出指定表单的字段")
    _ = parser.add_argument("--table", default="", help="表单名，取语义包 tables 下的表单名")
    _ = parser.add_argument(
        "--set",
        dest="set_values",
        action="append",
        default=[],
        metavar="字段名=值",
        help="要写入的系统字段名与值，可重复",
    )
    return parser.parse_args()


def parse_sets(values: list[str]) -> list[tuple[str, str]]:
    sets: list[tuple[str, str]] = []
    for raw in values:
        if "=" not in raw:
            raise schema_lib.SchemaError("--set 格式应为 字段名=值，收到：{}".format(raw))
        name, value = raw.split("=", 1)
        name = name.strip()
        if not name:
            raise schema_lib.SchemaError("--set 的字段名不能为空：{}".format(raw))
        sets.append((name, value.strip()))
    return sets


def main() -> None:
    args = parse_args()
    try:
        schema = schema_lib.load_schema(cast(str, args.schema))
        meta = schema["meta"]
        if not isinstance(meta, dict):
            raise schema_lib.SchemaError("语义包结构不完整")

        if cast(bool, args.list_tables):
            print(
                json.dumps(
                    {"team_code": meta["team_code"], "tables": schema_lib.list_tables(schema)},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return

        table = cast(str, args.table)
        if cast(bool, args.list_fields):
            if not table:
                raise schema_lib.SchemaError("--list-fields 需要同时指定 --table")
            print(
                json.dumps(
                    {"table": table, "fields": schema_lib.list_fields(schema, table)},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return

        if not table:
            raise schema_lib.SchemaError("生成参数需要 --table 与至少一个 --set 字段名=值")
        sets = parse_sets(cast(list[str], args.set_values))
        print(json.dumps(schema_lib.build_arguments(schema, table, sets), ensure_ascii=False, indent=2))
    except (schema_lib.SchemaError, OSError) as err:
        print("参数错误：{}".format(err), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
