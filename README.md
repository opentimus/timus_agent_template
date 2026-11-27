# general-timus-expert / Carly 卡莉

专家模板：复制后只换人设、语义包、头像。新增场景复制任一 `skills/timus-add-*/`，改名并只改触发语与步骤。

- `skills/timus-app-data/`：数据层固定入口（解析 / 查改删 / 本地缓存 / 日期点数 / 语义包）与预览页资源（模板 + build 脚本）。
- 场景技能：`timus-add-member`、`timus-add-task`、`timus-add-customer`。
- 依赖 WorkBuddy 连接器 `timus-runtime`：平台读写只走其 MCP 工具 `apaas_*`；`data_tool.py resolve` 把语义包稳定 ID 解析为 `app_name`（app 级 `team_code`）/ `table_name` / `platform_table` / `platform_field`，直接作为 MCP 参数。`add_data.py` 只写本地缓存（返回 `platformWritten=false`），不是平台写入；预览页按钮只导出 JSON，也不写入平台。
- 环境：Python ≥ 3.9，脚本纯标准库；`python3 skills/timus-app-data/scripts/data_tool.py -h` 查看入口。语义包 `references/timus-team.yaml` 中 `TODO_*` / `tblDemo*` 为占位，按实际组织编码与平台表替换后再使用；仅本地查看示例包时 `resolve` 可加 `--allow-demo`，其结果禁止作为平台参数。
- 测试：`python3 -m unittest discover -s tests -v`；连接器另跑 `cd connector/timus-runtime-connector && npm test`。
- 打包：`zip -r general-timus-expert.zip . -x '*.DS_Store' '.git/*' '**/__pycache__/*' 'tests/*' 'connector/*'`

[Apache 2.0](LICENSE)；Copyright 2026 武汉海辞科技有限公司，署名见 [NOTICE](NOTICE)。
