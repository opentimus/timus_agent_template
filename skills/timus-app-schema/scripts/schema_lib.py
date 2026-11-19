"""Timus SPMP 语义包解析与参数校验（Python 3 标准库，零第三方依赖）。

仅支持 references/timus-team-schema.yaml 使用的受限 YAML 子集：
顶层键、2 空格缩进的键值、4 空格缩进的字段键值；不支持列表语法与锚点。

分层约定（两包共用同一份代码，禁止各自改造）：
- 本模块只做「类型层」校验——字段是否存在、是否只读、值的类型是否合法。
- 业务口径（点数必须为正、两位小数、总点拆分、流水号派生、日期换算）
  不在本模块，由同目录 point_util.py 与 date_util.py 负责。
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from pathlib import Path

SECTION_KEYS = ("type_policy", "tables", "fields")
VALID_POLICIES = ("read_only", "writable")
READ_ONLY_HINT = {
    "AutoNumber": "服务端生成",
    "CreatedTime": "服务端生成",
    "Lookup": "关联派生，需先读取记录确认结构",
    "User": "人员字段需特定值结构",
    "Formula": "公式自动计算，无需写入",
}


class SchemaError(Exception):
    """语义包格式或参数不合法。"""


def _clean_line(raw: str) -> str:
    index = raw.find("#")
    if index >= 0:
        raw = raw[:index]
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

    _validate(meta, type_policy, tables, fields)
    return {"meta": meta, "type_policy": type_policy, "tables": tables, "fields": fields}


def _validate(
    meta: dict[str, str],
    type_policy: dict[str, str],
    tables: dict[str, str],
    fields: dict[str, dict[str, str]],
) -> None:
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


def _require_table(schema: dict[str, object], table: str) -> None:
    tables = schema["tables"]
    if not isinstance(tables, dict) or table not in tables:
        available = ", ".join(tables.keys()) if isinstance(tables, dict) else ""
        raise SchemaError("未知表单：{}。可用表单：{}".format(table or "(空)", available))


def list_tables(schema: dict[str, object]) -> list[dict[str, str]]:
    meta = schema["meta"]
    tables = schema["tables"]
    if not isinstance(meta, dict) or not isinstance(tables, dict):
        raise SchemaError("语义包结构不完整")
    return [{"name": name, "table_id": table_id} for name, table_id in tables.items()]


def list_fields(schema: dict[str, object], table: str) -> list[dict[str, object]]:
    _require_table(schema, table)
    fields = schema["fields"]
    policy = schema["type_policy"]
    if not isinstance(fields, dict) or not isinstance(policy, dict):
        raise SchemaError("语义包结构不完整")
    result: list[dict[str, object]] = []
    for name, field_type in fields[table].items():
        result.append(
            {
                "name": name,
                "type": field_type,
                "writable": policy.get(field_type) == "writable",
            }
        )
    return result


def _coerce_value(name: str, field_type: str, raw: object) -> object:
    """类型层取值：只判断「这个值能否作为该类型写入」，不套业务口径。"""
    if not isinstance(raw, str):
        raise SchemaError("字段 {} 的值必须是字符串".format(name))
    if field_type in ("Text", "SingleSelect"):
        return raw
    if field_type == "DateTime":
        # 平台要求完整 YYYY-MM-DD HH:mm:ss；纯日期、T 分隔与服务端不存在的日期一律拒绝。
        # 日期换算请用同目录 date_util.py，其输出即该格式。
        text = raw.strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", text):
            raise SchemaError(
                "字段 {} 是 DateTime，须为完整 YYYY-MM-DD HH:mm:ss（空格分隔，不用纯日期或 T）：{}".format(name, raw)
            )
        try:
            datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise SchemaError("字段 {} 的 DateTime 值不是有效日期时间：{}".format(name, raw))
        return text
    if field_type == "Number":
        text = raw.strip()
        # 数值形态：整数、小数、科学计数法（2 / 2.5 / .5 / -3 / 1e3）。正负与小数位属业务口径，
        # 由 point_util.py 校验，本层不拒绝，避免把业务规则焊死在类型层。
        if not text or not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text):
            raise SchemaError("字段 {} 是 Number，收到的值不是数值：{}".format(name, raw))
        value = float(text)
        if not math.isfinite(value):
            raise SchemaError("字段 {} 的数值超出范围：{}".format(name, raw))
        return int(text) if "." not in text and "e" not in text.lower() else value
    raise SchemaError("字段 {} 的类型 {} 不支持写入".format(name, field_type))


def build_arguments(
    schema: dict[str, object], table: str, sets: list[tuple[str, str]]
) -> dict[str, object]:
    """生成 apaas_add_record 的 arguments，并在校验失败时抛出 SchemaError。"""
    _require_table(schema, table)
    if not sets:
        raise SchemaError("至少需要一个 --set 字段名=值")

    meta = schema["meta"]
    fields = schema["fields"]
    policy = schema["type_policy"]
    if not isinstance(meta, dict) or not isinstance(fields, dict) or not isinstance(policy, dict):
        raise SchemaError("语义包结构不完整")
    table_fields = fields[table]

    seen: set = set()
    result_fields: list[dict[str, object]] = []
    for name, raw in sets:
        if name in seen:
            raise SchemaError("字段 {} 重复设置".format(name))
        seen.add(name)

        if name not in table_fields:
            available = ", ".join(table_fields.keys())
            raise SchemaError(
                "表单 {} 中不存在字段 {}。可用系统字段名：{}。语义包不含业务别名，请勿用别名".format(
                    table, name, available
                )
            )

        field_type = table_fields[name]
        if policy.get(field_type) != "writable":
            reason = READ_ONLY_HINT.get(field_type, "只读类型")
            raise SchemaError(
                "字段 {} 是 {}（{}），不允许写入。请改用可写字段：{}".format(
                    name,
                    field_type,
                    reason,
                    ", ".join(n for n, t in table_fields.items() if policy.get(t) == "writable"),
                )
            )

        result_fields.append({"name": name, "value": _coerce_value(name, field_type, raw)})

    return {"app_name": meta["team_code"], "table_name": table, "fields": result_fields}
