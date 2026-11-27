#!/usr/bin/env python3
"""语义包数据维护：查 / 改 / 删 / 解析 / 列表，原地改写单文件 YAML。纯标准库。"""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any

from pack_lib import (  # pyright: ignore[reportMissingImports]
    PackError, dump_pack, list_fields, load_pack, platform_field, platform_table,
    quote, resolve_app, resolve_field, resolve_table, unquote,
)

SKILL = Path(__file__).resolve().parents[1]
DEFAULT_PACK = SKILL / "references" / "timus-team.yaml"


def _records(pack: dict[str, Any], app: str, table: str) -> dict[str, Any]:
    return pack["apps"][app]["records"].get(table, {})


def _check_fields(pack: dict[str, Any], app: str, table: str, names: list[str]) -> None:
    known = set(list_fields(pack, app, table))
    for name in names:
        if name not in known:
            raise PackError("字段 {} 不在表 {} 表头元数据中".format(name, table))


def _conditions(raws: list[str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for raw in raws:
        if "=" not in raw:
            raise PackError("--where 格式应为 字段=值：{}".format(raw))
        name, value = raw.split("=", 1)
        out.append((name.strip(), value.strip()))
    return out


def _is_placeholder(value: str) -> bool:
    text = value.strip()
    return not text or text.upper().startswith("TODO") or (text.startswith("<") and text.endswith(">"))


def _ensure_writable(app: str) -> None:
    if _is_placeholder(app):
        raise PackError("应用名 {} 仍为占位符，禁止写入；请先落盘真实编码".format(app))


def query(pack: dict[str, Any], app: str, table: str, where: list[str], fields: list[str]) -> list[dict[str, Any]]:
    a = resolve_app(pack, app)
    t = resolve_table(pack, a, table)
    conditions = _conditions(where)
    selected = fields or None
    _check_fields(pack, a, t, [name for name, _ in conditions] + (selected or []))
    result: list[dict[str, Any]] = []
    for record_id, row in _records(pack, a, t).items():
        if all(row.get(name) == value for name, value in conditions):
            picked = {key: row[key] for key in selected if key in row} if selected else dict(row)
            result.append({"record_id": record_id, "fields": picked})
    return result


def _locate_record(rows: dict[str, Any], conditions: list[tuple[str, str]]) -> str:
    hits = [rid for rid, row in rows.items() if all(row.get(name) == value for name, value in conditions)]
    if not hits:
        raise PackError("未找到匹配记录")
    if len(hits) > 1:
        raise PackError("匹配到 {} 条记录，请补条件或给 --record".format(len(hits)))
    return hits[0]


def mutate(path: str, pack: dict[str, Any], app: str, table: str, record: str, sets: list[str], delete: bool, where: list[str]) -> dict[str, Any]:
    a = resolve_app(pack, app)
    t = resolve_table(pack, a, table)
    _ensure_writable(a)
    rows = _records(pack, a, t)
    if not record:
        conditions = _conditions(where)
        _check_fields(pack, a, t, [name for name, _ in conditions])
        record = _locate_record(rows, conditions)
    elif record not in rows:
        raise PackError("应用 {} 的表 {} 中不存在记录：{}。可用记录：{}".format(a, t, record, ", ".join(rows)))

    changes: dict[str, str] = {}
    if not delete:
        names: list[str] = []
        for raw in sets:
            if "=" not in raw:
                raise PackError("--set 格式应为 字段=值：{}".format(raw))
            name, value = raw.split("=", 1)
            names.append(name.strip())
            if name.strip() not in rows[record]:
                raise PackError("记录 {} 中没有字段 {}，不可新增字段".format(record, name.strip()))
            changes[names[-1]] = quote(value.strip())
        _check_fields(pack, a, t, names)

    if delete:
        del rows[record]
    else:
        for name, value in changes.items():
            rows[record][name] = unquote(value)
    Path(path).write_text(dump_pack(pack), encoding="utf-8")
    return {"app": a, "table": t, "record": record, "deleted": delete,
            "changed": {name: unquote(value) for name, value in changes.items()}}


def _next_ids(existing: dict[str, Any], count: int, prefix: str = "rec") -> list[str]:
    used = {int(m.group(1)) for name in existing if (m := re.search(r"(\d+)$", name))}
    number = max(used, default=0)
    result: list[str] = []
    while len(result) < count:
        number += 1
        if number not in used:
            result.append("{}{:03d}".format(prefix, number))
    return result


def append_pack(path: str, pack: dict[str, Any], app: str, table: str, rows: list[dict[str, str]]) -> dict[str, Any]:
    a = resolve_app(pack, app)
    t = resolve_table(pack, a, table)
    _ensure_writable(a)
    _check_fields(pack, a, t, [name for row in rows for name in row])
    target = pack["apps"][a]["records"].setdefault(t, {})
    ids = _next_ids(target, len(rows))
    for record_id, fields in zip(ids, rows):
        target[record_id] = dict(fields)
    Path(path).write_text(dump_pack(pack), encoding="utf-8")
    return {"app": a, "table": t, "added": len(rows), "records": ids, "traceId": uuid.uuid4().hex}


def main() -> None:
    parser = argparse.ArgumentParser(description="语义包数据维护（查 / 改 / 删 / 解析 / 列表）")
    parser.add_argument("--pack", default=str(DEFAULT_PACK), help="语义包 YAML 路径")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="列出应用与各表记录数")
    p.add_argument("--app", default="", help="只列该应用")

    p = sub.add_parser("resolve", help="解析名称到稳定 ID")
    p.add_argument("kind", choices=("table", "field"))
    p.add_argument("--app", required=True)
    p.add_argument("--table", default="", help="field 时必填")
    p.add_argument("--name", required=True, help="待解析的表名 / 字段名")

    p = sub.add_parser("query", help="查询记录")
    p.add_argument("--app", required=True)
    p.add_argument("--table", required=True)
    p.add_argument("--where", action="append", default=[], metavar="字段=值", help="过滤条件，可重复，AND")
    p.add_argument("--fields", action="append", nargs="+", default=[], metavar="字段", help="返回字段，可多值 / 重复")

    p = sub.add_parser("set", help="修改记录")
    p.add_argument("--app", required=True)
    p.add_argument("--table", required=True)
    p.add_argument("--record", default="", help="记录 ID；不传时用 --where 定位唯一记录")
    p.add_argument("--where", action="append", default=[], metavar="字段=值")
    p.add_argument("--set", dest="sets", action="append", nargs="+", required=True, metavar="字段=值", help="改字段，可多值 / 重复")

    p = sub.add_parser("delete", help="删除记录")
    p.add_argument("--app", required=True)
    p.add_argument("--table", required=True)
    p.add_argument("--record", default="", help="记录 ID；不传时用 --where 定位唯一记录")
    p.add_argument("--where", action="append", default=[], metavar="字段=值")

    args = parser.parse_args()

    try:
        if args.command == "list":
            pack = load_pack(args.pack, args.app)
            items = ({args.app: pack["apps"][args.app]} if args.app else pack["apps"])
            payload = [
                {"app": name, "tables": [
                    {"name": table, "records": len(item["records"].get(table, {}))}
                    for table in item["tables"]
                ]}
                for name, item in items.items()
            ]
            print(json.dumps({"apps": payload}, ensure_ascii=False, indent=2))
            return

        if args.command == "resolve":
            if args.kind == "field" and not args.table:
                raise PackError("resolve field 需要 --table")
            token = args.table if args.kind == "field" else (args.table or args.name)
            pack = load_pack(args.pack, args.app, (token,))
            a = resolve_app(pack, args.app)
            t = resolve_table(pack, a, token)
            if args.kind == "table":
                result: dict[str, Any] = {"app": a, "table": t, "platform": platform_table(pack, a, t)}
            else:
                field = resolve_field(pack, a, t, args.name)
                result = {"app": a, "table": t, "field": field, "platform": platform_field(pack, a, t, field)}
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        pack = load_pack(args.pack, args.app, (args.table,))
        if args.command == "query":
            fields = [name for group in args.fields for name in group]
            records = query(pack, args.app, args.table, args.where, fields)
            result = {"app": resolve_app(pack, args.app), "table": args.table,
                      "count": len(records), "records": records}
        else:
            sets = [item for group in args.sets for item in group] if args.command == "set" else []
            result = mutate(args.pack, pack, args.app, args.table, args.record, sets,
                            args.command == "delete", args.where)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (PackError, OSError) as err:
        print("参数错误：{}".format(err), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
