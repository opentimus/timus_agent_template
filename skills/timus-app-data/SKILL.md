---
name: timus-app-data
description: Timus 稳定数据层：解析 / 查询 / 改 / 删 / 本地缓存 / 日期 / 点数。
---

# 数据层

固定入口，不随 ADD 场景变化：

- `data_tool.py list|resolve|query|set|delete`（本地语义包）
- `add_data.py --app A --table T --row ... [--from S --map ...]`（仅本地缓存，非平台写入）
- `point_util.py`、`date_util.py`

参数见各脚本 `-h`。语义包在 `references/timus-team.yaml`，为机器维护，不保留手工注释；app 级 `team_code` 是连接器 `app_name`，`platform[language]` 是平台标识，`language` 决定取哪一套。字段值不可含 `#` 或引号，只读字段（`*@read_only`）不可写。stdout 仅 JSON，错误走 stderr + exit 2；同 pack 写操作由文件锁串行，写盘为临时文件 + 原子替换。

`resolve table` 返回 `app_name` / `table_name` / `platform_table`；`resolve field` 返回 `field` / `platform_field`。直接把 `app_name`、`table_name`、`platform_field` 作为 `apaas_*` 参数，禁止猜字段名。默认拒绝把 `TODO_*` / `tblDemo*` 示例 ID 作为平台参数；仅为本地查看示例包时加 `--allow-demo`，其结果不可写入平台。

平台写入只走连接器 MCP；本地 `add_data.py` 结果带 `platformWritten=false`，不可当作平台写入回报。`build_html.py` 生成的页面只用于确认预览，页面按钮仅导出待提交 JSON，**不会写入平台**；输出路径限项目目录 / 当前目录 / 临时目录，覆盖已存在文件需 `--force`。
