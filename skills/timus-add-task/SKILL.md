---
name: timus-add-task
description: 用户说「派任务 / 添加任务」时，写入 task 表。
---

# 任务添加

触发：用户说「派任务 / 添加任务」。仅新增；需查询时走连接器 `apaas_page_records`，不触发编辑、删除。

步骤：
1. `point_util.py normalize|split` 换算点数（两位小数），`date_util.py options|batch` 换算日期（`YYYY-MM-DD HH:mm:ss`），不心算。
2. `data_tool.py resolve table --app <任务应用> --name task` 取 `app_name` / `table_name`；`resolve field --table task --name <语义字段>` 取 `platform_field`，作为 `fields[].name`。示例语义包中 task 属于 `TODO_APP_A`，其解析结果默认被拒绝用于平台写入；须先替换为真实编码。
3. 调用连接器 `apaas_add_record` 一次写入：`fields` 为 `[{"name": "<platform_field>", "value": "..."}]`。
4. 需用户确认点数 / 日期时，可用 `build_html.py` 生成预览页并 `present_files`；点击页面按钮只导出 JSON，不写入平台，确认后仍须调用 `apaas_add_record`。
5. 只回报平台返回的记录 ID 或 `traceId`；本地 `add_data.py` 写入不算平台写入。

通用规则见 `agents/general-timus-expert.md`，数据层命令见 `timus-app-data/SKILL.md`；仅场景需自定义校验时才加脚本，且只组装参数调用 `add_data.py` 或 `build_html.py`。
