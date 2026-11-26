---
name: timus-app-maintenance
description: Timus 数据记录维护 — 行为层唯一权威源：意图路由、采集渠道与查 / 改 / 删。对本地基础数据操作，字段以 timus-app-schema 的表头元数据为准。触发词：查记录、查数据、搜、列出、详情、看一下、改记录、更新记录、修正字段、删记录、删除记录、移除。
version: 1.0.0
agent_created: true
---

# 数据记录维护（查 / 改 / 删）

对本地基础数据做查 / 改 / 删，表名与字段名取自 `timus-app-schema` 两类 schema，不绑定具体实体。本 Skill 是**行为层唯一权威源**：意图路由见 `references/intent-routing.md`。不生成 HTML、不启本地代理、不让浏览器参与、不直连 REST；对话采集，助手直调脚本。

## 意图与定位

- 动作族与逐关键词映射见 `references/intent-routing.md`，命中即执行、不确认动作类型；含糊（如「处理一下这条记录」）先弹 `AskUserQuestion` 选动作。
- 表名按 `intent-routing.md`「表定位规则」匹配表头元数据 `tables`：完全同名 → 子串唯一命中 → 多张弹窗选 → 零命中列可用表请用户指定，不造表名。
- 字段名逐字用系统字段名，禁历史别名 / 界面标题；可写性以 `type_policy` 为准，只读拒写、未知字段拒绝；记录 ID 来自本地基础数据，禁凭记忆填。

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
