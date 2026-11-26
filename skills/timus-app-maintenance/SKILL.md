---
name: timus-app-maintenance
description: Timus 数据记录维护技能 — 行为层唯一权威源：意图路由、采集渠道与查 / 改 / 删流程。对本地基础数据做查 / 改 / 删，字段以 timus-app-schema 的表头元数据为准。触发词：查记录、查数据、搜、列出、详情、看一下、改记录、更新记录、修正字段、删记录、删除记录、移除、弹窗录入。
version: 1.0.0
agent_created: true
---

# 数据记录维护（查 / 改 / 删）

对本地基础数据做查 / 改 / 删；表名与字段名取自 `timus-app-schema` 的两类 schema。**不绑定具体实体**：表名、字段名、关键字段均由 schema 判定。

本 Skill 是**行为层唯一权威源**：意图路由见 `references/intent-routing.md`。不生成 HTML、不启本地代理、浏览器不参与；对话采集，助手直调脚本。

## 意图路由

动作族与逐关键词映射见 `references/intent-routing.md`（唯一权威源）；命中即执行，不确认动作类型。意图含糊（如「处理一下这条记录」）先弹 `AskUserQuestion` 选动作，不猜测。

## 信息类别与采集渠道

| 信息类别 | 采集渠道 | 校验 / 生成位置 |
| --- | --- | --- |
| 固定值（类型枚举等） | 技能预置；有互斥分支用 `AskUserQuestion` 单选 | 禁用户改写 |
| 平台关联值（外键 ID、候选） | 先查基础数据，未命中再 `apaas_page_records` 查候选 → `AskUserQuestion` 单选 | 核对原值，禁凭记忆填 ID |
| 自由文本 | 对话提问 | trim + 长度校验 |
| 数值 | 首句解析 / 弹窗单选常用值 | 一律 `point_util.py normalize`；正数、两位小数；总量 `split` |
| 单号 | 不采集 | `point_util.py next-pair` / `next-batch` |
| 日期 | `date_util.py options` 候选 → 弹窗选择 | 写入取脚本 `*_datetime`，不心算星期、不手拼格式 |

## 字段到采集渠道映射

具体字段表由本技能给出，本节只定**判定顺序**：

1. `Lookup` / `AutoNumber` / `CreatedTime` / `Formula` → 不采集、不写入；`User` 可写，必须传入 `open_id`。
2. 在本技能「固定值」清单 → 预置值，不问。
3. 外键 ID（`S.<实体>ID` 且 `Text`）→ 先查本地基础数据 / 远程候选 + 弹窗，或上游继承。
4. `Number` → `point_util`。
5. `DateTime` → `date_util`。
6. 其余 → 对话自由文本。

## AskUserQuestion 契约

宿主内置工具，本专家不声明 `tools`；按宿主可用能力调用，禁伪造工具名 / 参数。

- 每次 1–4 题，每题 2–4 选项；`header` ≤12 字符，`label` 1–5 词并附 `description`。
- 推荐项首位并标「（推荐）」；互不依赖的选择合并**同一次**调用。
- 弹窗只承载选择题与动作选择，不承载长文本与字段明细。
- 开放输入由 UI「其他」承接，**不手工添加「自定义 / 其他」**。

## 候选查询规则

- 先查本地基础数据；未命中再 `apaas_page_records` 查候选；禁手写 / 凭记忆填关联 ID。
- 超过 4 项：取前 4 +「查看更多」分屏翻页，保证全部可逐屏选到。
- 状态过滤由技能显式声明；**未声明即不加**（默认全量）。
- 选项会话内复用；用户要求刷新才重查。

## 表与字段定位

- 表名按 `references/intent-routing.md`「表定位规则」匹配表头元数据 `tables`；多张弹窗选，零命中列可用表。
- 字段名逐字用系统字段名，禁历史别名 / 界面标题。
- 可写性以 `type_policy` 为准：只读类型拒写；未知字段直接拒绝。
- 记录 ID 由本地基础数据提供，禁凭记忆填写。

## 「关键字段」怎么定（复述依据）

不硬编码业务字段，取第一个可用者：

1. 该表首个 `Text` 且名含「名称 / 标题 / 单号 / 编号」的字段；
2. 否则首个 `Text` 字段；
3. 都没有用记录 ID。

复述时「关键字段值 + 记录 ID」并给，避免同名误改 / 误删。

## 一、查询（无破坏性）

```bash
python3 <skill-dir>/scripts/data_tool.py --list-tables
python3 <skill-dir>/scripts/data_tool.py --table <表名>
python3 <skill-dir>/scripts/data_tool.py --table <表名> --where "S.字段=值" --fields "S.字段A" "S.字段B"
```

`--where` 可重复（AND），`--fields` 可多值。直接执行；回报条数与关键字段，无匹配如实说明，不编造。统计 / 对账在结果上完成。

## 二、修改（先定位，再写入）

1. **定位**：有记录 ID 直接用；无则查询且**必须唯一**（0 条报未找到；多条请补条件或给 ID，不擅自挑）。
2. **采集新值**：按上文映射逐项采集；字段名 / 类型按表头元数据校验，只读字段拒绝。**一次只改一条。**
3. **执行**：`--record <记录ID> --set "字段=值"`，只改已存在字段，不新增字段；回报旧值 → 新值。

## 三、删除（破坏性）

1. **定位**：同修改——有 ID 直接用，无则查询且**唯一**。
2. **执行**：`--record <记录ID> --delete`；回报被删标识，删后不自动重查。

## 禁止

- 不写只读字段；不凭记忆填记录 ID，候选来自查询。
- 不批量改 / 删；一次只操作一条。
- 不删表、不改表结构、不新建；只操作登记的表。
- 同一条改 / 删不重复提交；查询可重试。
- 禁伪造 `AskUserQuestion` 或工具名 / 参数；禁绕过连接器直连 REST、生成 HTML、启本地 HTTP 代理、浏览器参与写入。
- 禁心算数值 / 单号、手拼日期；禁在脚本或输出写入真实令牌、地址或凭据。
- 令牌存连接器，不进对话 / 命令行 / 日志；完整规范见 README「关于工具与连接器」。

## 示例

- 「查客户里状态为 X 的记录」→ `--table 客户 --where "S.状态=X"` → 回报列表。
- 「把客户里 XX 的字段改成 YY」→ 定位唯一 → `--set` → 回报。
- 「删掉客户里 XX 这条」→ 定位唯一 → `--delete` → 回报。

## 资源

- `references/intent-routing.md`：意图 → 技能硬映射（行为路由权威源）。
- `skills/timus-app-schema/references/timus-team-schema.yaml`：表头元数据，表 / 字段 / 可写性唯一来源。
- `skills/timus-app-schema/references/timus-team-data.yaml`：基础数据，本地业务块。
