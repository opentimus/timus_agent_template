#!/usr/bin/env python3
"""专家包结构自检（零平台依赖，不写文件、不联网、不需令牌）。

两包共用同一份代码，包差异由同目录 pkg_config.py 提供：
1) 语义包可解析且表集与 pkg_config 一致；
2) 目录结构同形（agents 单一、skills 每个目录都有 SKILL.md、tests 三件套）；
3) 每个 SKILL.md frontmatter 完整（name / description / version）；
4) 通用契约集中在语义包技能 SKILL.md（AskUserQuestion / 两步确认 / 降级 / 脚本口径）；
5) plugin.json 技能登记与目录一致、未声明 tools；
6) 禁复述门禁：agents/*.md 与 README.md 不得出现字段清单表格行；
7) 各技能 lowcode-api.md 不得残留「弹窗逐条复述」旧口径，也不得整段复制通用契约；
8) 无 HTML / 代理 / 凭据 / 端口残留；
9) scripts/ 四个脚本哈希与 scripts.lock 一致（两包代码不分叉）。

用法:
  python3 tests/smoke_test.py
  python3 tests/smoke_test.py --update-lock    # 改脚本后刷新哈希
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pkg_config as cfg  # noqa: E402

SCHEMA_SKILL = SKILLS / cfg.SCHEMA_SKILL
SCRIPTS = SCHEMA_SKILL / "scripts"
PLUGIN = ROOT / ".codebuddy-plugin/plugin.json"
LOCK = Path(__file__).resolve().parent / "scripts.lock"
SHARED_SCRIPTS = ("schema_lib.py", "resolve_schema.py", "point_util.py", "date_util.py")
FORBIDDEN_FILES = ("*.html", "build_form.py", "submit_proxy.py", "build_core.py", "proxy_core.py")
CREDENTIAL_TOKENS = ("Authorization", "Bearer ")
PORTS = ("18700", "18765", "18766", "18767", "18768", "18769", "18770", "18771", "18772")
FIELD_TYPE_ANNOTATION = re.compile(
    r"`S\.[^`]+`\s*\((Text|Number|DateTime|SingleSelect|Lookup|User|AutoNumber|Formula)\)"
)
FIELD_ROW = re.compile(r"^\|\s*`S\.")

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if cond:
        print("  ok  " + msg)
    else:
        failures.append(msg)
        print("  FAIL " + msg)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def frontmatter_fields(text: str) -> set[str]:
    if not text.startswith("---"):
        return set()
    end = text.find("\n---", 3)
    if end < 0:
        return set()
    found: set[str] = set()
    for line in text[3:end].splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):", line)
        if m:
            found.add(m.group(1))
    return found


def skill_dirs() -> list[str]:
    return sorted(p.name for p in SKILLS.iterdir() if p.is_dir())


def all_skills() -> list[str]:
    return sorted(set(skill_dirs()))


def check_schema() -> None:
    print("[1] 语义包")
    resolver = SCRIPTS / "resolve_schema.py"
    schema_path = SCHEMA_SKILL / "references" / cfg.SCHEMA_FILE
    r = subprocess.run([sys.executable, str(resolver), "--schema", str(schema_path), "--list-tables"],
                       capture_output=True, text=True)
    check(r.returncode == 0, "resolve_schema --list-tables 退出码 0")
    try:
        payload = json.loads(r.stdout or "{}")
    except ValueError:
        payload = {}
    check(payload.get("team_code") == cfg.APP_CODE,
          "team_code == {}（实际 {}）".format(cfg.APP_CODE, payload.get("team_code")))
    names = {t["name"] for t in payload.get("tables", [])}
    check(names == set(cfg.REQUIRED_TABLES),
          "表集与 pkg_config 一致（缺 {} / 多 {}）".format(
              sorted(set(cfg.REQUIRED_TABLES) - names), sorted(names - set(cfg.REQUIRED_TABLES))))


def check_layout() -> None:
    print("[2] 目录结构同形")
    agents = sorted((ROOT / "agents").glob("*.md"))
    check(len(agents) == 1, "agents 目录恰好一个 *.md")
    check((ROOT / "tests").is_dir(), "包根存在 tests/（不再用 skills/_shared）")
    check(not (SKILLS / "_shared").exists(), "skills/_shared 已移除")
    for name in skill_dirs():
        check((SKILLS / name / "SKILL.md").is_file(), "{} 有 SKILL.md".format(name))
    check((ROOT / "avatars").is_dir(), "avatars 目录存在")
    check((ROOT / "README.md").is_file(), "README.md 存在")


def check_frontmatter() -> None:
    print("[3] 技能 frontmatter")
    for name in all_skills():
        text = read_text(SKILLS / name / "SKILL.md")
        fields = frontmatter_fields(text)
        check({"name", "description", "version"}.issubset(fields),
              "{} frontmatter 含 name/description/version".format(name))


def check_contract_layer() -> None:
    print("[4] 通用契约层（语义包技能）")
    text = read_text(SCHEMA_SKILL / "SKILL.md")
    for term in ("AskUserQuestion", "正文清单", "精简确认框", "降级", "确认提交",
                 "point_util.py", "date_util.py", "write-contract.md", "intent-routing.md"):
        check(term in text, "schema SKILL 含 {}".format(term))
    check((SCHEMA_SKILL / "references/write-contract.md").is_file(), "write-contract.md 存在")
    check((SCHEMA_SKILL / "references/intent-routing.md").is_file(), "intent-routing.md 存在")
    for name in cfg.FORM_SKILLS:
        skill_text = read_text(SKILLS / name / "SKILL.md")
        check("apaas_add_record" in skill_text, "{} 含 apaas_add_record".format(name))
        check(cfg.SCHEMA_SKILL in skill_text, "{} 引用通用规范".format(name))


def check_no_restatement() -> None:
    print("[5] 禁复述门禁")
    for target in list((ROOT / "agents").glob("*.md")) + [ROOT / "README.md"]:
        text = read_text(target)
        hits = [ln for ln in text.splitlines() if FIELD_TYPE_ANNOTATION.search(ln) or FIELD_ROW.match(ln)]
        check(not hits, "{} 无字段清单表格行".format(target.name))

    for name in all_skills():
        doc = SKILLS / name / "references" / "lowcode-api.md"
        if not doc.is_file():
            continue
        text = read_text(doc)
        check("逐条复述" not in text, "{} lowcode-api 无「逐条复述」旧口径".format(name))
        check("## 响应结构" not in text, "{} lowcode-api 未复制响应结构".format(name))
        check("## 安全边界" not in text, "{} lowcode-api 未复制安全边界".format(name))
        check(len(text.splitlines()) <= 100, "{} lowcode-api ≤100 行".format(name))


def check_registration() -> None:
    print("[6] plugin.json")
    if not PLUGIN.is_file():
        check(False, "缺少 plugin.json")
        return
    try:
        data = json.loads(read_text(PLUGIN))
    except ValueError:
        check(False, "plugin.json 解析失败")
        return
    declared = {str(p).rstrip("/").split("/")[-1] for p in data.get("skills", [])}
    check(declared == set(skill_dirs()),
          "skills 登记与目录一致（缺 {} / 多 {}）".format(sorted(set(skill_dirs()) - declared),
                                                   sorted(declared - set(skill_dirs()))))
    check("tools" not in data, "plugin.json 未声明 tools")
    check(data.get("name") == data.get("agentName") == data.get("plugin"),
          "plugin name / agentName / plugin 三者一致")
    check(data.get("dependencies", {}).get("connectors") == ["timus-runtime"],
          "声明 timus-runtime 连接器依赖")


def check_no_legacy() -> None:
    print("[7] 旧机制残留")
    for pattern in FORBIDDEN_FILES:
        hits = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob(pattern)]
        check(not hits, "无 {} 文件{}".format(pattern, "" if not hits else " 残留 " + ",".join(hits)))

    self_path = Path(__file__).resolve()
    texts = [p for p in ROOT.rglob("*")
             if p.is_file() and p.suffix in (".md", ".py", ".json", ".yaml")
             and p.resolve() != self_path]
    for token in CREDENTIAL_TOKENS:
        hits = [p.relative_to(ROOT).as_posix() for p in texts if token in read_text(p)]
        check(not hits, "无凭据字面量 {}{}".format(token, "" if not hits else " 出现在 " + ",".join(hits)))
    port_hits = [p.relative_to(ROOT).as_posix() for p in texts if any(port in read_text(p) for port in PORTS)]
    check(not port_hits, "无本地代理端口残留")


def digests() -> dict[str, str]:
    return {name: hashlib.sha256((SCRIPTS / name).read_bytes()).hexdigest() for name in SHARED_SCRIPTS}


def check_scripts_lock(update: bool) -> None:
    print("[8] 脚本哈希锁")
    current = digests()
    if update:
        LOCK.write_text(json.dumps({"package": ROOT.name, "files": current}, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        print("  ok  已刷新 scripts.lock")
        return
    if not LOCK.is_file():
        check(False, "缺少 scripts.lock（先跑 --update-lock）")
        return
    try:
        expected = json.loads(read_text(LOCK)).get("files", {})
    except ValueError:
        expected = {}
    for name in SHARED_SCRIPTS:
        check(current.get(name) == expected.get(name),
              "{} 哈希与 lock 一致".format(name))


def main() -> int:
    update = "--update-lock" in sys.argv
    print("=== {} ===".format(ROOT.name))
    check_schema()
    check_layout()
    check_frontmatter()
    check_contract_layer()
    check_no_restatement()
    check_registration()
    check_no_legacy()
    check_scripts_lock(update)
    print("")
    if failures:
        print("SMOKE FAILED：{} 项未通过".format(len(failures)))
        return 1
    print("SMOKE OK：全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
