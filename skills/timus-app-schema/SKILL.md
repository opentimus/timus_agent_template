---
name: timus-app-schema
description: Timus 多维表语义包（通用版）- 两类 schema：表头元数据（表名 / 字段名 / 类型 / 可写性）与基础数据（本地业务块）。规定字段查询、本地优先取值、采集、确认、数值与日期口径。触发词：查表、查字段、表结构、字段名、team_code、app_name、调用连接器前、生成提交参数、本地数据、基础数据、业务块、弹窗录入、录入采集规范、直写连接器、数值口径、单号生成、新建专家、适配新应用。
version: 1.0.0
---

# Timus 应用语义包（通用版）

调用 `timus-runtime` 前，把业务词确定翻译成工具参数。语义包**不是 MCP 运行时入参**：连接器只接受 `app_name` / `table_name` / `fields`，映射在本 Skill 完成。

领域无关：换应用 = 换 `references/` 下的两类 schema，代码与契约不动。

本 Skill 是**采集方式与直写流程唯一权威源**。参数语义 / 响应 / 错误 / 安全见 `references/write-contract.md`；意图路由见 `references/intent-routing.md`。

## 两类 schema

| 类型 | 模板 | 演示 | 用途 |
| --- | --- | --- | --- |
| 表头元数据 | `references/timus-team-schema.yaml` | `demo-schema.yaml` | 查指定字段：表名 / 字段名 / 类型 / 可写性；生成写入参数 |
| 基础数据 | `references/timus-team-data.yaml` | `demo-data.yaml` | 获取目标业务块的记录值，本地命中即止，避免远程调用 |

两类须成对维护：`team_code` 一致，基础数据的表名与字段名逐字照抄表头元数据，禁止自定义字段。表头元数据为**唯一字段来源**；基础数据为**本地取值来源**。

## 何时使用

- 确认表、字段、类型、可写性 → 表头元数据。
- 取业务块记录值（候选、关联 ID、历史值）→ 先查基础数据，本地未命中再 `apaas_page_records`。
- 调用 `apaas_edit_record` / `apaas_page_records` / `apaas_delete_record` 前取准确 `app_name` / `table_name` / `fields[].name`。
- 业务词（如「客户」「订单」「里程碑」）→ 系统字段名。
- 数值或日期拿不准：用 `scripts/point_util.py` / `scripts/date_util.py`。
- 新建基于本模板的专家：按两类模板填目标应用。

## 表头元数据

`references/timus-team-schema.yaml` 是包内**唯一**表名 / 字段名清单，为**通用模板**；首次使用须填真实 `team_code` / 表名 / 字段名，禁凭记忆或界面标题拼字段。

| 元素 | 映射到连接器 | 规则 |
| --- | --- | --- |
| `team_code` | `app_name` | 应用编码，所有工具共用 |
| `tables` 下表单名 | `table_name` | 与平台配置一致 |
| `tables` 下表单标识（`tbl...`） | 不映射 | 仅元数据 / 追溯，禁入参数 |
| `fields` 下系统字段名 | `fields[].name` | 唯一允许的字段标识 |
| `type_policy` | 可写性 | 只读：`AutoNumber` / `CreatedTime` / `Lookup` / `User` / `Formula`；可写：`Text` / `Number` / `SingleSelect` / `DateTime` |

- 字段名逐字使用，含前缀与大小写；同应用不同表前缀可不同，照 yaml 抄，不统一。
- 只读类型及需特定值结构的 `Lookup` / `User` 禁入写 `fields`。
- 字段缺失时索取准确名，不用近义词 / 界面标题 / 历史别名。
- 包内无自定义字段名；历史别名与 `A.` 前缀禁传。

## 基础数据（本地业务块）

`references/timus-team-data.yaml` 存本地业务记录；首次使用须填真实 `team_code` 与记录。结构：`data` → 表名 → 记录 ID → 字段名: 值。记录 ID 仅本地追溯，禁入连接器参数。

基础数据的查 / 改 / 删统一由 `timus-app-maintenance` 技能的 `data_tool.py` 执行，本技能只定义 schema，不持有数据操作脚本。

- 本地查询先于远程：命中即直接用，避免 `apaas_page_records`；未命中再走远程。
- 字段名须在表头元数据中存在，否则 `exit 2`。
- 本地数据只作取值来源，不伪造远程结果；远程返回的新记录按需落盘后再复用。

## 声明方式

宿主按 `plugin.json` 的 `skills` 路径渐进加载本 Skill；`plugin.json` 无 `schema` / `references` 字段，Agent frontmatter 不声明 `skills`。语义包放 `references/`，不占常驻上下文。

## 脚本（跨专家包共用同一份代码）

四脚本在三包**字节级一致**；改动须全同步。基础数据的查 / 改 / 删脚本在 `timus-app-maintenance` 技能。

| 脚本 | 职责 |
| --- | --- |
| `resolve_schema.py` | 表头元数据查询与参数生成（降级） |
| `schema_lib.py` | 受限 YAML 解析 + 类型层校验 |
| `point_util.py` | 数值口径：`normalize` 两位小数、`split` 按权重拆分、`next-pair` / `next-batch` 单号 |
| `date_util.py` | 日期口径：`options` 候选、`dates` / `batch` 第 N 天、`single` 今日→目标日，输出 `YYYY-MM-DD HH:mm:ss` |

```bash
python3 <skill-dir>/scripts/resolve_schema.py --list-tables
python3 <skill-dir>/scripts/resolve_schema.py --list-fields --table <表单名>
python3 <skill-dir>/scripts/resolve_schema.py --table <表单名> --set <字段>=<值>
python3 <skill-dir>/scripts/point_util.py normalize 99.5
python3 <skill-dir>/scripts/point_util.py split --total 6 --weight 3 --weight 2 --weight 1
python3 <skill-dir>/scripts/point_util.py next-pair --prefix TIN
python3 <skill-dir>/scripts/point_util.py next-batch --prefix TPAY --count 3
python3 <skill-dir>/scripts/date_util.py options
python3 <skill-dir>/scripts/date_util.py batch --start-date 2026-11-20 --task "任务A|1|2"
python3 <skill-dir>/scripts/date_util.py single --end-date 2026-11-30
```

脚本 `exit 2` + stderr 中文原因；stdout 仅 JSON。

## 录入与维护技能的通用规范（所有技能必须遵循）

不生成 HTML、不启本地代理、浏览器不参与；对话采集，助手直调连接器。技能 `SKILL.md` 只写自身差异。

### 信息类别与采集渠道

| 信息类别 | 采集渠道 | 校验 / 生成位置 |
| --- | --- | --- |
| 固定值（类型枚举等） | 技能预置；有互斥分支用 `AskUserQuestion` 单选 | 禁用户改写 |
| 平台关联值（外键 ID、候选） | 先查基础数据，未命中再 `apaas_page_records` 查候选 → `AskUserQuestion` 单选 | 核对原值，禁凭记忆填 ID |
| 自由文本 | 对话提问 | trim + 长度校验 |
| 数值 | 首句解析 / 弹窗单选常用值 | 一律 `point_util.py normalize`；正数、两位小数；总量 `split` |
| 单号 | 不采集 | `point_util.py next-pair` / `next-batch` |
| 日期 | `date_util.py options` 候选 → 弹窗选择 | 写入取脚本 `*_datetime`，不心算星期、不手拼格式 |
| 写入确认 | 正文清单（表格）+ `AskUserQuestion` 精简确认框（必经） | 见下 |

### AskUserQuestion 契约

宿主内置工具，本专家不声明 `tools`；按宿主可用能力调用，禁伪造工具名 / 参数。

- 每次 1–4 题，每题 2–4 选项；`header` ≤12 字符，`label` 1–5 词并附 `description`。
- 推荐项首位并标「（推荐）」；互不依赖的选择合并**同一次**调用。
- 弹窗只承载选择题与动作确认，不承载长文本与字段明细。
- 开放输入由 UI「其他」承接，**不手工添加「自定义 / 其他」**。

### 写入确认两步法（唯一版本，任何技能不得另立口径）

1. **正文清单**：正文「一句话 + 表格」，逐条编号；必填项完整展示，空值 `—`，敏感字段脱敏；字段明细**仅此处**。
2. **精简弹窗**：紧接弹一次 `AskUserQuestion`，`question` 仅 `即将写入「<表名>」表，共 N 条，确认提交？`（不重复字段值）；选项固定 `确认提交`（首位、「（推荐）」）/ `取消 / 返回修改`。

判定与约束：

- 仅 `确认提交` 才写入；取消 / 关闭即终止，调整后重走两步。
- 用户说「直接记 / 不用确认 / 别问了」也不得省略；禁弹窗塞字段、禁文字「请回复确认」替代弹窗。
- 弹窗后本批参数锁定；增 / 改任一条都重出清单、重弹窗。
- **降级**：仅当宿主无弹窗能力，正文清单照常并请用户文字回复「确认」，收到明确「确认」才写入。

### 候选查询规则

- 先查本地基础数据；未命中再 `apaas_page_records` 查候选；禁手写 / 凭记忆填关联 ID。
- 超过 4 项：取前 4 +「查看更多」分屏翻页，保证全部可逐屏选到。
- 状态过滤由技能显式声明；**未声明即不加**（默认全量）。
- 选项会话内复用；用户要求刷新才重查。

### 字段到采集渠道映射（通用骨架）

具体字段表由技能 `SKILL.md` 给出，本节只定**判定顺序**：

1. `Lookup` / `AutoNumber` / `CreatedTime` / `User` / `Formula` → 不采集、不写入。
2. 在本技能「固定值」清单 → 预置值，不问。
3. 外键 ID（`S.<实体>ID` 且 `Text`）→ 先查本地基础数据 / 远程候选 + 弹窗，或上游继承。
4. `Number` → `point_util`。
5. `DateTime` → `date_util`。
6. 其余 → 对话自由文本。

### 直写流程

1. 按上述顺序采集校验；业务块取值先查本地基础数据，缺项补齐，不臆造。
2. 直接构造连接器参数；字段不确定或报错才用 `resolve_schema.py` 复核。
3. 数值、日期由脚本出数，不心算、不手拼。
4. 走「写入确认两步法」，仅 `确认提交` 才调连接器。
5. 写入、部分失败、错误码与安全边界按 `references/write-contract.md`。

## 禁止事项

- 两类 schema 整体、表单标识、自定义字段名禁入连接器参数。
- 禁猜字段名；禁用语义包外的工具名。
- 禁改连接器、绕过连接器直调 REST、生成 HTML、启本地 HTTP 代理、浏览器参与写入。
- 禁伪造 `AskUserQuestion` 或连接器工具名 / 参数；弹窗不可用时降级文字，不中断。
- 禁凭记忆填关联 ID；禁心算数值 / 单号、手拼日期。
- 禁在语义包、脚本或输出写入真实令牌、地址或凭据。
- 禁改 `scripts/` 四脚本接口；新能力走新脚本。

## 作为「专家包模板」使用

新建领域专家按序（细节见 README「后续专家规范」）：

1. 复制本包为 `<new-expert>/1.0.0`，改 `plugin.json` 的 `name` / `plugin` / `agentName` / `displayName` / `categoryId` / `description`。
2. 用目标应用字段替换表头元数据 `references/timus-team-schema.yaml` 的 `team_code` / `tables` / `fields`，`type_policy` 保留全集；同步替换基础数据 `references/timus-team-data.yaml` 的 `team_code` 与业务块。
3. 写 `agents/<new-expert>.md`：人设 + 核心能力 + 路由原则 + 能力边界，无字段表 / 流程细则。
4. 领域专属能力才建专属技能；基础数据查 / 改 / 删复用 `timus-app-maintenance`。
5. 换语义包后确认脚本可用；跨包脚本与契约保持字节级一致。

## 资源

- `references/timus-team-schema.yaml`：表头元数据通用模板，填后为唯一字段来源。
- `references/timus-team-data.yaml`：基础数据通用模板，填后为本地取值来源。
- `references/demo-schema.yaml` / `demo-data.yaml`：演示集。
- `references/write-contract.md`：参数 / 响应 / 错误 / 安全（跨包同一份）。
- `references/intent-routing.md`：意图 → 技能硬映射。
- `scripts/`：四脚本，跨包字节级一致。
- 解析限制：`schema_lib.py` 按行首缩进读键值；行内第一个 `#` 起为注释，值禁含 `#`，不支持列表、引号包裹的井号或跨行结构。
