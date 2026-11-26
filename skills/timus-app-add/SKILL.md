---
name: timus-app-add
description: Timus 基础数据批量添加 — 描述「先查 X 表 A 字段、再查 Y 表 B 字段，然后添加到 Z 表」或直接填写字段值，批量添加记录。触发词：添加数据、新增记录、录入、写入、批量添加、批量录入。
version: 1.0.0
agent_created: true
---

# 基础数据批量添加

两种意图：①先查 X 表 A 字段、Y 表 B 字段，再添加到 Z 表；②直接填写字段值，不查询。

## 执行

含查询时先用 `timus-app-maintenance` 的 `data_tool.py` 取值，再写入；直接填写跳过查询。

```bash
python3 <skill-dir>/scripts/add_data.py --table <目标表> --set "S.字段=值|S.字段=值" --set "S.字段=值|..."
```

`--set` 可重复，每次一条记录；记录 ID 自动生成；字段名须在表头元数据中存在。必填 / 选填由创建类型技能约束定义，本技能不推导；其余通用规则见 `agents/general-timus-expert.md`。
