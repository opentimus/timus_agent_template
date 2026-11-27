#!/usr/bin/env python3
"""语义包数据维护：查 / 改 / 删 / 解析 / 列表；仅操作本地缓存，平台写入走连接器 MCP。纯标准库。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from errors import ToolError, emit_error
from pack_lib import (  # pyright: ignore[reportMissingImports]
    PackError, atomic_write, dump_pack, load_pack, pack_lock, platform_field,
    platform_table, quote, resolve_app, resolve_field, resolve_table, unquote,
)

SKILL = Path(__file__).resolve().parents[1]
DEFAULT_PACK = SKILL / "references" / "timus-team.yaml"


def _records(pack: dict[str, Any], app: str, table: str) -> dict[str, Any]:
    return pack["apps"][app]["records"].get(table, {})


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
    upper = text.upper()
    return (not text or upper.startswith("TODO") or text.startswith("tblDemo")
            or "_RECORD_" in upper or (text.startswith("<") and text.endswith(">")))


def _ensure_writable(pack: dict[str, Any], app: str) -> None:
    team_code = str(pack["apps"][app].get("team_code") or "")
    for label, value in (("应用名", app), ("team_code", team_code)):
        if _is_placeholder(value):
            raise PackError("{} {} 仍为占位符，禁止写入；请先落盘真实编码".format(label, value))


def _ensure_platform_ready(pack: dict[str, Any], app: str, table: str,
                           allow_demo: bool, extra: tuple[str, ...] = ()) -> None:
    """防止示例 ID / 占位 app_name 被当作 MCP 参数。"""
    pairs = (("app_name", str(pack["apps"][app].get("team_code") or "")),
             ("table_id", str(pack["apps"][app]["tables"][table].get("id") or "")),
             *[("platform_value", value) for value in extra])
    bad = ["{}={}".format(label, value) for label, value in pairs if _is_placeholder(value)]
    if bad and not allow_demo:
        raise PackError("语义包仍为示例配置（{}），禁止作为平台参数；"
                        "请替换为真实编码，或加 --allow-demo 仅做本地解析".format("、".join(bad)))


def _clean_value(value: str) -> str:
    """校验值格式（无 # / 引号）并去首尾空白。"""
    return unquote(quote(value.strip()))


def _validate_type(field_type: str, value: str, field: str) -> None:
    kind = field_type.split("@", 1)[0]
    if kind == "Number":
        try:
            Decimal(value)
        except (InvalidOperation, ValueError):
            raise PackError("字段 {} 的值 {} 不是有效数值".format(field, value))
    elif kind == "DateTime":
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", value):
            raise PackError("字段 {} 的值 {} 应为 YYYY-MM-DD HH:mm:ss".format(field, value))


def _writable_field(pack: dict[str, Any], app: str, table: str, name: str) -> str:
    """解析字段别名并拒绝只读字段。"""
    canonical = resolve_field(pack, app, table, name)
    spec = pack["apps"][app]["fields"][table][canonical]
    if str(spec.get("type", "")).endswith("@read_only"):
        raise PackError("字段 {} 为只读，不可写入".format(canonical))
    return canonical


def query(pack: dict[str, Any], app: str, table: str, where: list[str], fields: list[str]) -> list[dict[str, Any]]:
    a = resolve_app(pack, app)
    t = resolve_table(pack, a, table)
    conditions = [(resolve_field(pack, a, t, name), value) for name, value in _conditions(where)]
    selected = [resolve_field(pack, a, t, name) for name in fields] or None
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


def mutate_unlocked(path: str, pack: dict[str, Any], app: str, table: str, record: str, sets: list[str], delete: bool, where: list[str]) -> dict[str, Any]:
    a = resolve_app(pack, app)
    t = resolve_table(pack, a, table)
    _ensure_writable(pack, a)
    rows = _records(pack, a, t)
    if not record:
        conditions = [(resolve_field(pack, a, t, name), value) for name, value in _conditions(where)]
        record = _locate_record(rows, conditions)
    elif record not in rows:
        raise PackError("应用 {} 的表 {} 中不存在记录：{}。可用记录：{}".format(a, t, record, ", ".join(rows)))

    changes: dict[str, str] = {}
    if not delete:
        for raw in sets:
            if "=" not in raw:
                raise PackError("--set 格式应为 字段=值：{}".format(raw))
            name, value = raw.split("=", 1)
            canonical = _writable_field(pack, a, t, name.strip())
            if canonical not in rows[record]:
                raise PackError("记录 {} 中没有字段 {}，不可新增字段".format(record, canonical))
            text = _clean_value(value)
            _validate_type(str(pack["apps"][a]["fields"][t][canonical].get("type", "")), text, canonical)
            changes[canonical] = text

    if delete:
        del rows[record]
    else:
        rows[record].update(changes)
    atomic_write(path, dump_pack(pack))
    return {"app": a, "table": t, "record": record, "deleted": delete, "changed": changes}


def mutate(path: str, pack: dict[str, Any], app: str, table: str, record: str, sets: list[str], delete: bool, where: list[str]) -> dict[str, Any]:
    """库入口：内部加锁。若调用方已持有 pack_lock，请改用 mutate_unlocked。"""
    with pack_lock(path):
        return mutate_unlocked(path, pack, app, table, record, sets, delete, where)


def _next_ids(existing: dict[str, Any], count: int, prefix: str = "rec") -> list[str]:
    used = {int(m.group(1)) for name in existing if (m := re.search(r"(\d+)$", name))}
    number = max(used, default=0)
    result: list[str] = []
    while len(result) < count:
        number += 1
        if number not in used:
            result.append("{}{:03d}".format(prefix, number))
    return result


def append_pack_unlocked(path: str, pack: dict[str, Any], app: str, table: str, rows: list[dict[str, str]]) -> dict[str, Any]:
    a = resolve_app(pack, app)
    t = resolve_table(pack, a, table)
    _ensure_writable(pack, a)
    cleaned: list[dict[str, str]] = []
    for row in rows:
        item: dict[str, str] = {}
        for name, value in row.items():
            canonical = _writable_field(pack, a, t, name)
            text = _clean_value(value)
            _validate_type(str(pack["apps"][a]["fields"][t][canonical].get("type", "")), text, canonical)
            item[canonical] = text
        cleaned.append(item)
    target = pack["apps"][a]["records"].setdefault(t, {})
    ids = _next_ids(target, len(cleaned))
    for record_id, fields in zip(ids, cleaned):
        target[record_id] = fields
    atomic_write(path, dump_pack(pack))
    return {"app": a, "table": t, "added": len(cleaned),
            "localRecordIds": ids, "platformWritten": False}


def append_pack(path: str, pack: dict[str, Any], app: str, table: str, rows: list[dict[str, str]]) -> dict[str, Any]:
    """库入口：内部加锁。若调用方已持有 pack_lock，请改用 append_pack_unlocked。"""
    with pack_lock(path):
        return append_pack_unlocked(path, pack, app, table, rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="语义包数据维护（查 / 改 / 删 / 解析 / 列表）")
    parser.add_argument("--pack", default=str(DEFAULT_PACK), help="语义包 YAML 路径")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="列出应用与各表记录数")
    p.add_argument("--app", default="", help="只列该应用")

    p = sub.add_parser("resolve", help="解析名称到稳定 ID 与平台标识")
    p.add_argument("kind", choices=("table", "field"))
    p.add_argument("--app", required=True)
    p.add_argument("--table", default="", help="field 时必填")
    p.add_argument("--name", required=True, help="待解析的表名 / 字段名")
    p.add_argument("--allow-demo", action="store_true", help="允许解析示例占位配置（仅本地查看，不可作为平台参数）")

    p = sub.add_parser("query", help="查询本地记录")
    p.add_argument("--app", required=True)
    p.add_argument("--table", required=True)
    p.add_argument("--where", action="append", default=[], metavar="字段=值", help="过滤条件，可重复，AND")
    p.add_argument("--fields", action="append", nargs="+", default=[], metavar="字段", help="返回字段，可多值 / 重复")

    p = sub.add_parser("set", help="修改本地记录")
    p.add_argument("--app", required=True)
    p.add_argument("--table", required=True)
    p.add_argument("--record", default="", help="记录 ID；不传时用 --where 定位唯一记录")
    p.add_argument("--where", action="append", default=[], metavar="字段=值")
    p.add_argument("--set", dest="sets", action="append", nargs="+", required=True, metavar="字段=值", help="改字段，可多值 / 重复")

    p = sub.add_parser("delete", help="删除本地记录")
    p.add_argument("--app", required=True)
    p.add_argument("--table", required=True)
    p.add_argument("--record", default="", help="记录 ID；不传时用 --where 定位唯一记录")
    p.add_argument("--where", action="append", default=[], metavar="字段=值")

    args = parser.parse_args()

    try:
        if args.command == "list":
            pack = load_pack(args.pack, args.app)
            app = resolve_app(pack, args.app) if args.app else ""
            items = ({app: pack["apps"][app]} if app else pack["apps"])
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
            app_name = str(pack["apps"][a]["team_code"])
            if args.kind == "table":
                table_name = platform_table(pack, a, t)
                _ensure_platform_ready(pack, a, t, args.allow_demo, (table_name,))
                result: dict[str, Any] = {"app": a, "table": t, "app_name": app_name,
                                          "table_name": table_name, "platform_table": table_name}
            else:
                field = resolve_field(pack, a, t, args.name)
                field_name = platform_field(pack, a, t, field)
                _ensure_platform_ready(pack, a, t, args.allow_demo, (field_name,))
                result = {"app": a, "table": t, "field": field, "app_name": app_name,
                          "table_name": platform_table(pack, a, t),
                          "platform_field": field_name}
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        if args.command == "query":
            pack = load_pack(args.pack, args.app, (args.table,))
            a = resolve_app(pack, args.app)
            fields = [name for group in args.fields for name in group]
            records = query(pack, args.app, args.table, args.where, fields)
            result = {"app": a, "table": resolve_table(pack, a, args.table),
                      "count": len(records), "records": records}
        else:
            sets = [item for group in args.sets for item in group] if args.command == "set" else []
            with pack_lock(args.pack):
                pack = load_pack(args.pack, args.app, (args.table,))
                result = mutate_unlocked(args.pack, pack, args.app, args.table, args.record, sets,
                                         args.command == "delete", args.where)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ToolError, OSError) as err:
        emit_error(err)
        sys.exit(2)


if __name__ == "__main__":
    main()
