---
name: timus-app-maintenance
description: Timus 数据记录维护与语义包 — 行为层唯一权威源：意图路由、采集渠道、表/字段/类型/可写性、本地业务块与查改删。触发词：查记录、查数据、搜、列出、详情、看一下、改记录、更新记录、修正字段、删记录、删除记录、移除、查表、查字段、表结构、字段名、team_code、app_name、本地数据、基础数据、业务块、数值口径、单号生成、适配新应用。
version: 1.0.0
agent_created: true
---

# 数据记录维护与语义包（查 / 改 / 删）

对本地基础数据做查 / 改 / 删，不绑定具体实体。本 Skill 是**行为层唯一权威源**：意图路由见 `references/intent-routing.md`。不生成 HTML、不启本地代理、不让浏览器参与、不直连 REST；对话采集，助手直调脚本。

## 语义包

换应用 = 换 `references/` 下两份 YAML，代码与契约不动。语义包不是 MCP 入参：连接器只接受 `app_name` / `table_name` / `fields`，映射在此完成。

| 文件 | 用途 |
| --- | --- |
| `references/timus-team-schema.yaml` | 表名 / 字段名 / 类型 / 可写性；**唯一字段来源** |
| `references/timus-team-data.yaml` | 本地业务块记录值；**本地取值来源** |

两份须成对维护：`team_code` 一致，基础数据的表名与字段名逐字照抄表头元数据，禁自定义字段。表头元数据为通用模板，首次使用填真实 `team_code` / 表名 / 字段名；表单标识 `tbl...` 仅追溯、禁入参数。基础数据结构：`data` → 表名 → 记录 ID → 字段名: 值；另有 `synced_at` / `source` / `members` 快照（成员字段下划线命名）。`members[].open_id` 即 `User` 写入值，`record_id` 仅本地追溯。

字段名是平台内部标识（`S.客户`），逐字使用（含前缀与大小写，同应用不同表前缀可不同），禁历史别名 / 界面标题 / 凭记忆拼。**本地未登记时**，才按 `timus-runtime` 技能的样本记录法（`apaas_page_records` 读一条取 `payloadFieldList[].name`）获取真实字段名，核对后落盘到表头元数据再写入。

映射：`team_code` → `app_name`；`tables` 下表单名 → `table_name`；`fields` 下系统字段名 → `fields[].name`；`type_policy` 定可写性——只读：`AutoNumber` / `CreatedTime` / `Lookup` / `Formula`，可写：`Text` / `Number` / `SingleSelect` / `DateTime` / `User`；`User` 值必须是 `open_id`（非姓名 / 别名 / 邮箱）。

取值先本地后远程：本地命中直接用，避免远程调用；未命中再走连接器，远程新记录按需落盘复用；本地数据不伪造远程结果。

## 意图与定位

- 动作族与逐关键词映射见 `references/intent-routing.md`，命中即执行、不确认动作类型；含糊（如「处理一下这条记录」）先弹 `AskUserQuestion` 选动作。
- 表名按 `intent-routing.md`「表定位规则」匹配表头元数据 `tables`：完全同名 → 子串唯一命中 → 多张弹窗选 → 零命中列可用表请用户指定，不造表名。
- 可写性以 `type_policy` 为准，只读拒写、未知字段拒绝；记录 ID 来自本地基础数据，禁凭记忆填。

## 采集

| 信息类别 | 渠道 | 校验 / 生成 |
| --- | --- | --- |
| 固定值（类型枚举等） | 技能预置；互斥分支用 `AskUserQuestion` 单选 | 禁用户改写 |
| 平台关联值（外键 ID / 候选） | 先查基础数据，未命中再 `apaas_page_records`，`AskUserQuestion` 单选 | 核对原值，禁凭记忆填 ID |
| 自由文本 | 对话提问 | trim + 长度校验 |
| 数值 | 首句解析 / 弹窗常用值 | `point_util.py normalize`，正数两位小数；总量 `split` |
| 单号 | 不采集 | `point_util.py next-pair` / `next-batch` |
| 日期 | `date_util.py options` 候选 → 弹窗选 | 写入取 `*_datetime`，不心算 / 手拼 |

字段到渠道按序判定：①`Lookup` / `AutoNumber` / `CreatedTime` / `Formula` 不采集不写入，`User` 可写但须传 `open_id`；②固定值清单 → 预置不问；③外键 ID（`S.<实体>ID` 且 `Text`）→ 查本地 / 远程候选 + 弹窗，或上游继承；④`Number` → `point_util`；⑤`DateTime` → `date_util`；⑥其余自由文本。

`AskUserQuestion`：宿主内置工具，本专家不声明 `tools`，禁伪造工具名 / 参数。每次 1–4 题、每题 2–4 选项；`header` ≤12 字符，`label` 1–5 词并附 `description`；推荐项首位标「（推荐）」，互不依赖的选择同一次调用；只承载选择题与动作选择，开放输入由 UI「其他」承接，不手工加「自定义 / 其他」。

候选查询：先本地基础数据，未命中再 `apaas_page_records`；超 4 项取前 4 +「查看更多」分屏；状态过滤仅技能显式声明时加；选项会话内复用，用户要求刷新才重查。

## 脚本（本技能 scripts/，单点实现）

| 脚本 | 职责 |
| --- | --- |
| `schema_lib.py` | 受限 YAML 解析 + 字段可写性查询 |
| `point_util.py` | 数值：`normalize` 两位小数、`split` 按权重拆分、`next-pair` / `next-batch` 单号 |
| `date_util.py` | 日期：`options` 候选、`batch` 第 N 天、`single` 今日→目标日，输出 `YYYY-MM-DD HH:mm:ss` |

```bash
python3 <skill-dir>/scripts/point_util.py normalize 99.5
python3 <skill-dir>/scripts/point_util.py split --total 6 --weight 3 --weight 2 --weight 1
python3 <skill-dir>/scripts/point_util.py next-pair --prefix TIN
python3 <skill-dir>/scripts/point_util.py next-batch --prefix TPAY --count 3
python3 <skill-dir>/scripts/date_util.py options
python3 <skill-dir>/scripts/date_util.py batch --start-date 2026-11-20 --task "任务A|1|2"
python3 <skill-dir>/scripts/date_util.py single --end-date 2026-11-30
```

`exit 2` + stderr 中文原因；stdout 仅 JSON。禁改三脚本接口（新能力走新脚本）。解析限制：按行首缩进读键值，不支持列表与跨行结构。

## 关键字段

复述定位用「关键字段值 + 记录 ID」，避免同名误改 / 误删。关键字段取第一个可用者：①首个 `Text` 且名含「名称 / 标题 / 单号 / 编号」；②否则首个 `Text`；③都没有用记录 ID。

## 操作

```bash
python3 <skill-dir>/scripts/data_tool.py --list-tables
python3 <skill-dir>/scripts/data_tool.py --table <表名> --where "S.字段=值" --fields "S.字段A" "S.字段B"
python3 <skill-dir>/scripts/data_tool.py --table <表名> --record <ID> --set "字段=值"
python3 <skill-dir>/scripts/data_tool.py --table <表名> --record <ID> --delete
```

- **查**：`--where` 可重复（AND），`--fields` 可多值；直接执行，回报条数与关键字段，无匹配如实说明；统计 / 对账在结果上完成。
- **改 / 删**：先定位——有 ID 直接用，无则查询且**必须唯一**（0 条报未找到，多条请补条件或给 ID）；一次只改一条，只改已存在字段、不新增；改回报旧值 → 新值，删回报被删标识且删后不自动重查。

## 禁止

不写只读字段；不凭记忆填 ID；不批量改 / 删、不删表 / 改结构 / 新建；同一条改 / 删不重复提交（查询可重试）；不生成 HTML、不启代理、不让浏览器参与写入、不直连 REST。
