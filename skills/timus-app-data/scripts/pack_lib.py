"""语义包解析与写回：单文件含表头元数据与本地记录；受限 YAML（2 空格缩进，无列表 / 锚点）。"""
from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, NamedTuple

from errors import ToolError

try:
    import fcntl
except ImportError:  # 非 Unix 平台退化为无锁写
    fcntl = None  # type: ignore[assignment]

SECTION_KEYS = ("apps",)
APP_KEYS = ("language", "team_code", "tables", "fields", "records")
VALID_TYPES = ("AutoNumber", "CreatedTime", "Lookup", "User", "Formula", "Text", "Number", "SingleSelect", "DateTime")
PACK_HEADER = "# 语义包：apps → 应用名 → team_code / language / tables / fields / records；team_code 为连接器组织编码，platform[language] 供平台请求。"


class PackError(ToolError):
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


def quote(value: str) -> str:
    text = str(value)
    if "#" in text or '"' in text or "'" in text or "," in text or "}" in text:
        raise PackError("值不能包含 # / 引号 / 逗号 / 右花括号：{}".format(text))
    return '"{}"'.format(text)


def atomic_write(path: str, text: str) -> None:
    """同目录临时文件 + fsync + 原子替换，避免中断写坏语义包。"""
    file = Path(path).expanduser().resolve()
    fd, temp = tempfile.mkstemp(prefix=file.name + ".", suffix=".tmp", dir=str(file.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, file)
        try:
            dir_fd = os.open(str(file.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass  # 非 Unix 文件系统不支持目录 fsync 时退化为仅文件 fsync
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


@contextmanager
def pack_lock(path: str) -> Iterator[None]:
    """同 pack 的读-改-写串行化；非 Unix 平台退化为无锁。"""
    file = Path(path).expanduser().resolve()
    handle = file.with_name(file.name + ".lock").open("a+", encoding="utf-8")
    try:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


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


def parse_platform(value: str, lineno: int) -> dict[str, str]:
    text = value.strip()
    if len(text) < 2 or text[0] != "{" or text[-1] != "}":
        raise PackError("第 {} 行 platform 应写作 {{zh: ..., en: ...}}：{}".format(lineno, value))
    result: dict[str, str] = {}
    for part in text[1:-1].split(","):
        if not part.strip():
            continue
        if ":" not in part:
            raise PackError("第 {} 行 platform 项应为 语种: 值：{}".format(lineno, part))
        key, _, item = part.partition(":")
        key = unquote(key.strip())
        item = unquote(item.strip())
        if not key or not item:
            raise PackError("第 {} 行 platform 项缺少语种或值：{}".format(lineno, part))
        if key in result:
            raise PackError("第 {} 行重复语种：{}".format(lineno, key))
        result[key] = item
    if not result:
        raise PackError("第 {} 行 platform 不能为空".format(lineno))
    return result


def field_spec(value: str, lineno: int) -> str:
    """字段写作 类型 或 类型@read_only。"""
    parts = value.split("@")
    if len(parts) > 2:
        raise PackError("第 {} 行字段类型格式应为 类型 或 类型@read_only：{}".format(lineno, value))
    field_type = parts[0].strip()
    if field_type not in VALID_TYPES:
        raise PackError("第 {} 行未知字段类型：{}".format(lineno, field_type))
    if len(parts) == 2 and parts[1].strip() != "read_only":
        raise PackError("第 {} 行仅支持 @read_only：{}".format(lineno, value))
    return value.strip()


def resolve_name(mapping: dict[str, str], token: str, kind: str) -> str:
    key = (token or "").strip().casefold()
    if not key:
        raise PackError("未指定{}".format(kind))
    if key in mapping:
        return mapping[key]
    hits = {name for alias, name in mapping.items() if key in alias}
    if len(hits) == 1:
        return hits.pop()
    if len(hits) > 1:
        raise PackError("{}「{}」匹配多个：{}。请明确指定".format(kind, token, "、".join(sorted(hits))))
    raise PackError("未知{}「{}」。可用：{}".format(kind, token, "、".join(sorted(set(mapping.values()))) or "(空)"))


def _aliases(specs: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for name, spec in specs.items():
        out[name.casefold()] = name
        for value in spec.get("platform", {}).values():
            out[str(value).casefold()] = name
    return out


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
    field: str


def iter_lines(lines: list[str]) -> Iterator[LineState]:
    """逐行产出缩进状态；section ∈ {meta, apps}，空行与注释 section 为空。"""
    section = app = subsection = table = record = field = ""
    for lineno, raw in enumerate(lines, start=1):
        line = clean_line(raw)
        if not line.strip():
            yield LineState(lineno, raw, -1, "", "", "", "", "", "", "", "")
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, value = split_pair(line.strip(), lineno)
        if indent == 0:
            section = key if key in SECTION_KEYS else "meta"
            app = subsection = table = record = field = ""
        elif section == "apps":
            if indent == 2:
                app, subsection, table, record, field = key, "", "", "", ""
            elif indent == 4:
                subsection = key if key in APP_KEYS else ""
                table = record = field = ""
            elif subsection in ("tables", "fields", "records"):
                if indent == 6:
                    table, record, field = key, "", ""
                elif indent == 8:
                    if subsection == "records":
                        record, field = key, ""
                    else:
                        field = key
                elif indent == 10 and subsection == "records":
                    field = key
        yield LineState(lineno, raw, indent, key, value, section, app, subsection, table, record, field)


def load_pack(path: str, target_app: str = "", target_tables: tuple[str, ...] = ()) -> dict[str, Any]:
    """读取语义包；指定 target_app / target_tables 时只校验目标应用与表。"""
    file = Path(path).expanduser().resolve()
    if not file.is_file():
        raise PackError("找不到语义包文件：{}".format(file))
    meta: dict[str, str] = {}
    apps: dict[str, Any] = {}
    for s in iter_lines(file.read_text(encoding="utf-8").splitlines()):
        if s.section == "meta":
            if s.indent == 0:
                _put(meta, s.key, s.value, s.lineno)
        elif s.section == "apps":
            if s.indent == 2:
                if s.value:
                    raise PackError("第 {} 行应用名 {} 不应带值".format(s.lineno, s.key))
                if s.key in apps:
                    raise PackError("第 {} 行重复应用：{}".format(s.lineno, s.key))
                apps[s.key] = {"language": "", "team_code": "", "tables": {}, "fields": {}, "records": {}}
            elif s.indent == 4 and s.subsection in ("language", "team_code"):
                if not s.value:
                    raise PackError("第 {} 行应用 {} 缺少 {}".format(s.lineno, s.app, s.subsection))
                apps[s.app][s.subsection] = s.value
            elif s.indent == 6 and s.subsection in ("tables", "fields", "records"):
                container = apps[s.app][s.subsection]
                if s.key in container:
                    raise PackError("第 {} 行重复表：{}".format(s.lineno, s.key))
                container[s.key] = {}
            elif s.indent == 8 and s.subsection == "tables":
                spec = apps[s.app]["tables"][s.table]
                if s.key == "id":
                    if not s.value:
                        raise PackError("第 {} 行表 {} 缺少 id".format(s.lineno, s.table))
                    spec["id"] = s.value
                elif s.key == "platform":
                    spec["platform"] = parse_platform(s.value, s.lineno)
                else:
                    raise PackError("第 {} 行未知表属性：{}".format(s.lineno, s.key))
            elif s.indent == 8 and s.subsection == "fields":
                fields_table = apps[s.app]["fields"][s.table]
                if s.key in fields_table:
                    raise PackError("第 {} 行重复字段：{}".format(s.lineno, s.key))
                fields_table[s.key] = {"type": "", "platform": {}}
            elif s.indent == 10 and s.subsection == "fields":
                spec = apps[s.app]["fields"][s.table][s.field]
                if s.key == "type":
                    spec["type"] = field_spec(s.value, s.lineno)
                elif s.key == "platform":
                    spec["platform"] = parse_platform(s.value, s.lineno)
                else:
                    raise PackError("第 {} 行未知字段属性：{}".format(s.lineno, s.key))
            elif s.indent == 8 and s.subsection == "records":
                apps[s.app]["records"][s.table][s.key] = {}
            elif s.indent == 10 and s.subsection == "records":
                apps[s.app]["records"][s.table][s.record][s.key] = s.value

    for key in ("schema_version", "connector"):
        if not meta.get(key):
            raise PackError("语义包缺少顶层键：{}".format(key))
    if not apps:
        raise PackError("语义包缺少 apps 块，且至少需登记一个应用")
    check_apps = [resolve_name({name.casefold(): name for name in apps}, target_app, "应用")] if target_app else list(apps)
    for app in check_apps:
        item = apps[app]
        language = str(item["language"] or "")
        if not language:
            raise PackError("应用 {} 缺少 language".format(app))
        if not str(item.get("team_code") or ""):
            raise PackError("应用 {} 缺少 team_code（连接器组织编码）".format(app))
        tables = item["tables"]
        fields = item["fields"]
        records = item["records"]
        if not tables or not fields:
            raise PackError("应用 {} 必须同时登记 tables 与 fields".format(app))
        if set(tables) != set(fields):
            raise PackError("应用 {} 的 tables 与 fields 表名不一致".format(app))
        for table, spec in tables.items():
            platform = spec.get("platform", {})
            if not spec.get("id") or not platform.get(language):
                raise PackError("应用 {} 的表 {} 缺少 id 或语种 {} 的平台表".format(app, table, language))
        check_tables = [resolve_table({"apps": apps}, app, name) for name in target_tables] if target_tables else list(fields)
        for table in check_tables:
            table_fields = fields.get(table, {})
            if not table_fields:
                raise PackError("应用 {} 的表 {} 没有字段或未登记".format(app, table))
            for field, spec in table_fields.items():
                platform = spec.get("platform", {})
                if not spec.get("type") or not platform.get(language):
                    raise PackError("应用 {} 的表 {} 字段 {} 缺少 type 或语种 {} 的平台字段".format(app, table, field, language))
            for row in records.get(table, {}).values():
                for name in row:
                    if name not in table_fields:
                        raise PackError("应用 {} 的表 {} 记录字段 {} 未在 fields 中登记".format(app, table, name))
        for table in records:
            if table not in tables and (not target_tables or table in check_tables):
                raise PackError("应用 {} 的 records 表 {} 未在 tables 中登记".format(app, table))
    return {"meta": meta, "apps": apps}


def _platform_text(platform: dict[str, str]) -> str:
    return "{" + ", ".join("{}: {}".format(key, quote(value)) for key, value in platform.items()) + "}"


def dump_pack(pack: dict[str, Any]) -> str:
    lines = [
        PACK_HEADER,
        "",
        "schema_version: {}".format(quote(pack["meta"]["schema_version"])),
        "connector: {}".format(quote(pack["meta"]["connector"])),
        "",
        "apps:",
    ]
    for app, item in pack["apps"].items():
        lines.append("  {}:".format(app))
        lines.append("    team_code: {}".format(quote(item["team_code"])))
        lines.append("    language: {}".format(quote(item["language"])))
        for section in ("tables", "fields", "records"):
            lines.append("    {}:".format(section))
            for name, spec in item[section].items():
                lines.append("      {}:".format(name))
                if section == "tables":
                    lines.append("        id: {}".format(quote(spec["id"])))
                    lines.append("        platform: {}".format(_platform_text(spec["platform"])))
                elif section == "fields":
                    for field, field_spec_value in spec.items():
                        lines.append("        {}:".format(field))
                        lines.append("          type: {}".format(quote(field_spec_value["type"])))
                        lines.append("          platform: {}".format(_platform_text(field_spec_value["platform"])))
                else:
                    for record_id, row in spec.items():
                        lines.append("        {}:".format(record_id))
                        for key, value in row.items():
                            lines.append("          {}: {}".format(key, quote(value)))
    return "\n".join(lines) + "\n"


def resolve_app(pack: dict[str, Any], app: str) -> str:
    return resolve_name({name.casefold(): name for name in pack["apps"]}, app, "应用")


def resolve_table(pack: dict[str, Any], app: str, table: str) -> str:
    return resolve_name(_aliases(pack["apps"][app]["tables"]), table, "表")


def resolve_field(pack: dict[str, Any], app: str, table: str, token: str) -> str:
    return resolve_name(_aliases(pack["apps"][app]["fields"][table]), token, "字段")


def list_fields(pack: dict[str, Any], app: str, table: str) -> list[str]:
    return list(pack["apps"][app]["fields"][table])


def platform_table(pack: dict[str, Any], app: str, table: str, language: str = "") -> str:
    language = language or str(pack["apps"][app]["language"])
    value = str(pack["apps"][app]["tables"][table]["platform"].get(language, ""))
    if not value:
        raise PackError("表 {} 缺少语种 {} 的平台表".format(table, language))
    return value


def platform_field(pack: dict[str, Any], app: str, table: str, field: str, language: str = "") -> str:
    language = language or str(pack["apps"][app]["language"])
    value = str(pack["apps"][app]["fields"][table][field]["platform"].get(language, ""))
    if not value:
        raise PackError("字段 {} 缺少语种 {} 的平台字段".format(field, language))
    return value
