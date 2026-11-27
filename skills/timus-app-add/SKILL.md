---
name: timus-app-add
description: Timus 批量添加记录 — 直接填写字段值，或先查后加。
version: 1.0.0
agent_created: true
---

# 基础数据批量添加

两种意图：①先查 X 表 A 字段、Y 表 B 字段，再添加到 Z 表；②直接填写字段值，不查询。含查询时先用 `timus-app-maintenance` 的 `data_tool.py` 取值，再写入。

参数见 `<skill-dir>/scripts/add_data.py -h`。`--app` 必填，填应用名；同名表分属不同应用时先定应用。多条记录用重复 `--set` 一次调用，不拆多次；记录 ID 自动生成。

先查后加用 `--copy-from <源表> --where "sys.字段=值" --map "目标字段=源字段"`，脚本内部查源表并追加，返回新 ID，不再分两次调用。

实例技能固化 `--app` / `--table` / `--pack` 时不再传参或定位。必填 / 选填由创建类型技能定义，本技能不推导；通用规则见 `agents/general-timus-expert.md`。
