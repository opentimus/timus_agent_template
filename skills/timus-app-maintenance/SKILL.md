---
name: timus-app-maintenance
description: Timus 数据查改删与语义包 — 记录查询、字段更新、记录删除、本地数据维护。
version: 1.0.0
agent_created: true
---

# 数据记录维护与语义包（查 / 改 / 删）

语义包为单文件 `references/timus-team.yaml`，含表头元数据与本地记录；换应用只换该文件，代码与契约不动。动作族与定位见 `references/intent-routing.md`，本文件不重复。对话采集，助手直调脚本；不生成 HTML、不启代理、不让浏览器参与、不直连 REST。

## 语义包结构

- 层级：`apps` → 应用名（即 `app_name`）→ `tables`（表名 → `tbl...`）+ `fields`（表 → 字段: 类型@策略）+ `records`（表 → 记录 ID → 字段: 值）。
- `tables` / `fields` / `records` 归属当前应用，`fields` / `records` 再归属当前表；`tbl...` 仅追溯，禁入参数。
- 字段名是平台内部标识（`S.客户`），逐字使用；未登记时按 `timus-runtime` 样本记录法取 `payloadFieldList[].name` 核对后落盘。
- 字段写作 `类型@策略`；策略省略取 `type_policy` 默认（`AutoNumber` / `CreatedTime` / `Lookup` / `Formula` 只读，其余可写），可逐字段覆盖。`User` 值须为 `open_id`（取自应用 `members` 快照），禁姓名 / 邮箱。
- 占位符（`TODO*` / `<...>`）禁写入，先索取落盘。
- 取值先本地后远程：本地命中直接用；未命中再走 `timus-runtime`；远程新记录按需落盘复用，不伪造远程结果。

## 采集

| 信息 | 渠道 | 处理 |
| --- | --- | --- |
| 固定值 | 技能预置，互斥用 `AskUserQuestion` | 禁用户改写 |
| 外键 ID / 候选 | 先本地，未命中 `apaas_page_records`，弹窗单选 | 禁凭记忆填 ID |
| 自由文本 | 对话提问 | trim + 长度校验 |
| 数值 | 首句 / 弹窗 | `point_util.py normalize` 两位小数 |
| 单号 | 不采集 | `point_util.py next-pair` / `next-batch` |
| 日期 | `date_util.py options` → 弹窗 | 写入取 `*_datetime` |

`AskUserQuestion` 为宿主内置工具，本专家不声明 `tools`。每次 1–4 题、每题 2–4 选项；`header` ≤12 字符，推荐项首位标「（推荐）」；只承载选择题与动作选择，开放输入由 UI「其他」承接。候选查询超 4 项取前 4 +「查看更多」，状态过滤仅技能显式声明时加，选项会话内复用。

## 脚本

| 脚本 | 职责 |
| --- | --- |
| `pack_lib.py` | 语义包解析、应用 / 表 / 字段解析与可写性查询 |
| `data_tool.py` | 按应用 + 表查 / 改 / 删，原地改写单文件 YAML |
| `point_util.py` | 数值：`normalize` / `split` / `next-pair` / `next-batch` |
| `date_util.py` | 日期：`options` / `batch` / `single`，输出 `YYYY-MM-DD HH:mm:ss` |

参数见 `<skill-dir>/scripts/<脚本> -h`。`stdout` 仅 JSON，错误走 `stderr` + `exit 2`。禁改脚本接口（新能力走新脚本）。解析限制：2 空格缩进，无列表 / 锚点；`members` 块跳过。

## 操作

- 查：`--where` 可重复（AND），`--fields` 可多值；直接执行，回报应用、表、条数与关键字段。
- 改 / 删：有 ID 直接用，无则查询且必须唯一（0 条报未找到，多条补条件或给 ID）；一次一条，只改已存在字段。改回报旧值 → 新值，删后不自动重查。
- 追加走 `timus-app-add`，同样须传 `--app`。
- 关键字段取首个可用：`Text` 且名含「名称 / 标题 / 单号 / 编号」→ 首个 `Text` → 记录 ID。
- 禁：只读字段、跨应用、凭记忆填 ID、批量改 / 删、删表 / 改结构、重复提交同一条改 / 删、占位应用名写入。
