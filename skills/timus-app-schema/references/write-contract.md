# 通用写入契约（两包同一份）

`timus-runtime` 读写参数的**唯一通用权威源**：参数语义、响应结构、错误处理、安全边界。本地基础数据的查 / 改 / 删见 `timus-app-maintenance` 技能，不重复本文件。

凭据（地址 / 令牌）由用户在 WorkBuddy `timus-runtime` 连接设置填写，注入连接器进程环境变量；不经对话、命令行或本包文件。

## 写入链路

`采集（弹窗 + 对话） → 助手校验 → 正文清单（表格） → 精简确认框 → 调用连接器 → 回报结果`

助手直调连接器；不经本地代理、不生成 HTML、浏览器不参与。字段不确定或报错才用 `scripts/resolve_schema.py` 降级复核；热路径直接构造参数。

## 参数语义

| 工具参数 | 来源 | 规则 |
| --- | --- | --- |
| `app_name` | 语义包 `team_code` | 所有工具共用，不手写 |
| `table_name` | 语义包表单名 | 中文名；`tbl...` 仅元数据，禁传 |
| `fields[].name` | 语义包系统字段名 | 逐字含前缀；界面别名禁传 |
| `fields[].value` | 语义包 `type_policy` | `Text` / `SingleSelect` 字符串、`Number` 数值、`DateTime` 完整 `YYYY-MM-DD HH:mm:ss` |
| `query_fields[]` | `name` / `operator` / `value` | operator 默认 `eq`；支持 `neq` / `like` / `gt` / `ge` / `lt` / `le` / `is` / `isnot` |
| `conjunction` | `AND` / `OR` | 多条件用；复杂嵌套用 `composite_query` |
| `return_fields[]` | 语义包字段名 | 只要部分字段时用 |
| `page_size` | 整数 | ≤50；翻页 `page_num`，飞书续页 `page_token`（不混用） |
| `record_id` | 查询结果 | 改 / 删优先；与 `query_fields` 二选一，都给以 `record_id` 为准 |

只读类型：`AutoNumber` / `CreatedTime` / `Lookup` / `User` / `Formula`。「本技能不写入」是行为描述，不等于字段只读。

## 响应结构

成功：`data` 为新记录 ID（`add` 常无 `success`，以 `data` 非空判定）：

```json
{ "ok": true, "data": "recXXX", "traceId": "-" }
```

失败三件套：

```json
{ "ok": false, "errorCode": "kits_lowcode_error_table_config_not_found", "errorMessage": "…", "traceId": "…" }
```

> `traceId` 常为 `"-"`，非可追溯编号；以记录 `id` 为主。仅创建指令回报 `traceId`，其余不报。

## 错误处理

| 情况 | 处理 |
| --- | --- |
| `kits_lowcode_error_table_config_not_found` / `tmc_error_team_not_found` | 核对 `app_name`（`team_code`）与 `table_name` |
| HTTP 401 / 403 | 用户更新令牌或确认权限，不重试 |
| HTTP 404 / 网络错误 / 超时 | 核对地址；结果未知先按 ID / 流水号查询再定 |
| 字段值被拒 | 按语义包复核字段名、类型、可写性 |
| 定位不唯一（0 或多条） | 请用户补条件或给 `record_id`，不擅自选 |

## 部分失败

- 不回滚、不自动重试；同一条不重复提交（可能已成功）。
- 按流水号 / 名称 + 关联 ID 查实际落库，列已写入与失败明细，由用户决定是否补写。
- 全部成功不回查；`id` 即成功凭据。

## 安全边界

- 令牌、地址不进对话 / 日志 / 包内文件；仅在连接设置与连接器进程内。
- 关联 ID 候选先查本地基础数据，未命中才 `apaas_page_records`，禁凭记忆。
- 敏感字段真实值仅写入参数明文；清单 / 弹窗 / 回报 / 日志脱敏。
- 禁伪造工具名 / 参数、绕连接器直连 REST、删表、改表结构、放开任意表 / 条件查询。
