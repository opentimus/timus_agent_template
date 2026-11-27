---
name: timus-app-data
description: Timus 稳定数据层：解析 / 查询 / 改 / 删 / 写入 / 日期 / 点数。
---

# 数据层

固定入口，不随 ADD 场景变化：

- `data_tool.py list|resolve|query|set|delete`
- `add_data.py --app A --table T --row ... [--from S --map ...]`（唯一写入口）
- `point_util.py`、`date_util.py`

参数见各脚本 `-h`。语义包在 `references/timus-team.yaml`，为机器维护，不保留手工注释。字段值不可含 `#` 或引号。stdout 仅 JSON，错误走 stderr + exit 2；同 pack 写操作串行。
