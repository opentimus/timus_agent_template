# 通用建档写入契约（本技能差异）

参数 / 响应 / 错误 / 安全见 `skills/timus-app-schema/references/write-contract.md`；采集与确认见 `timus-app-schema/SKILL.md`「录入与维护技能的通用规范」。本文件只写差异。

## 目标表定位

```json
{
  "app_name": "<语义包 team_code>",
  "table_name": "<语义包 tables 下的表单名>"
}
```

两者均取自语义包，不手写；`tbl...` 不进参数。

## 关联字段候选查询

对所有 `Text` 且形如 `S.<实体>ID` 的字段先查候选：

```json
{
  "app_name": "<team_code>",
  "table_name": "<父级表名>",
  "page_size": "50",
  "return_fields": ["S.<实体>", "S.<实体>ID"]
}
```

- 状态过滤由技能显式声明；未声明即不加。
- 仅显式排除语义（如「黑名单」）才加 `query_fields`，写在本技能说明里，不外扩。
- 只取前一页（≤50），按名称排序去重；超过 4 项按通用规范分屏。
- 只读候选两列；父级敏感列（令牌 / 密钥）不读、不回显。

## 字段映射（按类型推导）

| 语义包类型 | 写入取值 | 来源 |
| --- | --- | --- |
| `Text`（自由文本） | 字符串 | 对话，trim + 长度校验 |
| `Text`（`S.<实体>ID`） | 父级查询原值 | 候选弹窗 / 精确匹配 / 上游继承 |
| `Text`（单号，用户未给） | `point_util` 生成 | `next-pair` / `next-batch` |
| `SingleSelect` | 字符串 | 对话选择或预置固定值 |
| `Number` | 数值 | `point_util normalize`（总量 `split`） |
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

选填为空**省略该项**，不传空串；必填不得省略。

## 本技能特有点

- 多条 = 多个参数对象逐条调用；同批共用关联值。
- 强序依赖（父 → 子 → 孙）串行；无依赖同轮并行。
- 只读类型（`AutoNumber` / `CreatedTime` / `Lookup` / `User` / `Formula`）禁入 `fields`。
- 语义包仍为占位符（`<表A>` / `<APP_CODE>`）时拒绝写入。
