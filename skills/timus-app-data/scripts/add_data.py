#!/usr/bin/env python3
"""基础数据批量添加：直接写入或从源表复制后写入。纯标准库。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from data_tool import append_pack, load_pack, query, resolve_app, resolve_table
from pack_lib import PackError

DEFAULT_PACK = Path(__file__).resolve().parents[1] / "references" / "timus-team.yaml"


def _parse_rows(items: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw in items:
        fields: dict[str, str] = {}
        for pair in raw.split("|"):
            if "=" not in pair:
                raise PackError("字段格式应为 字段=值：{}".format(pair))
            name, value = pair.split("=", 1)
            fields[name.strip()] = value.strip()
        rows.append(fields)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="批量添加本地基础数据")
    parser.add_argument("--pack", default=str(DEFAULT_PACK), help="语义包 YAML 路径")
    parser.add_argument("--app", required=True, help="目标应用名")
    parser.add_argument("--table", required=True, help="目标应用下的表")
    parser.add_argument("--row", dest="items", action="append", default=[],
                        metavar="字段=值|字段=值", help="一条记录；可重复多条")
    parser.add_argument("--from", dest="source", metavar="源表", help="从同一应用的源表查记录并写入目标表")
    parser.add_argument("--where", action="append", default=[], metavar="字段=值", help="源表过滤条件，可重复，AND")
    parser.add_argument("--map", dest="maps", action="append", default=[], metavar="目标字段=源字段", help="字段映射，可重复")
    args = parser.parse_args()

    if not args.items and not args.source:
        parser.error("需要 --row 或 --from")
    if args.source:
        if args.items:
            parser.error("--row 与 --from 互斥")
        if not args.maps:
            parser.error("--from 需要 --map")
    elif args.where or args.maps:
        parser.error("--where / --map 仅用于 --from")

    try:
        if args.source:
            pack = load_pack(args.pack, args.app, (args.table, args.source))
            app = resolve_app(pack, args.app)
            source = resolve_table(pack, app, args.source)
            maps: list[tuple[str, str]] = []
            for raw in args.maps:
                if "=" not in raw:
                    raise PackError("--map 格式应为 目标字段=源字段：{}".format(raw))
                target, field = raw.split("=", 1)
                maps.append((target.strip(), field.strip()))
            records = query(pack, app, source, args.where, [name for _, name in maps])
            if not records:
                raise PackError("源表 {} 未找到匹配记录".format(source))
            rows = [
                {target: record["fields"].get(field, "") for target, field in maps}
                for record in records
            ]
        else:
            pack = load_pack(args.pack, args.app, (args.table,))
            rows = _parse_rows(args.items)
        result = append_pack(args.pack, pack, args.app, args.table, rows)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (PackError, OSError) as err:
        print("参数错误：{}".format(err), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
