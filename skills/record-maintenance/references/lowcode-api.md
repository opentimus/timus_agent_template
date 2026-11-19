# 通用维护写入契约（查 / 改 / 删）

通用参数语义、响应结构、错误处理、安全边界见 `skills/timus-app-schema/references/write-contract.md`。
本文件只写查 / 改 / 删的请求模板与定位规则；新建走 `record-create-form`。

## 查询

| 意图 | 工具 | 关键参数 |
| --- | --- | --- |
| 列表 / 搜索 / 筛选 | `apaas_page_records` | `app_name` + `table_name` + `page_size`（≤50）+ 可选 `query_fields` / `conjunction` / `sort_fields` / `return_fields` |
| 按 ID 取详情 | `apaas_get_record` | `app_name` + `table_name` + `record_id` |

```json
{
  "app_name": "<team_code>",
  "table_name": "<目标表>",
  "page_size": "50",
  "query_fields": [{ "name": "S.<字段>", "operator": "like", "value": "关键词" }],
  "conjunction": "AND",
  "return_fields": ["S.<字段A>", "S.<字段B>"]
}
```

operator 支持 `eq` / `neq` / `like` / `gt` / `ge` / `lt` / `le` / `is` / `isnot`，默认 `eq`。
查询无破坏性，无需确认框；回报匹配条数与关键字段，无匹配如实说明。

## 定位规则（改 / 删共用）

1. 用户给了 `record_id` → 直接用。
2. 没给 → `apaas_page_records` 查询，**必须唯一**：
   - 0 条 → 回报未找到，列出可用筛选维度，请用户补充；
   - 多条 → 列出候选（关键字段 + `record_id`），请用户指定，**不擅自挑一条**；
   - 1 条 → 继续。
3. 可先 `apaas_get_record` 取回完整字段，用于复述旧值或确认删除目标。

## 修改

```json
{
  "app_name": "<team_code>",
  "table_name": "<目标表>",
  "record_id": "<查到的 ID>",
  "fields": [{ "name": "S.<字段>", "value": "<新值>" }]
}
```

- `fields` 只放要改的字段，不放未变更字段。
- 新值按类型：`Text` / `SingleSelect` 字符串、`Number` 经 `point_util` 归一、`DateTime` 取 `date_util` 的 `*_datetime`。
- `record_id` 与 `query_fields` 二选一，都给时以 `record_id` 为准。
- 必经最终确认框：复述关键字段值 + `record_id` + 每个字段「旧值 → 新值」。

## 删除（破坏性）

```json
{ "app_name": "<team_code>", "table_name": "<目标表>", "record_id": "<查到的 ID>" }
```

- 二次确认措辞必须含「**删除不可撤销**」，并复述表名 / `record_id` / 关键字段值。
- 成功后回报被删标识；**不自动重查**（记录已不存在）。

## 本技能特有点

- 不新建、不批量、不改表结构；一次只操作一条记录。
- 不凭记忆填 `record_id`，候选必须来自查询。
- 查可安全重试；改 / 删不重复提交（可能已成功），删除失败不自动重试。
- 语义包仍是模板占位符时，本技能拒绝执行任何写操作（查询也需先填充表名）。
