#!/usr/bin/env python3
"""本地基础数据维护：查 / 改 / 删，原地改写受限 YAML。纯标准库。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, NamedTuple, cast

SKILLS = Path(__file__).resolve().parents[2]
SCHEMA_SCRIPTS = SKILLS / "timus-app-schema" / "scripts"
sys.path.insert(0, str(SCHEMA_SCRIPTS))

import schema_lib  # pyright: ignore[reportImplicitRelativeImport]

DEFAULT_DATA = SKILLS / "timus-app-schema" / "references" / "timus-team-data.yaml"
DEFAULT_SCHEMA = SKILLS / "timus-app-schema" / "references" / "timus-team-schema.yaml"


class DataError(Exception):
    """基础数据格式或参数不合法。"""


# 复用 schema_lib 的受限 YAML 解析辅助函数，避免两处实现漂移。
_clean_line = cast(Callable[[str], str], schema_lib._clean_line)
_unquote = cast(Callable[[str], str], schema_lib._unquote)
_split_pair = cast(Callable[[str, int], tuple[str, str]], schema_lib._split_pair)


def load_data(path: str) -> dict[str, object]:
    file = Path(path).expanduser().resolve()
    if not file.is_file():
        raise DataError("找不到基础数据：{}".format(file))
    meta: dict[str, str] = {}
    source: dict[str, str] = {}
    members: list[dict[str, str]] = []
    data: dict[str, dict[str, dict[str, str]]] = {}
    section = table = record = ""
    for lineno, raw in enumerate(file.read_text(encoding="utf-8").splitlines(), start=1):
        line = _clean_line(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        text = line.strip()
        if indent == 0:
            key, value = _split_pair(text, lineno)
            section = key if key in ("source", "members", "data") else ""
            if not section:
                if key in meta:
                    raise DataError("第 {} 行重复键：{}".format(lineno, key))
                meta[key] = value
            elif value:
                raise DataError("第 {} 行 {} 块不应带值".format(lineno, key))
            table = record = ""
            continue
        if section == "source":
            if indent != 2:
                raise DataError("第 {} 行 source 缩进须为 2 空格".format(lineno))
            key, value = _split_pair(text, lineno)
            source[key] = value
            continue
        if section == "members":
            if indent not in (2, 4):
                raise DataError("第 {} 行 members 缩进须为 2/4 空格".format(lineno))
            if indent == 2:
                if not text.startswith("- "):
                    raise DataError("第 {} 行成员须以 `- ` 开头：{}".format(lineno, text))
                members.append({})
            key, value = _split_pair(text[2:] if indent == 2 else text, lineno)
            if not members:
                raise DataError("第 {} 行字段没有所属成员".format(lineno))
            members[-1][key] = value
            continue
        if section != "data":
            raise DataError("第 {} 行缩进内容不属于已知块：{}".format(lineno, text))
        key, value = _split_pair(text, lineno)
        if indent == 2:
            if value:
                raise DataError("第 {} 行表名不应带值：{}".format(lineno, key))
            if key in data:
                raise DataError("第 {} 行重复表：{}".format(lineno, key))
            data[key] = {}
            table, record = key, ""
        elif indent == 4:
            if not table or value:
                raise DataError("第 {} 行记录格式错误：{}".format(lineno, key))
            if key in data[table]:
                raise DataError("第 {} 行重复记录：{}".format(lineno, key))
            data[table][key] = {}
            record = key
        elif indent == 6:
            if not record:
                raise DataError("第 {} 行字段没有所属记录：{}".format(lineno, key))
            if not value:
                raise DataError("第 {} 行字段缺少值：{}".format(lineno, key))
            if key in data[table][record]:
                raise DataError("第 {} 行重复字段：{}".format(lineno, key))
            data[table][record][key] = value
        else:
            raise DataError("第 {} 行缩进须为 2/4/6 空格".format(lineno))
    if not meta.get("team_code") or not members:
        raise DataError("基础数据缺少 team_code 或 members 块")
    for name, records in data.items():
        if not records:
            raise DataError("表 {} 无记录".format(name))
    for index, member in enumerate(members, start=1):
        for key in ("member_id", "member", "role", "open_id", "record_id"):
            if not member.get(key):
                raise DataError("第 {} 个成员缺少 {}（下划线命名）".format(index, key))
    return {"meta": meta, "source": source, "members": members, "data": data}


def _known_fields(schema_path: str, table: str) -> set[str]:
    schema = schema_lib.load_schema(schema_path)
    if table not in schema["tables"]:
        raise DataError("表头元数据中不存在表：{}".format(table))
    return {cast(str, item["name"]) for item in schema_lib.list_fields(schema, table)}


def query(dataset: dict[str, object], table: str, where: list[str], fields: list[str], schema_path: str) -> list[dict[str, object]]:
    data = cast(dict[str, dict[str, dict[str, str]]], dataset["data"])
    if table not in data:
        raise DataError("未知表 {}。可用表：{}".format(table, ", ".join(data)))
    known = _known_fields(schema_path, table)
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


def _format_value(new_value: str) -> str:
    if "#" in new_value or '"' in new_value or "'" in new_value:
        raise DataError("值不能包含 # 或引号：{}".format(new_value))
    return '"{}"'.format(new_value)


def mutate(path: str, table: str, record: str, sets: list[str], delete: bool, schema_path: str) -> dict[str, object]:
    file = Path(path).expanduser().resolve()
    dataset = load_data(str(file))
    data = cast(dict[str, dict[str, dict[str, str]]], dataset["data"])
    if table not in data:
        raise DataError("未知表：{}。可用表：{}".format(table, ", ".join(data)))
    if record not in data[table]:
        raise DataError("表 {} 中不存在记录：{}。可用记录：{}".format(table, record, ", ".join(data[table])))

    changes: dict[str, str] = {}
    if not delete:
        known = _known_fields(schema_path, table)
        for raw in sets:
            if "=" not in raw:
                raise DataError("--set 格式应为 字段=值：{}".format(raw))
            name, value = raw.split("=", 1)
            name = name.strip()
            if name not in known:
                raise DataError("字段 {} 不在表头元数据中：{}".format(name, table))
            if name not in data[table][record]:
                raise DataError("记录 {} 中没有字段 {}，不可新增字段".format(record, name))
            changes[name] = _format_value(value.strip())

    original = file.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    section = current_table = current_record = ""
    applied: dict[str, str] = {}
    for lineno, raw in enumerate(original, start=1):
        line = _clean_line(raw)
        if not line.strip():
            out.append(raw)
            continue
        indent = len(line) - len(line.lstrip(" "))
        text = line.strip()
        if indent == 0:
            key, _ = _split_pair(text, lineno)
            section = "data" if key == "data" else ""
            current_table = current_record = ""
            out.append(raw)
            continue
        if section != "data":
            out.append(raw)
            continue
        key, _ = _split_pair(text, lineno)
        if indent == 2:
            current_table, current_record = key, ""
            out.append(raw)
            continue
        if indent == 4:
            current_record = key
            if delete and current_table == table and key == record:
                continue
            out.append(raw)
            continue
        if indent == 6:
            if current_table == table and current_record == record:
                if delete:
                    continue
                if key in changes:
                    out.append(raw[:raw.index(":")] + ": " + changes[key])
                    applied[key] = _unquote(changes[key])
                    continue
            out.append(raw)
            continue
        out.append(raw)

    if not delete:
        for name in changes:
            if name not in applied:
                raise DataError("记录 {} 中字段 {} 未被改写".format(record, name))
    file.write_text("\n".join(out) + "\n", encoding="utf-8")
    return {"team_code": dataset["meta"]["team_code"], "table": table, "record": record,
            "deleted": delete, "changed": applied}


class Args(NamedTuple):
    data: str
    schema: str
    list_tables: bool
    table: str
    record: str
    where: list[str]
    fields: list[str]
    sets: list[str]
    delete: bool


def parse_args() -> Args:
    parser = argparse.ArgumentParser(description="本地基础数据维护（查 / 改 / 删）")
    _ = parser.add_argument("--data", default=str(DEFAULT_DATA), help="基础数据 YAML 路径")
    _ = parser.add_argument("--schema", default=str(DEFAULT_SCHEMA), help="表头元数据路径（字段校验）")
    _ = parser.add_argument("--list-tables", action="store_true", help="列出本地表与记录数")
    _ = parser.add_argument("--table", default="", help="表名")
    _ = parser.add_argument("--record", default="", help="记录 ID（改 / 删必填）")
    _ = parser.add_argument("--where", action="append", default=[], metavar="字段=值", help="过滤条件，可重复，AND")
    _ = parser.add_argument("--fields", action="append", nargs="+", default=[], metavar="字段", help="返回字段，可多值 / 重复")
    _ = parser.add_argument("--set", dest="sets", action="append", nargs="+", default=[], metavar="字段=值", help="改字段，可多值 / 重复")
    _ = parser.add_argument("--delete", action="store_true", help="删除指定记录")
    raw = parser.parse_args()
    return Args(
        data=cast(str, raw.data),
        schema=cast(str, raw.schema),
        list_tables=cast(bool, raw.list_tables),
        table=cast(str, raw.table),
        record=cast(str, raw.record),
        where=cast(list[str], raw.where),
        fields=[name for group in cast(list[list[str]], raw.fields) for name in group],
        sets=[item for group in cast(list[list[str]], raw.sets) for item in group],
        delete=cast(bool, raw.delete),
    )


def main() -> None:
    args = parse_args()
    try:
        if args.delete and args.sets:
            raise DataError("--delete 与 --set 互斥，不能同时使用")
        if args.list_tables and (args.table or args.where or args.fields or args.sets or args.delete):
            raise DataError("--list-tables 不能与其它操作参数同时使用")
        dataset = load_data(args.data)
        meta = cast(dict[str, str], dataset["meta"])
        if args.list_tables:
            data = cast(dict[str, dict[str, dict[str, str]]], dataset["data"])
            tables = [{"name": name, "records": len(rows)} for name, rows in data.items()]
            print(json.dumps({"team_code": meta["team_code"], "tables": tables}, ensure_ascii=False, indent=2))
            return
        if not args.table:
            raise DataError("需要 --table 或 --list-tables")
        if args.delete or args.sets:
            if not args.record:
                raise DataError("改 / 删需要 --record 指定记录 ID")
            result = mutate(args.data, args.table, args.record, args.sets, args.delete, args.schema)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        records = query(dataset, args.table, args.where, args.fields, args.schema)
        print(json.dumps(
            {"team_code": meta["team_code"], "table": args.table, "count": len(records), "records": records},
            ensure_ascii=False, indent=2,
        ))
    except (DataError, schema_lib.SchemaError, OSError) as err:
        print("参数错误：{}".format(err), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
