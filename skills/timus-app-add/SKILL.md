---
name: timus-app-add
description: Timus 基础数据批量添加技能 — 用户只需描述「先查 X 表 A 字段、再查 Y 表 B 字段，然后添加到 Z 表」，或直接填写字段值，即可对指定表批量添加数据。触发词：添加数据、新增记录、录入、写入、批量添加、批量录入。
version: 1.0.0
agent_created: true
---

# 基础数据批量添加

用户只需描述两种意图：

1. 先查 X 表 A 字段、Y 表 B 字段，再添加到 Z 表，A / B / C 字段分别填什么。
2. 直接填写字段值，不需要查询。

## 执行

- 含查询：先用 `timus-app-maintenance` 的 `data_tool.py` 取值，再写入。
- 直接填写：跳过查询。

```bash
python3 <skill-dir>/scripts/add_data.py --table <目标表> --set "S.字段=值|S.字段=值" --set "S.字段=值|..."
```

`--set` 可重复，每次一条记录；记录 ID 自动生成；字段名须在表头元数据中存在。

## 约束

- 必填 / 选填由创建类型技能约束定义，本技能不推导。
- 数值 / 日期由 `point_util.py` / `date_util.py` 出数，不心算、不手拼。
- 回报自然简约；不重复提交可能已成功的记录。

## 资源

- `skills/timus-app-schema/references/timus-team-schema.yaml`：表头元数据，字段唯一来源。
- `skills/timus-app-schema/references/timus-team-data.yaml`：基础数据，本地业务块。
- `skills/timus-app-maintenance/scripts/data_tool.py`：本地查询。
