#!/usr/bin/env python3
"""语义包数据维护：查 / 改 / 删 / 追加，原地改写单文件 YAML。纯标准库。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import cast

from pack_lib import (  # pyright: ignore[reportMissingImports]
    PackError as DataError, iter_lines, list_fields, load_pack, platform_field, platform_table,
    resolve_app, resolve_field, resolve_table, unquote,
)

SKILL = Path(__file__).resolve().parents[1]
DEFAULT_PACK = SKILL / "references" / "timus-team.yaml"


def _app(pack: dict[str, object], app: str) -> dict[str, object]:
    return cast(dict[str, object], cast(dict[str, object], pack["apps"])[app])


def _records(pack: dict[str, object], app: str, table: str) -> dict[str, dict[str, str]]:
    return cast(dict[str, dict[str, str]], cast(dict[str, object], _app(pack, app)["records"]).get(table, {}))


def _known(pack: dict[str, object], app: str, table: str) -> set[str]:
    return {str(item["name"]) for item in list_fields(pack, app, table)}


def _is_placeholder(value: str) -> bool:
    text = value.strip()
    return not text or text.upper().startswith("TODO") or (text.startswith("<") and text.endswith(">"))


def _ensure_writable(app: str) -> None:
    if _is_placeholder(app):
        raise DataError("应用名 {} 仍为占位符，禁止写入；请先落盘真实编码".format(app))


def format_value(new_value: str) -> str:
    if "#" in new_value or '"' in new_value or "'" in new_value:
        raise DataError("值不能包含 # 或引号：{}".format(new_value))
    return '"{}"'.format(new_value)


def query(pack: dict[str, object], app: str, table: str, where: list[str], fields: list[str]) -> list[dict[str, object]]:
    a = resolve_app(pack, app)
    t = resolve_table(pack, a, table)
    known = _known(pack, a, t)
    conditions: list[tuple[str, str]] = []
    for raw in where:
        if "=" not in raw:
            raise DataError("--where 格式应为 字段=值：{}".format(raw))
        name, value = raw.split("=", 1)
        conditions.append((name.strip(), value.strip()))
    selected = fields or None
    for name in [key for key, _ in conditions] + (selected or []):
        if name not in known:
            raise DataError("字段 {} 不在应用 {} 的表 {} 表头元数据中".format(name, a, t))
    result: list[dict[str, object]] = []
    for record_id, row in _records(pack, a, t).items():
        if all(row.get(name) == value for name, value in conditions):
            picked = {key: row[key] for key in selected if key in row} if selected else dict(row)
            result.append({"record_id": record_id, "fields": picked})
    return result


def _locate_record(rows: dict[str, dict[str, str]], where: list[str], known: set[str]) -> str:
    if not where:
        raise DataError("缺少 --record 和 --where，无法定位记录")
    conditions: list[tuple[str, str]] = []
    for raw in where:
        if "=" not in raw:
            raise DataError("--where 格式应为 字段=值：{}".format(raw))
        name, value = raw.split("=", 1)
        name = name.strip()
        if name not in known:
            raise DataError("字段 {} 不在表头元数据中".format(name))
        conditions.append((name, value.strip()))
    hits = [rid for rid, row in rows.items() if all(row.get(name) == value for name, value in conditions)]
    if not hits:
        raise DataError("未找到匹配记录")
    if len(hits) > 1:
        raise DataError("匹配到 {} 条记录，请补条件或给 --record".format(len(hits)))
    return hits[0]


def mutate(path: str, pack: dict[str, object], app: str, table: str, record: str, sets: list[str], delete: bool, where: list[str]) -> dict[str, object]:
    a = resolve_app(pack, app)
    t = resolve_table(pack, a, table)
    _ensure_writable(a)
    rows = _records(pack, a, t)
    if not record:
        record = _locate_record(rows, where, _known(pack, a, t))
    elif record not in rows:
        raise DataError("应用 {} 的表 {} 中不存在记录：{}。可用记录：{}".format(a, t, record, ", ".join(rows)))

    changes: dict[str, str] = {}
    if not delete:
        known = _known(pack, a, t)
        for raw in sets:
            if "=" not in raw:
                raise DataError("--set 格式应为 字段=值：{}".format(raw))
            name, value = raw.split("=", 1)
            name = name.strip()
            if name not in known:
                raise DataError("字段 {} 不在表头元数据中：{}".format(name, t))
            if name not in rows[record]:
                raise DataError("记录 {} 中没有字段 {}，不可新增字段".format(record, name))
            changes[name] = format_value(value.strip())

    out: list[str] = []
    applied: dict[str, str] = {}
    for s in iter_lines(Path(path).read_text(encoding="utf-8").splitlines()):
        if s.section != "apps" or s.app != a or s.table != t or s.subsection != "records":
            out.append(s.raw)
            continue
        if s.indent == 8 and delete and s.record == record:
            continue
        if s.indent == 10 and s.record == record:
            if delete:
                continue
            if s.key in changes:
                out.append(s.raw[:s.raw.index(":")] + ": " + changes[s.key])
                applied[s.key] = unquote(changes[s.key])
                continue
        out.append(s.raw)

    if not delete:
        for name in changes:
            if name not in applied:
                raise DataError("记录 {} 中字段 {} 未被改写".format(record, name))
    Path(path).write_text("\n".join(out) + "\n", encoding="utf-8")
    return {"app": a, "table": t, "record": record, "deleted": delete, "changed": applied}


def _next_ids(existing: dict[str, dict[str, str]], count: int, prefix: str = "rec") -> list[str]:
    names = list(existing)
    used = {int(m.group(1)) for name in names if (m := re.search(r"(\d+)$", name))}
    number = max(used, default=0)
    result: list[str] = []
    while len(result) < count:
        number += 1
        if number not in used:
            result.append("{}{:03d}".format(prefix, number))
    return result


def _data_insert_position(lines: list[str], app: str, table: str) -> int:
    position: int | None = None
    for s in iter_lines(lines):
        if s.section == "apps" and s.app == app and s.subsection == "records" and s.table == table:
            if s.indent in (6, 8, 10):
                position = s.lineno
    if position is None:
        raise DataError("语义包中没有应用 {} 的表 {}，请先在 records 中登记该表".format(app, table))
    return position


def append(path: str, app: str, table: str, items: list[str], extra_tables: tuple[str, ...] = ()) -> dict[str, object]:
    """向指定应用的表追加记录；字段须在该应用表头元数据中存在，记录 ID 自动生成。"""
    return append_pack(path, load_pack(path, app, (table, *extra_tables)), app, table, items)


def append_pack(path: str, pack: dict[str, object], app: str, table: str, items: list[str]) -> dict[str, object]:
    a = resolve_app(pack, app)
    t = resolve_table(pack, a, table)
    _ensure_writable(a)
    known = _known(pack, a, t)

    rows: list[dict[str, str]] = []
    for raw in items:
        fields: dict[str, str] = {}
        for pair in raw.split("|"):
            if "=" not in pair:
                raise DataError("字段格式应为 字段=值：{}".format(pair))
            name, value = pair.split("=", 1)
            name = name.strip()
            if name not in known:
                raise DataError("字段 {} 不在应用 {} 的表 {} 表头元数据中".format(name, a, t))
            fields[name] = format_value(value.strip())
        rows.append(fields)

    ids = _next_ids(_records(pack, a, t), len(rows))
    rendered: list[str] = []
    for record_id, fields in zip(ids, rows):
        rendered.append("        {}:".format(record_id))
        rendered.extend("          {}: {}".format(name, value) for name, value in fields.items())

    file = Path(path).expanduser().resolve()
    lines = file.read_text(encoding="utf-8").splitlines()
    insert_at = _data_insert_position(lines, a, t)
    lines[insert_at:insert_at] = rendered
    file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"app": a, "table": t, "added": len(rows), "records": ids}


def _print_apps(pack: dict[str, object]) -> None:
    payload = []
    for app, item in cast(dict[str, object], pack["apps"]).items():
        records = cast(dict[str, object], item["records"])
        payload.append({
            "app": app,
            "tables": [
                {"name": name, "records": len(cast(dict[str, object], records.get(name, {})))}
                for name in cast(dict[str, object], item["tables"])
            ],
        })
    print(json.dumps({"apps": payload}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="语义包数据维护（查 / 改 / 删）")
    parser.add_argument("--pack", default=str(DEFAULT_PACK), help="语义包 YAML 路径（表头元数据 + 本地记录）")
    parser.add_argument("--list-apps", action="store_true", help="列出应用及各表记录数")
    parser.add_argument("--list-tables", action="store_true", help="列出表与记录数；带 --app 时只列该应用")
    parser.add_argument("--app", default="", help="应用名")
    parser.add_argument("--table", default="", help="表名")
    parser.add_argument("--record", default="", help="记录 ID；改 / 删不传时用 --where 定位唯一记录")
    parser.add_argument("--where", action="append", default=[], metavar="字段=值", help="过滤条件，可重复，AND；改 / 删不传 --record 时用于定位")
    parser.add_argument("--fields", action="append", nargs="+", default=[], metavar="字段", help="返回字段，可多值 / 重复")
    parser.add_argument("--set", dest="sets", action="append", nargs="+", default=[], metavar="字段=值", help="改字段，可多值 / 重复")
    parser.add_argument("--delete", action="store_true", help="删除指定记录")
    parser.add_argument("--resolve-field", metavar="字段词", help="解析为稳定字段 ID 与当前语种平台字段")
    parser.add_argument("--resolve-table", metavar="表词", help="解析为稳定表 ID 与当前语种平台表")
    args = parser.parse_args()
    fields = [name for group in args.fields for name in group]
    sets = [item for group in args.sets for item in group]

    try:
        pack = load_pack(args.pack, args.app, (args.table,) if args.table else ())
        if args.resolve_table:
            if not args.app:
                raise DataError("--resolve-table 需要 --app")
            a = resolve_app(pack, args.app)
            t = resolve_table(pack, a, args.resolve_table)
            print(json.dumps({"app": a, "table": t, "platform": platform_table(pack, a, t)}, ensure_ascii=False, indent=2))
            return
        if args.resolve_field:
            if not args.app or not args.table:
                raise DataError("--resolve-field 需要 --app 与 --table")
            a = resolve_app(pack, args.app)
            t = resolve_table(pack, a, args.table)
            field = resolve_field(pack, a, t, args.resolve_field)
            print(json.dumps({"app": a, "table": t, "field": field,
                              "platform": platform_field(pack, a, t, field)}, ensure_ascii=False, indent=2))
            return
        if args.list_apps:
            if args.app or args.table or args.where or fields or sets or args.delete:
                raise DataError("--list-apps 不能与其它操作参数同时使用")
            _print_apps(pack)
            return
        if args.list_tables:
            if args.table or args.where or fields or sets or args.delete:
                raise DataError("--list-tables 不能与表/记录操作参数同时使用")
            if args.app:
                app = resolve_app(pack, args.app)
                apps = {app: cast(dict[str, object], cast(dict[str, object], pack["apps"])[app])}
            else:
                apps = cast(dict[str, object], pack["apps"])
            payload = [
                {"app": app, "tables": [
                    {"name": name, "records": len(cast(dict[str, object], cast(dict[str, object], item["records"]).get(name, {})))}
                    for name in cast(dict[str, object], item["tables"])
                ]}
                for app, item in apps.items()
            ]
            print(json.dumps({"apps": payload}, ensure_ascii=False, indent=2))
            return
        if args.delete and sets:
            raise DataError("--delete 与 --set 互斥，不能同时使用")
        if not args.app:
            raise DataError("需要 --app 指定应用（可用 --list-apps 查看）")
        if not args.table:
            raise DataError("需要 --table 指定该应用下的表")
        if args.delete or sets:
            result = mutate(args.pack, pack, args.app, args.table, args.record, sets, args.delete, args.where)
        else:
            a = resolve_app(pack, args.app)
            records = query(pack, a, args.table, args.where, fields)
            result = {"app": a, "table": args.table, "count": len(records), "records": records}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (DataError, OSError) as err:
        print("参数错误：{}".format(err), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
