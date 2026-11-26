"""语义包解析：单文件含表头元数据与本地记录；受限 YAML（2 空格缩进，无列表 / 锚点）。"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple, cast

SECTION_KEYS = ("type_policy", "apps")
APP_KEYS = ("tables", "fields", "records")
VALID_POLICIES = ("read_only", "writable")


class PackError(Exception):
    """语义包格式不合法。"""


def clean_line(raw: str) -> str:
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


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("\"", "'"):
        return value[1:-1]
    return value


def split_pair(line: str, lineno: int) -> tuple[str, str]:
    if ":" not in line:
        raise PackError("第 {} 行缺少冒号：{}".format(lineno, line))
    key, _, value = line.partition(":")
    key = unquote(key.strip())
    if not key:
        raise PackError("第 {} 行的键为空".format(lineno))
    return key, unquote(value)


def _put(mapping: dict[str, str], key: str, value: str, lineno: int) -> None:
    if key in mapping:
        raise PackError("第 {} 行出现重复键：{}".format(lineno, key))
    mapping[key] = value


def field_spec(value: str, type_policy: dict[str, str], lineno: int) -> str:
    """字段写作 类型@策略；省略策略时取 type_policy 默认。"""
    parts = value.split("@")
    if len(parts) > 2:
        raise PackError("第 {} 行字段格式应为 类型@策略：{}".format(lineno, value))
    field_type = parts[0].strip()
    if not field_type or field_type not in type_policy:
        raise PackError("第 {} 行字段类型 {} 未在 type_policy 中声明".format(lineno, field_type))
    if len(parts) == 1:
        return "{}@{}".format(field_type, type_policy[field_type])
    policy = parts[1].strip()
    if policy not in VALID_POLICIES:
        raise PackError("第 {} 行字段策略必须是 read_only 或 writable：{}".format(lineno, policy))
    return "{}@{}".format(field_type, policy)


def resolve_name(mapping: dict[str, str], name: str, kind: str) -> str:
    """本地名精确 → 映射值精确 → 唯一子串；失败列候选。"""
    value = (name or "").strip()
    if not value:
        raise PackError("未指定{}".format(kind))
    if value in mapping:
        return value
    exact = [key for key, mapped in mapping.items() if value == mapped and mapped]
    if len(exact) == 1:
        return exact[0]
    hits = [key for key, mapped in mapping.items() if value in key or (mapped and value in mapped)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise PackError("{}「{}」匹配多个：{}。请明确指定".format(kind, value, "、".join(hits)))
    raise PackError("未知{}「{}」。可用：{}".format(kind, value, "、".join(mapping) or "(空)"))


class LineState(NamedTuple):
    lineno: int
    raw: str
    indent: int
    key: str
    value: str
    section: str
    app: str
    subsection: str
    table: str
    record: str


def iter_lines(lines: list[str]) -> Iterator[LineState]:
    """逐行产出缩进状态；section ∈ {meta, type_policy, apps}，空行与注释 section 为空。"""
    section = app = subsection = table = record = ""
    for lineno, raw in enumerate(lines, start=1):
        line = clean_line(raw)
        if not line.strip():
            yield LineState(lineno, raw, -1, "", "", "", "", "", "", "")
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, value = split_pair(line.strip(), lineno)
        if indent == 0:
            section = key if key in SECTION_KEYS else "meta"
            app = subsection = table = record = ""
        elif section == "apps":
            if indent == 2:
                app, subsection, table, record = key, "", "", ""
            elif indent == 4:
                subsection = key if key in APP_KEYS else ""
                table = record = ""
            elif subsection in ("tables", "fields", "records"):
                if indent == 6:
                    table, record = key, ""
                elif indent == 8 and subsection == "records":
                    record = key
        yield LineState(lineno, raw, indent, key, value, section, app, subsection, table, record)


def load_pack(path: str) -> dict[str, object]:
    """读取并校验单文件语义包，返回 meta / type_policy / apps。"""
    file = Path(path).expanduser().resolve()
    if not file.is_file():
        raise PackError("找不到语义包文件：{}".format(file))
    meta: dict[str, str] = {}
    type_policy: dict[str, str] = {}
    apps: dict[str, dict[str, object]] = {}
    for s in iter_lines(file.read_text(encoding="utf-8").splitlines()):
        if s.section == "meta":
            if s.indent == 0:
                _put(meta, s.key, s.value, s.lineno)
        elif s.section == "type_policy":
            if s.indent == 2:
                if s.value not in VALID_POLICIES:
                    raise PackError("第 {} 行类型 {} 的策略必须是 read_only 或 writable".format(s.lineno, s.key))
                _put(type_policy, s.key, s.value, s.lineno)
        elif s.section == "apps":
            item: dict[str, object]
            if s.indent == 2:
                if s.value:
                    raise PackError("第 {} 行应用名 {} 不应带值".format(s.lineno, s.key))
                if s.key in apps:
                    raise PackError("第 {} 行重复应用：{}".format(s.lineno, s.key))
                apps[s.key] = {"tables": {}, "fields": {}, "records": {}}
            elif s.indent == 6 and s.subsection in ("tables", "fields", "records"):
                item = apps[s.app]
                container = cast_dict(item[s.subsection])
                if s.subsection == "tables":
                    if not s.value:
                        raise PackError("第 {} 行表 {} 缺少表单标识".format(s.lineno, s.key))
                    if s.key in container:
                        raise PackError("第 {} 行重复表：{}".format(s.lineno, s.key))
                    container[s.key] = s.value
                else:
                    if s.value:
                        raise PackError("第 {} 行 {} 不应带值".format(s.lineno, s.key))
                    if s.key in container:
                        raise PackError("第 {} 行重复表：{}".format(s.lineno, s.key))
                    container[s.key] = {}
            elif s.indent == 8 and s.subsection == "fields":
                fields_table = cast_dict(cast_dict(apps[s.app]["fields"])[s.table])
                if s.key in fields_table:
                    raise PackError("第 {} 行重复字段：{}".format(s.lineno, s.key))
                fields_table[s.key] = field_spec(s.value, type_policy, s.lineno)
            elif s.indent == 8 and s.subsection == "records":
                cast_dict(cast_dict(apps[s.app]["records"])[s.table])[s.key] = {}
            elif s.indent == 10 and s.subsection == "records":
                cast_dict(cast_dict(cast_dict(apps[s.app]["records"])[s.table])[s.record])[s.key] = s.value

    for key in ("schema_version", "connector"):
        if not meta.get(key):
            raise PackError("语义包缺少顶层键：{}".format(key))
    if not type_policy:
        raise PackError("语义包缺少 type_policy")
    if not apps:
        raise PackError("语义包缺少 apps 块，且至少需登记一个应用")
    for app, item in apps.items():
        tables = cast_dict(item["tables"])
        fields = cast_dict(item["fields"])
        records = cast_dict(item["records"])
        if not tables or not fields:
            raise PackError("应用 {} 必须同时登记 tables 与 fields".format(app))
        if set(tables) != set(fields):
            raise PackError("应用 {} 的 tables 与 fields 表名不一致".format(app))
        for table, table_fields in fields.items():
            if not table_fields:
                raise PackError("应用 {} 的表 {} 没有任何字段".format(app, table))
        for table in records:
            if table not in tables:
                raise PackError("应用 {} 的 records 表 {} 未在 tables 中登记".format(app, table))
    return {"meta": meta, "type_policy": type_policy, "apps": apps}


def cast_dict(value: object) -> dict[str, object]:
    return cast(dict[str, object], value)


def resolve_app(pack: dict[str, object], app: str) -> str:
    return resolve_name({name: "" for name in cast_dict(pack["apps"])}, app, "应用")


def resolve_table(pack: dict[str, object], app: str, table: str) -> str:
    tables = cast_dict(cast_dict(cast_dict(pack["apps"])[app])["tables"])
    return resolve_name({name: str(value) for name, value in tables.items()}, table, "表")


def list_fields(pack: dict[str, object], app: str, table: str) -> list[dict[str, object]]:
    fields = cast_dict(cast_dict(cast_dict(pack["apps"])[app])["fields"])
    result = []
    for name, value in cast_dict(fields[table]).items():
        field_type, policy = str(value).split("@", 1)
        result.append({"name": name, "type": field_type, "writable": policy == "writable"})
    return result
