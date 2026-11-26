---
name: timus-app-add
description: Timus 批量添加记录 — 直接填写字段值，或先查后加。
version: 1.0.0
agent_created: true
---

# 基础数据批量添加

两种意图：①先查 X 表 A 字段、Y 表 B 字段，再添加到 Z 表；②直接填写字段值，不查询。含查询时先用 `timus-app-maintenance` 的 `data_tool.py` 取值，再写入。

参数见 `<skill-dir>/scripts/add_data.py -h`。`--app` 必填，接受本地应用名或 `app_name`；同名表分属不同应用时先定应用。`--set` 可重复，每条一记录；记录 ID 自动生成；字段名须在该应用表头元数据中存在。必填 / 选填由创建类型技能定义，本技能不推导；通用规则见 `agents/general-timus-expert.md`。
