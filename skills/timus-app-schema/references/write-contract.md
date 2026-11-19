# 通用写入契约（两包同一份）

本文件是 `timus-runtime` 连接器读写参数的**唯一通用权威源**：参数语义、响应结构、错误处理、安全边界。
各技能的 `references/lowcode-api.md` 只写「本表候选查询 + 字段映射 + 特有点」，不重复本文件内容。

凭据（服务地址 / 访问令牌）由用户在 WorkBuddy 的 `timus-runtime` 连接设置中填写，注入连接器进程环境变量，
不经对话、命令行或本包任何文件。

## 写入链路

`采集（弹窗 + 对话） → 助手校验 → 正文清单（表格） → 精简确认框 → 逐条 apaas_add_record → 回报记录 ID`

助手直接调用连接器工具，不经过本地代理、不生成 HTML、浏览器不参与。
字段不确定或写入报错时，才用 `scripts/resolve_schema.py` 降级复核；热路径直接构造参数。

## 参数语义

| 工具参数 | 来源 | 规则 |
| --- | --- | --- |
| `app_name` | 语义包顶层 `team_code` | 所有工具共用，不手写 |
| `table_name` | 语义包 `tables` 下的表单名 | 中文表单名；表单标识 `tbl...` 仅元数据，禁止传给接口 |
| `fields[].name` | 语义包 `fields.<表>` 下的系统字段名 | 逐字使用，含前缀差异；界面别名禁止传入 |
| `fields[].value` | 语义包 `type_policy` | `Text` / `SingleSelect` 字符串、`Number` 数值、`DateTime` 完整 `YYYY-MM-DD HH:mm:ss` |
| `query_fields[]` | `name` / `operator` / `value` | operator 默认 `eq`，支持 `neq` / `like` / `gt` / `ge` / `lt` / `le` / `is` / `isnot` |
| `conjunction` | `AND` / `OR` | 多条件时使用；复杂嵌套用 `composite_query` |
| `return_fields[]` | 语义包字段名 | 只要部分字段时使用 |
| `page_size` | 整数 | 上限 50；翻页用 `page_num`，飞书数据源续页用 `page_token`（不与 `page_num` 混用） |
| `record_id` | 查询结果 | 改 / 删优先用；与 `query_fields` 二选一，都给时以 `record_id` 为准 |

可写性一律以语义包 `type_policy` 为唯一权威源：`AutoNumber` / `CreatedTime` / `Lookup` / `User` / `Formula` 只读。
「本技能不写入」只是行为描述，**不等于字段只读**，两者不得混为一谈。

## 响应结构

成功时 `data` 为新记录 ID（`add` 接口常不带 `success` 字段，以 `data` 非空判定）：

```json
{ "ok": true, "data": "recXXX", "traceId": "-" }
```

失败时保留三件套：

```json
{ "ok": false, "errorCode": "kits_lowcode_error_table_config_not_found", "errorMessage": "…", "traceId": "…" }
```

> `traceId` 常见返回 `"-"`，此时它不是可追溯编号：以记录 `id` 为主追溯依据，`traceId` 仅在为有效值时一并回报。

## 错误处理

| 情况 | 处理 |
| --- | --- |
| `kits_lowcode_error_table_config_not_found` / `tmc_error_team_not_found` | 核对 `app_name`（语义包 `team_code`）与 `table_name` 是否与平台一致 |
| HTTP 401 / 403 | 请用户在连接设置中更新访问令牌或确认权限，不重试 |
| HTTP 404 / 网络错误 / 超时 | 核对服务地址；结果未知时先按 ID 或流水号查询再决定 |
| 字段值被拒 | 按语义包复核字段名、类型与可写性 |
| 定位不唯一（0 条或多条） | 请用户补充条件或给 `record_id`，不擅自选择 |

## 部分失败

- 不回滚、不自动重试。同一条不重复提交（可能已成功）。
- 按流水号 / 名称 + 关联 ID 查询核对实际落库情况，列出已写入与失败明细，由用户决定是否人工补写。
- 全部成功时不再回查；记录 `id` 已是成功凭据。

## 安全边界

- 不在对话、日志或包内文件中写入或回显令牌、服务地址；凭据只在连接设置与连接器进程内。
- 关联 ID（渠道 / 客户 / 交付单元 / 项目）候选必须来自 `apaas_page_records` 查询，禁止凭记忆填写。
- 敏感业务字段（如交付单元 `S.令牌`）：真实值只在写入参数中明文使用，正文清单、弹窗、回报、日志一律脱敏。
- 不伪造工具名或参数，不绕过连接器直连 REST，不删表、不改表结构，不放开任意表 / 任意条件查询。
