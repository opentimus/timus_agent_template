---
name: timus-runtime
description: Timus Runtime 组织元数据操作技能 - 分页查询、查看详情、新增、修改、删除元数据记录
version: 1.3.0
author: Timus
---

# Timus Runtime 组织元数据 Skill

读写 Timus Runtime 组织元数据记录。服务地址与令牌由连接器「连接设置」注入 `API_BASE_URL`（必须 https）/ `CLIENT_TOKEN`；不要向用户索取、回显或写入工具参数。

## 工具

所有工具都需要 `app_name`（组织编码）与 `table_name`（平台配置的元数据表名）；完整参数以 `tools/list` 的 `inputSchema` 为准。

| 工具 | 作用 | 关键参数 |
| --- | --- | --- |
| `apaas_page_records` | 分页查询，也是取 `id` 与真实字段名的主要方式 | `page_size`（字符串，必填）、`page_num`、`page_token`、`query_fields`、`composite_query`、`sort_fields`、`return_fields` |
| `apaas_get_record` | 按 id 看详情 | `record_id` |
| `apaas_add_record` | 新增 | `fields`: `[{"name":"S.客户","value":"远景科技"}]` |
| `apaas_edit_record` | 修改 | `record_id` 或 `query_fields`（二选一，优先 id）+ `fields` |
| `apaas_delete_record` | 删除（不可撤销） | `record_id` 或 `query_fields`（二选一） |

## schema 之外的必要规则

1. 字段名是平台内部标识（如 `S.客户`），不是界面标题。来源：上游注入 → 用户给出 → `apaas_page_records` 读一条样本取 `payloadFieldList[].name` → 向用户索取。禁止猜测。
2. 读出的 `value` 常是 `[{"text":"...","type":"text"}]`；回写取 `value[].text`，人员/选项等字段照样本结构写。
3. 条件：`operator` 默认 `eq`；有值字段 `eq/neq/like/nlike/gt/ge/lt/le`，无值字段 `is/isnot`；`value` 传字符串，日期可用 `today`/`pastWeek` 等。`query_fields` 与 `composite_query` 二选一。
4. 分页：返回 `data.rows[]`、`data.total`、`data.pageToken`；用 `page_token` 续页，`pageToken` 为空即末页；用 `return_fields` 限制返回字段。
5. 写前先读：新增确认字段结构，修改确认目标与旧值；删除必须复述目标 `id` 与关键字段并获用户确认，不做模糊批量删。失败先按错误码排查，不盲目重试。
6. 错误响应带 `errorCode` 与可操作提示：401 更新令牌、403 权限不足、404 服务地址不带 `/api`、`kits_lowcode_error_table_config_not_found` 检查 `app_name`/`table_name`；有 `traceId` 时一并反馈。

不在回复、文件或工具参数中出现令牌、`secret`、`accessToken`。
