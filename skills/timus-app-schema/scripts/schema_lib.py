"""Timus 语义包解析（Python 3 标准库，零第三方依赖）。

仅支持 references/timus-team-schema.yaml 使用的受限 YAML 子集：
顶层键、2 空格缩进的键值、4 空格缩进的字段键值；不支持列表语法与锚点。

_parse 辅助函数同时供同目录 data_tool.py / add_data.py 复用。
"""
from __future__ import annotations

from pathlib import Path

SECTION_KEYS = ("type_policy", "tables", "fields")
VALID_POLICIES = ("read_only", "writable")


class SchemaError(Exception):
    """语义包格式不合法。"""


def _clean_line(raw: str) -> str:
    quote = ""
    for index, char in enumerate(raw):
        if quote:
            if char == quote:
                quote = ""
        elif char in ("'", '"'):
            quote = char
        elif char == "#" and (index == 0 or raw[index - 1].isspace()):
            return raw[:index].rstrip()
    return raw.rstrip()


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("\"", "'"):
        return value[1:-1]
    return value


def _split_pair(line: str, lineno: int) -> tuple[str, str]:
    if ":" not in line:
        raise SchemaError("第 {} 行缺少冒号：{}".format(lineno, line))
    key, _, value = line.partition(":")
    key = _unquote(key.strip())
    if not key:
        raise SchemaError("第 {} 行的键为空".format(lineno))
    return key, _unquote(value)


def _put(mapping: dict[str, str], key: str, value: str, lineno: int) -> None:
    if key in mapping:
        raise SchemaError("第 {} 行出现重复键：{}".format(lineno, key))
    mapping[key] = value


def load_schema(path: str) -> dict[str, object]:
    """读取并校验语义包，返回 meta / type_policy / tables / fields 四部分。"""
    file = Path(path).expanduser().resolve()
    if not file.is_file():
        raise SchemaError("找不到语义包文件：{}".format(file))

    meta: dict[str, str] = {}
    type_policy: dict[str, str] = {}
    tables: dict[str, str] = {}
    fields: dict[str, dict[str, str]] = {}
    section = ""
    current_table = ""

    for lineno, raw in enumerate(file.read_text(encoding="utf-8").splitlines(), start=1):
        line = _clean_line(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        text = line.strip()

        if indent == 0:
            key, value = _split_pair(text, lineno)
            if key in SECTION_KEYS:
                if value:
                    raise SchemaError("第 {} 行的块 {} 不应带值".format(lineno, key))
                section = key
                current_table = ""
            else:
                section = ""
                current_table = ""
                _put(meta, key, value, lineno)
            continue

        if not section:
            raise SchemaError("第 {} 行缩进内容没有所属块：{}".format(lineno, text))

        key, value = _split_pair(text, lineno)

        if section == "type_policy":
            if indent != 2:
                raise SchemaError("第 {} 行 type_policy 需 2 空格缩进".format(lineno))
            if value not in VALID_POLICIES:
                raise SchemaError("第 {} 行类型 {} 的策略必须是 read_only 或 writable".format(lineno, key))
            _put(type_policy, key, value, lineno)
        elif section == "tables":
            if indent != 2:
                raise SchemaError("第 {} 行 tables 需 2 空格缩进".format(lineno))
            if not value:
                raise SchemaError("第 {} 行表单 {} 缺少表单标识".format(lineno, key))
            _put(tables, key, value, lineno)
        elif section == "fields":
            if indent == 2:
                if value:
                    raise SchemaError("第 {} 行表单名 {} 不应带值".format(lineno, key))
                if key in fields:
                    raise SchemaError("第 {} 行出现重复表单：{}".format(lineno, key))
                fields[key] = {}
                current_table = key
            elif indent == 4:
                if not current_table:
                    raise SchemaError("第 {} 行字段 {} 没有所属表单".format(lineno, key))
                if not value:
                    raise SchemaError("第 {} 行字段 {} 缺少类型".format(lineno, key))
                _put(fields[current_table], key, value, lineno)
            else:
                raise SchemaError("第 {} 行 fields 缩进必须为 2 或 4 空格".format(lineno))
        else:
            raise SchemaError("第 {} 行属于未知块：{}".format(lineno, section))

    for key in ("schema_version", "team_code", "connector"):
        if not meta.get(key):
            raise SchemaError("语义包缺少顶层键：{}".format(key))
    if not type_policy or not tables or not fields:
        raise SchemaError("语义包必须同时包含 type_policy、tables 与 fields")
    if set(tables) != set(fields):
        raise SchemaError("tables 与 fields 中的表单名不一致")
    for table, table_fields in fields.items():
        if not table_fields:
            raise SchemaError("表单 {} 没有任何字段".format(table))
        for name, field_type in table_fields.items():
            if field_type not in type_policy:
                raise SchemaError("表单 {} 的字段 {} 类型 {} 未在 type_policy 中声明".format(table, name, field_type))

    return {"meta": meta, "type_policy": type_policy, "tables": tables, "fields": fields}


def list_fields(schema: dict[str, object], table: str) -> list[dict[str, object]]:
    tables = schema["tables"]
    if not isinstance(tables, dict) or table not in tables:
        raise SchemaError("未知表单：{}。可用表单：{}".format(table or "(空)", ", ".join(tables)))
    fields = schema["fields"]
    policy = schema["type_policy"]
    if not isinstance(fields, dict) or not isinstance(policy, dict):
        raise SchemaError("语义包结构不完整")
    return [
        {"name": name, "type": field_type, "writable": policy.get(field_type) == "writable"}
        for name, field_type in fields[table].items()
    ]
