# 通用建档写入契约（本技能差异）

通用参数语义、响应结构、错误处理、安全边界见 `skills/timus-app-schema/references/write-contract.md`；
采集与确认流程见 `timus-app-schema/SKILL.md` 的「录入与维护技能的通用规范」。本文件只写通用建档技能的差异。

## 目标表定位

```json
{
  "app_name": "<语义包 team_code>",
  "table_name": "<语义包 tables 下的表单名>"
}
```

`app_name` 与 `table_name` 都从语义包取，不手写；表单标识 `tbl...` 不进参数。

## 关联字段候选查询

对所有 `Text` 类型且形如 `S.<实体>ID` 的字段，先查候选：

```json
{
  "app_name": "<team_code>",
  "table_name": "<父级表名>",
  "page_size": "50",
  "return_fields": ["S.<实体>", "S.<实体>ID"]
}
```

- 是否加状态过滤由技能显式声明；未声明即不加过滤（默认全量）。
- 若父级表本身有「黑名单」之类显式排除语义，才加 `query_fields`，并写在本技能调用说明里，不外扩到其他表。
- 只取前一页（≤50 条），按名称排序去重；超过 4 项按通用规范分屏。
- 只读候选需要的两列；父级表若有敏感列（令牌 / 密钥），**不读取、不回显**。

## 字段映射（按类型推导）

| 语义包类型 | 写入取值 | 来源 |
| --- | --- | --- |
| `Text`（自由文本） | 字符串 | 对话，trim + 长度校验 |
| `Text`（`S.<实体>ID`） | 父级查询原值 | 候选弹窗 / 精确匹配 / 上游继承 |
| `Text`（单号，用户未给） | `point_util` 生成 | `next-pair` 或 `next-batch` |
| `SingleSelect` | 字符串 | 对话选择，或技能预置固定值 |
| `Number` | 数值 | `point_util normalize`（批量总量用 `split`） |
| `DateTime` | `YYYY-MM-DD HH:mm:ss` | `date_util` 的 `*_datetime` |

## 参数模板

```json
{
  "app_name": "<team_code>",
  "table_name": "<目标表>",
  "fields": [
    { "name": "S.<外键ID>", "value": "<父级查询原值>" },
    { "name": "S.<名称>", "value": "示例值" },
    { "name": "S.<数量>", "value": 6.57 },
    { "name": "S.<备注>", "value": "选填，空则省略该 fields 项" }
  ]
}
```

选填字段为空时**省略该 `fields` 项**，不传空字符串占位；必填字段不得省略。

## 本技能特有点

- 多条录入 = 多个上述参数对象，逐条调用；同批共用同一组关联值。
- 有强序依赖（父 → 子 → 孙）时串行写入，无依赖时同轮并行。
- 只读类型（`AutoNumber` / `CreatedTime` / `Lookup` / `User` / `Formula`）永远不出现在 `fields` 中。
- 语义包仍是模板占位符（`<表A>` / `<APP_CODE>` 之类）时，本技能拒绝执行写入。
