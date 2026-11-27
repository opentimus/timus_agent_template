#!/usr/bin/env python3
"""基础数据批量添加：直接写入或从源表复制后写入。纯标准库。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import cast

SKILLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILLS / "timus-app-maintenance" / "scripts"))

from data_tool import (  # pyright: ignore[reportMissingImports]
    DataError, append, append_pack, load_pack, query, resolve_app, resolve_table,
)

DEFAULT_PACK = SKILLS / "timus-app-maintenance" / "references" / "timus-team.yaml"


def main() -> None:
    parser = argparse.ArgumentParser(description="批量添加本地基础数据")
    parser.add_argument("--pack", default=str(DEFAULT_PACK), help="语义包 YAML 路径（表头元数据 + 本地记录）")
    parser.add_argument("--app", required=True, help="目标应用名")
    parser.add_argument("--table", required=True, help="目标应用下的表")
    parser.add_argument("--set", dest="items", action="append", default=[],
                        metavar="字段=值|字段=值", help="一条记录；可重复多条")
    parser.add_argument("--copy-from", metavar="源表", help="从同一应用的源表查记录并写入目标表")
    parser.add_argument("--where", action="append", default=[], metavar="字段=值", help="源表过滤条件，可重复，AND")
    parser.add_argument("--map", dest="maps", action="append", default=[], metavar="目标字段=源字段", help="字段映射，可重复")
    args = parser.parse_args()

    if not args.items and not args.copy_from:
        parser.error("需要 --set 或 --copy-from")
    if args.copy_from:
        if args.items:
            parser.error("--set 与 --copy-from 互斥")
        if not args.maps:
            parser.error("--copy-from 需要 --map")
    elif args.where or args.maps:
        parser.error("--where / --map 仅用于 --copy-from")

    try:
        if args.copy_from:
            pack = load_pack(args.pack, args.app, (args.table, args.copy_from))
            app = resolve_app(pack, args.app)
            source = resolve_table(pack, app, args.copy_from)
            maps: list[tuple[str, str]] = []
            for raw in args.maps:
                if "=" not in raw:
                    raise DataError("--map 格式应为 目标字段=源字段：{}".format(raw))
                target_field, source_field = raw.split("=", 1)
                maps.append((target_field.strip(), source_field.strip()))
            records = query(pack, app, source, args.where, [name for _, name in maps])
            if not records:
                raise DataError("源表 {} 未找到匹配记录".format(source))
            items = [
                "|".join("{}={}".format(target, cast(dict[str, str], record["fields"]).get(source_field, ""))
                         for target, source_field in maps)
                for record in records
            ]
            result = append_pack(cast(str, args.pack), pack, cast(str, args.app), cast(str, args.table), items)
        else:
            result = append(
                cast(str, args.pack), cast(str, args.app), cast(str, args.table), cast(list[str], args.items),
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (DataError, OSError) as err:
        print("参数错误：{}".format(err), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
