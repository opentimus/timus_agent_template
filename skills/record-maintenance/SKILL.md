---
name: record-maintenance
description: Timus 多维表通用数据维护 — 查询（分页列表 / 按 ID 详情）、修改、删除，覆盖语义包登记的全部表。触发词：查记录、查数据、搜、列出、详情、看一下、改记录、更新记录、修改状态、修正字段、删记录、删除记录、移除。表与字段以 timus-app-schema 语义包为唯一来源；修改必经最终确认框，删除须二次确认且不可撤销。
version: 1.0.0
agent_created: true
---

# 通用数据维护（查 / 改 / 删）

对语义包登记的表查 / 改 / 删；新建走 `record-create-form`。

参数 / 响应 / 错误 / 安全见 `skills/timus-app-schema/references/write-contract.md`；采集规范见 `timus-app-schema/SKILL.md`。**不绑定具体实体**：表名、字段名、关键字段均取自语义包与运行时判定。

## 触发条件

「查 / 搜 / 列出 / 详情」「改 / 更新 / 修正 / 改状态」「删 / 删除 / 移除」。覆盖全部登记的表；**不新建、不批量、不改表结构**。

## 动作硬映射（命中即动作，不确认动作类型）

| 用户关键词 | 动作 | 连接器工具 | 破坏性 |
| --- | --- | --- | --- |
| 查、查记录、查数据、搜、列出、有哪些、详情、看一下 | 查询 | `apaas_page_records`（列表）/ `apaas_get_record`（详情） | 否 |
| 改、修改、更新、修正、改成、设置为、改状态 | 修改 | `apaas_edit_record` | 否（必经确认框） |
| 删、删除、移除、删掉、清掉 | 删除 | `apaas_delete_record` | 高（二次确认） |

- 意图含糊（如「处理一下这条记录」）先弹 `AskUserQuestion` 选动作。
- 数值 / 日期字段修改同走 `point_util` / `date_util`，不口算、不手拼。

## 表与字段定位

- 表名按 `intent-routing.md`「表定位规则」匹配 `tables`；多张弹窗选，零命中列可用表。
- 字段名逐字用语义包系统字段名，禁历史别名 / 界面标题。
- 可写性以 `type_policy` 为准：只读类型（`AutoNumber` / `CreatedTime` / `Lookup` / `User` / `Formula`）拒写；未知字段拒绝并请用户给准确名。

## 「关键字段」怎么定（删除与修改的复述依据）

不硬编码业务字段，取第一个可用者：

1. 该表首个 `Text` 且名含「名称 / 标题 / 单号 / 编号」的字段；
2. 否则首个 `Text` 字段；
3. 都没有用 `record_id`。

复述时「关键字段值 + `record_id`」并给，避免同名误删。

## 一、查询（无破坏性，直接查）

- **列表 / 搜索 / 筛选** → `apaas_page_records`：`app_name` + `table_name` + `page_size`（≤50）；条件 `query_fields`（operator 默认 `eq`）、多条件 `conjunction`、部分字段 `return_fields`、排序 `sort_fields`；飞书续页传 `page_token`（不与 `page_num` 混用）。
- **按 ID 详情** → `apaas_get_record`：`app_name` + `table_name` + `record_id`。

直接调用，无需确认；回报条数与关键字段，无匹配如实说明，不编造。统计 / 对账在结果上完成。

## 二、修改（先查询确认目标，再确认后写）

1. **定位**：有 `record_id` 直接用；无则 `apaas_page_records` 查询且**必须唯一**（0 条报未找到；多条请补条件或给 ID，不擅自挑）。可用 `apaas_get_record` 取当前值确认改哪些字段。
2. **采集新值**：逐项对话；字段名 / 类型按语义包校验，只读字段拒绝。**一次只改一条。**
3. **构造参数**：`apaas_edit_record`，`fields` 只放要改字段；`record_id` 与 `query_fields` 二选一，都给以 `record_id` 为准。
4. **最终确认框（必经）**：复述「表名 / 记录 ID / 关键字段值 / 各字段旧值 → 新值」；选项 `确认提交`（首位、「（推荐）」）/ `取消 / 返回修改`。用户说「直接改 / 不用确认」也须弹框。
5. 回报记录 ID；`traceId` 有效时一并回报。

## 三、删除（破坏性，二次确认，不可撤销）

1. **定位**：同修改——有 ID 直接用，无则查且**唯一**；可先 `apaas_get_record` 取完整字段确认目标。
2. **二次确认（必经）**：弹 `AskUserQuestion`，写明「**删除不可撤销**」，复述「表名 / 记录 ID / 关键字段值」；选项 `确认删除`（首位、「（推荐，不可撤销）」）/ `取消`。
3. **构造参数**：`apaas_delete_record`，用 `record_id`（推荐）；无 ID 用 `query_fields` 唯一定位。
4. 回报被删标识与 `traceId`（有效时）；删后不自动重查。

用户说「直接删 / 不用确认」也不得省略；禁用文字复述替代弹窗（除非宿主无弹窗能力，此时文字须含「不可撤销」并收到明确「确认删除」）。

## 降级与禁止

- 弹窗不可用 → 文字逐项复述：改须明确「确认」，删须明确「确认删除」。
- 不写只读字段；不凭记忆填 `record_id`，候选来自查询。
- 不批量改 / 删；一次只操作一条。
- 不删表、不改表结构、不新建；只操作登记的表。
- 同一条改 / 删不重复提交；查询可重试；删失败不自动重试。

## 示例（通用骨架）

- 「查 <表> 里 <状态> 为 X 的记录」→ `apaas_page_records`（`query_fields` = `<状态字段> eq X`，`page_size=50`）→ 回报列表。
- 「把 <表> 里 XX 的 <字段> 改成 YY」→ 定位唯一 → 复述旧值 → 新值 → 确认框 → `apaas_edit_record` → 回报。
- 「删掉 <表> 里 XX 这条」→ 定位唯一 → 二次确认（含「不可撤销」+ 关键字段值 + `record_id`）→ `apaas_delete_record` → 回报。

## 资源

- `skills/timus-app-schema/references/timus-team-schema.yaml`：表 / 字段 / 可写性唯一来源。
- `skills/timus-app-schema/references/write-contract.md`：参数 / 响应 / 错误 / 安全。
- `references/lowcode-api.md`：查 / 改 / 删请求模板与定位规则。
