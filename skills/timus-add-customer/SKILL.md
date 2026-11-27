---
name: timus-add-customer
description: 用户说「新增客户 / 录客户」时，写入 customer 表。
---

# 客户添加

触发：用户说「新增客户 / 录客户」。仅新增；需查询时走连接器 `apaas_page_records`，不触发编辑、删除。

步骤：
1. `data_tool.py resolve table --app <客户应用> --name customer` 取 `app_name` / `table_name`；`resolve field --table customer --name <语义字段>` 取 `platform_field`，作为 `fields[].name`。示例语义包中 customer 属于 `TODO_APP_B`，其解析结果默认被拒绝用于平台写入；须先替换为真实编码。
2. 调用连接器 `apaas_add_record` 一次写入：`fields` 为 `[{"name": "<platform_field>", "value": "..."}]`。
3. 需用户确认点数 / 日期时，用 `build_html.py` 生成预览页并 `present_files`；点击页面按钮只导出 JSON，不写入平台，确认后仍须调用 `apaas_add_record`。
4. 只回报平台返回的记录 ID 或 `traceId`；本地 `add_data.py` 写入不算平台写入。

通用规则见 `agents/general-timus-expert.md`，数据层命令见 `timus-app-data/SKILL.md`；仅场景需自定义校验时才加脚本，且只组装参数调用 `add_data.py` 或 `build_html.py`。
