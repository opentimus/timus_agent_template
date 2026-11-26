#!/usr/bin/env python3
"""本地基础数据维护：查 / 改 / 删 / 追加，原地改写受限 YAML。纯标准库。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterator, NamedTuple, cast

SKILLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILLS / "timus-app-schema" / "scripts"))

from schema_lib import clean_line, list_fields, load_schema, split_pair, unquote, SchemaError  # pyright: ignore[reportImplicitRelativeImport]

DEFAULT_DATA = SKILLS / "timus-app-schema" / "references" / "timus-team-data.yaml"
DEFAULT_SCHEMA = SKILLS / "timus-app-schema" / "references" / "timus-team-schema.yaml"


class DataError(Exception):
    """基础数据格式或参数不合法。"""


Rows = dict[str, dict[str, dict[str, str]]]


class LineState(NamedTuple):
    lineno: int
    raw: str
    indent: int
    key: str
    value: str
    section: str
    table: str
    record: str


def walk(lines: list[str]) -> Iterator[LineState]:
    """逐行产出缩进状态；section ∈ {meta, data, skip}，空白行不产出。"""
    section = table = record = ""
    for lineno, raw in enumerate(lines, start=1):
        line = clean_line(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, value = split_pair(line.strip(), lineno)
        if indent == 0:
            section = "data" if key == "data" else ("meta" if value else "skip")
            table = record = ""
        elif section == "data":
            if indent == 2:
                table, record = key, ""
            elif indent == 4:
                record = key
        yield LineState(lineno, raw, indent, key, value, section, table, record)


def load_data(path: str) -> dict[str, object]:
    """只读 meta 与 data 段；source / members 等其它顶层块整块忽略。"""
    file = Path(path).expanduser().resolve()
    if not file.is_file():
        raise DataError("找不到基础数据：{}".format(file))
    meta: dict[str, str] = {}
    data: Rows = {}
    for s in walk(file.read_text(encoding="utf-8").splitlines()):
        if s.section == "meta":
            meta[s.key] = s.value
        elif s.section == "data" and s.indent > 0:
            if s.indent == 2:
                if s.value:
                    raise DataError("第 {} 行表名不应带值：{}".format(s.lineno, s.key))
                if s.key in data:
                    raise DataError("第 {} 行重复表：{}".format(s.lineno, s.key))
                data[s.key] = {}
            elif s.indent == 4:
                if not s.table or s.value:
                    raise DataError("第 {} 行记录格式错误：{}".format(s.lineno, s.key))
                if s.key in data[s.table]:
                    raise DataError("第 {} 行重复记录：{}".format(s.lineno, s.key))
                data[s.table][s.key] = {}
            elif s.indent == 6:
                if not s.record:
                    raise DataError("第 {} 行字段没有所属记录：{}".format(s.lineno, s.key))
                if not s.value:
                    raise DataError("第 {} 行字段缺少值：{}".format(s.lineno, s.key))
                if s.key in data[s.table][s.record]:
                    raise DataError("第 {} 行重复字段：{}".format(s.lineno, s.key))
                data[s.table][s.record][s.key] = s.value
            else:
                raise DataError("第 {} 行缩进须为 2/4/6 空格".format(s.lineno))
    if not meta.get("team_code"):
        raise DataError("基础数据缺少 team_code")
    return {"meta": meta, "data": data}


def known_fields(schema_path: str, table: str) -> set[str]:
    try:
        schema = load_schema(schema_path)
    except SchemaError as err:
        raise DataError(str(err)) from err
    if table not in schema["tables"]:
        raise DataError("表头元数据中不存在表：{}".format(table))
    return {cast(str, item["name"]) for item in list_fields(schema, table)}


def format_value(new_value: str) -> str:
    if "#" in new_value or '"' in new_value or "'" in new_value:
        raise DataError("值不能包含 # 或引号：{}".format(new_value))
    return '"{}"'.format(new_value)


def query(dataset: dict[str, object], table: str, where: list[str], fields: list[str], schema_path: str) -> list[dict[str, object]]:
    data = cast(Rows, dataset["data"])
    if table not in data:
        raise DataError("未知表 {}。可用表：{}".format(table, ", ".join(data)))
    known = known_fields(schema_path, table)
    conditions: list[tuple[str, str]] = []
    for raw in where:
        if "=" not in raw:
            raise DataError("--where 格式应为 字段=值：{}".format(raw))
        name, value = raw.split("=", 1)
        conditions.append((name.strip(), value.strip()))
    selected = fields or None
    for name in [key for key, _ in conditions] + (selected or []):
        if name not in known:
            raise DataError("字段 {} 不在表头元数据中：{}".format(name, table))
    result: list[dict[str, object]] = []
    for record_id, row in data[table].items():
        if all(row.get(name) == value for name, value in conditions):
            picked = {key: row[key] for key in selected if key in row} if selected else dict(row)
            result.append({"record_id": record_id, "fields": picked})
    return result


def mutate(path: str, table: str, record: str, sets: list[str], delete: bool, schema_path: str) -> dict[str, object]:
    file = Path(path).expanduser().resolve()
    dataset = load_data(str(file))
    data = cast(Rows, dataset["data"])
    if table not in data:
        raise DataError("未知表：{}。可用表：{}".format(table, ", ".join(data)))
    if record not in data[table]:
        raise DataError("表 {} 中不存在记录：{}。可用记录：{}".format(table, record, ", ".join(data[table])))

    changes: dict[str, str] = {}
    if not delete:
        known = known_fields(schema_path, table)
        for raw in sets:
            if "=" not in raw:
                raise DataError("--set 格式应为 字段=值：{}".format(raw))
            name, value = raw.split("=", 1)
            name = name.strip()
            if name not in known:
                raise DataError("字段 {} 不在表头元数据中：{}".format(name, table))
            if name not in data[table][record]:
                raise DataError("记录 {} 中没有字段 {}，不可新增字段".format(record, name))
            changes[name] = format_value(value.strip())

    lines = file.read_text(encoding="utf-8").splitlines()
    states = {s.lineno: s for s in walk(lines)}
    out: list[str] = []
    applied: dict[str, str] = {}
    for lineno, raw in enumerate(lines, start=1):
        s = states.get(lineno)
        if not s or s.section != "data" or s.indent <= 0:
            out.append(raw)
            continue
        if s.indent == 4 and delete and s.table == table and s.record == record:
            continue
        if s.indent == 6 and s.table == table and s.record == record:
            if delete:
                continue
            if s.key in changes:
                out.append(raw[:raw.index(":")] + ": " + changes[s.key])
                applied[s.key] = unquote(changes[s.key])
                continue
        out.append(raw)

    if not delete:
        for name in changes:
            if name not in applied:
                raise DataError("记录 {} 中字段 {} 未被改写".format(record, name))
    file.write_text("\n".join(out) + "\n", encoding="utf-8")
    return {"team_code": dataset["meta"]["team_code"], "table": table, "record": record,
            "deleted": delete, "changed": applied}


def _next_ids(existing: Rows, table: str, count: int, prefix: str = "rec") -> list[str]:
    """按已有记录的最大序号续编；新表用 prefix 作前缀。"""
    names = list(existing.get(table, {}))
    used = {int(m.group(1)) for name in names if (m := re.search(r"(\d+)$", name))}
    number = max(used, default=0)
    result: list[str] = []
    while len(result) < count:
        number += 1
        if number not in used:
            result.append("{}{:03d}".format(prefix, number))
    return result


def _data_insert_position(lines: list[str], table: str) -> tuple[int, bool]:
    """返回 (插入行号, 表是否已存在)；无 data 段时返回文件末尾。"""
    data_end: int | None = None
    insert_at: int | None = None
    seen_data = False
    for s in walk(lines):
        if s.section == "data":
            seen_data = True
            if s.indent == 0:
                continue
            data_end = s.lineno  # 1 基行号即该行之后的插入下标
            if s.indent == 2 and s.key == table:
                insert_at = s.lineno
            elif insert_at is not None and s.indent in (4, 6) and s.table == table:
                insert_at = s.lineno
        elif seen_data and data_end is None:
            data_end = s.lineno - 1
    if insert_at is not None:
        return insert_at, True
    return (data_end if data_end is not None else len(lines)), False


def append(path: str, schema: str, table: str, items: list[str]) -> dict[str, object]:
    """按表追加记录；字段须在表头元数据中存在，记录 ID 自动生成。"""
    file = Path(path).expanduser().resolve()
    dataset = load_data(str(file))
    data = cast(Rows, dataset["data"])
    known = known_fields(schema, table)

    rows: list[dict[str, str]] = []
    for raw in items:
        if "=" not in raw:
            raise DataError("--set 格式应为 字段=值：{}".format(raw))
        fields: dict[str, str] = {}
        for pair in raw.split("|"):
            if "=" not in pair:
                raise DataError("字段格式应为 字段=值：{}".format(pair))
            name, value = pair.split("=", 1)
            name = name.strip()
            if name not in known:
                raise DataError("字段 {} 不在表头元数据中：{}".format(name, table))
            fields[name] = format_value(value.strip())
        rows.append(fields)

    ids = _next_ids(data, table, len(rows))
    rendered: list[str] = []
    for record_id, fields in zip(ids, rows):
        rendered.append("    {}:".format(record_id))
        rendered.extend("      {}: {}".format(name, value) for name, value in fields.items())

    lines = file.read_text(encoding="utf-8").splitlines()
    position, exists = _data_insert_position(lines, table)
    has_data = any(clean_line(line).strip() == "data:" for line in lines)
    block = rendered if exists else ["  {}:".format(table)] + rendered
    if not has_data:
        block = ["", "data:"] + block
        position = len(lines)
    lines[position:position] = block
    file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"team_code": dataset["meta"]["team_code"], "table": table, "added": len(rows), "records": ids}


def main() -> None:
    parser = argparse.ArgumentParser(description="本地基础数据维护（查 / 改 / 删）")
    parser.add_argument("--data", default=str(DEFAULT_DATA), help="基础数据 YAML 路径")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA), help="表头元数据路径（字段校验）")
    parser.add_argument("--list-tables", action="store_true", help="列出本地表与记录数")
    parser.add_argument("--table", default="", help="表名")
    parser.add_argument("--record", default="", help="记录 ID（改 / 删必填）")
    parser.add_argument("--where", action="append", default=[], metavar="字段=值", help="过滤条件，可重复，AND")
    parser.add_argument("--fields", action="append", nargs="+", default=[], metavar="字段", help="返回字段，可多值 / 重复")
    parser.add_argument("--set", dest="sets", action="append", nargs="+", default=[], metavar="字段=值", help="改字段，可多值 / 重复")
    parser.add_argument("--delete", action="store_true", help="删除指定记录")
    args = parser.parse_args()
    fields = [name for group in args.fields for name in group]
    sets = [item for group in args.sets for item in group]

    try:
        if args.delete and sets:
            raise DataError("--delete 与 --set 互斥，不能同时使用")
        if args.list_tables and (args.table or args.where or fields or sets or args.delete):
            raise DataError("--list-tables 不能与其它操作参数同时使用")
        dataset = load_data(args.data)
        meta = cast(dict[str, str], dataset["meta"])
        if args.list_tables:
            data = cast(Rows, dataset["data"])
            tables = [{"name": name, "records": len(rows)} for name, rows in data.items()]
            print(json.dumps({"team_code": meta["team_code"], "tables": tables}, ensure_ascii=False, indent=2))
            return
        if not args.table:
            raise DataError("需要 --table 或 --list-tables")
        if args.delete or sets:
            if not args.record:
                raise DataError("改 / 删需要 --record 指定记录 ID")
            result = mutate(args.data, args.table, args.record, sets, args.delete, args.schema)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        records = query(dataset, args.table, args.where, fields, args.schema)
        print(json.dumps(
            {"team_code": meta["team_code"], "table": args.table, "count": len(records), "records": records},
            ensure_ascii=False, indent=2,
        ))
    except (DataError, OSError) as err:
        print("参数错误：{}".format(err), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
