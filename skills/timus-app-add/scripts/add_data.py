#!/usr/bin/env python3
"""基础数据批量添加：本地命中取值，按表追加记录。纯标准库。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import cast

SKILLS = Path(__file__).resolve().parents[2]
MAINT_SCRIPTS = SKILLS / "timus-app-maintenance" / "scripts"
SCHEMA_SCRIPTS = SKILLS / "timus-app-schema" / "scripts"
sys.path.insert(0, str(MAINT_SCRIPTS))
sys.path.insert(0, str(SCHEMA_SCRIPTS))

import data_tool  # pyright: ignore[reportImplicitRelativeImport]
import schema_lib  # pyright: ignore[reportImplicitRelativeImport]

DEFAULT_DATA = SKILLS / "timus-app-schema" / "references" / "timus-team-data.yaml"
DEFAULT_SCHEMA = SKILLS / "timus-app-schema" / "references" / "timus-team-schema.yaml"


def _next_ids(existing: dict[str, dict[str, str]], count: int) -> list[str]:
    if existing:
        names = list(existing)
        match = re.match(r"^(.*?)(\d+)$", names[0])
        prefix, start = (match.group(1), int(match.group(2))) if match else (names[0] + "-", 0)
        used = {int(m.group(1)) for name in names if (m := re.search(r"(\d+)$", name))}
    else:
        prefix, start, used = "record", 0, set()
    result = []
    number = start
    while len(result) < count:
        number += 1
        if number not in used:
            result.append("{}{:03d}".format(prefix, number))
    return result


def add(path: str, schema: str, table: str, items: list[str]) -> dict[str, object]:
    file = Path(path).expanduser().resolve()
    dataset = data_tool.load_data(str(file))
    data = cast(dict[str, dict[str, dict[str, str]]], dataset["data"])
    if table not in data:
        raise data_tool.DataError("未知表：{}。可用表：{}".format(table, ", ".join(data)))
    known = data_tool._known_fields(schema, table)

    rows: list[dict[str, str]] = []
    for raw in items:
        if "=" not in raw:
            raise data_tool.DataError("--set 格式应为 字段=值：{}".format(raw))
        fields: dict[str, str] = {}
        for pair in raw.split("|"):
            if "=" not in pair:
                raise data_tool.DataError("字段格式应为 字段=值：{}".format(pair))
            name, value = pair.split("=", 1)
            name = name.strip()
            if name not in known:
                raise data_tool.DataError("字段 {} 不在表头元数据中：{}".format(name, table))
            fields[name] = data_tool._format_value(value.strip())
        rows.append(fields)

    ids = _next_ids(data[table], len(rows))
    rendered: list[str] = []
    for record_id, fields in zip(ids, rows):
        rendered.append("    {}:".format(record_id))
        rendered.extend("      {}: {}".format(name, value) for name, value in fields.items())

    lines = file.read_text(encoding="utf-8").splitlines()
    section = current_table = ""
    insert_at = None
    for lineno, raw in enumerate(lines):
        line = data_tool._clean_line(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        text = line.strip()
        if indent == 0:
            key, _ = data_tool._split_pair(text, lineno + 1)
            section = "data" if key == "data" else ""
            current_table = ""
        elif section == "data" and indent == 2:
            key, _ = data_tool._split_pair(text, lineno + 1)
            current_table = key
        if section == "data" and current_table == table and indent in (4, 6):
            insert_at = lineno
    if insert_at is None:
        raise data_tool.DataError("表 {} 无记录块，无法追加".format(table))
    lines[insert_at + 1:insert_at + 1] = rendered
    file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"team_code": dataset["meta"]["team_code"], "table": table, "added": len(rows), "records": ids}


def main() -> None:
    parser = argparse.ArgumentParser(description="批量添加本地基础数据")
    parser.add_argument("--data", default=str(DEFAULT_DATA), help="基础数据 YAML 路径")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA), help="表头元数据路径（字段校验）")
    parser.add_argument("--table", required=True, help="目标表")
    parser.add_argument("--set", dest="items", action="append", required=True,
                        metavar="字段=值|字段=值", help="一条记录；可重复多条")
    args = parser.parse_args()
    try:
        result = add(cast(str, args.data), cast(str, args.schema), cast(str, args.table),
                     cast(list[str], args.items))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (data_tool.DataError, schema_lib.SchemaError, OSError) as err:
        print("参数错误：{}".format(err), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
