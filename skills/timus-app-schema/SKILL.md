---
name: timus-app-schema
description: Timus 多维表语义包（通用版）- 把任意 Timus 应用的「表名 / 字段名 / 类型 / 可写性」落成一份可解析的 schema 文件，并规定所有录入与维护技能的采集、确认、数值与日期口径。触发词：查表、查字段、表结构、字段名、team_code、app_name、调用连接器前、生成提交参数、弹窗录入、录入采集规范、直写连接器、数值口径、单号生成、新建专家、适配新应用。
version: 1.0.0
---

# Timus 应用语义包（通用版）

在调用 `timus-runtime` 连接器前，把业务词确定性翻译成连接器工具参数。语义包**不是 MCP 的运行时入参**：连接器工具只接受 `app_name` / `table_name` / `fields`，本 Skill 负责在专家侧完成映射。

本 Skill 是**领域无关的**：不绑定任何具体业务，只绑定「Timus 应用」这一层。换应用 = 换 `references/timus-team-schema.yaml` 的内容，代码与契约不动。

本 Skill 同时是**所有录入 / 维护技能采集方式与直写流程的唯一权威源**。通用参数语义、响应结构、错误处理、安全边界见 `references/write-contract.md`；意图→技能映射见 `references/intent-routing.md`。

## 何时使用

- 需要确认某张表有哪些字段、字段是什么类型、是否可写；
- 准备调用 `apaas_add_record` / `apaas_edit_record` / `apaas_page_records` / `apaas_delete_record`，需要准确的 `app_name`、`table_name`、`fields[].name`；
- 用户说业务词（如「客户」「订单」「里程碑」），需要落到系统字段名；
- 上游技能（`record-create-form` / `record-maintenance`）通过弹窗与对话采集信息、调用连接器直写之前；
- 数值（数量 / 金额 / 点数）或日期拿不准时，用 `scripts/point_util.py` / `scripts/date_util.py` 出数；
- **新建一个基于本模板的专家时**，按 `references/timus-team-schema.yaml` 的模板填写目标应用。

## 唯一字段来源

`references/timus-team-schema.yaml` 是专家包内**唯一**的表名与字段名清单。它是**通用模板**：首次使用前必须用目标应用的真实 `team_code` / 表名 / 字段名填充；不允许凭记忆或界面标题拼字段名。

| 语义包元素 | 映射到连接器 | 规则 |
| --- | --- | --- |
| `team_code` | `app_name` | 应用编码，所有工具共用 |
| `tables` 下的表单名 | `table_name` | 必须与平台配置的表名一致 |
| `tables` 下的表单标识（`tbl...`） | 不映射 | 仅作元数据与追溯，禁止写入任何工具参数 |
| `fields` 下的系统字段名 | `fields[].name` | 唯一允许传给接口的字段标识 |
| `type_policy` | 可写性 | `AutoNumber` / `CreatedTime` / `Lookup` / `User` / `Formula` 只读；`Text` / `Number` / `SingleSelect` / `DateTime` 可写 |

- 系统字段名逐字使用，包括前缀与大小写差异。**同一应用内不同表的前缀可能不同**（如某表 `创建时间` 无前缀、另一表 `S.创建时间`），这是平台实况，照 yaml 抄，不统一、不纠正。
- `AutoNumber`、`CreatedTime`、`Formula` 由服务端生成 / 计算，`Lookup`、`User` 需要特定值结构，均不得出现在写操作的 `fields` 中。
- 字段不在语义包中时，向用户索取准确字段名，不要用近义词、界面标题或历史别名替代。
- 语义包不含自定义字段名；历史别名与 `A.` 前缀名称不属于接口字段，禁止传入。

## 声明方式

官方单 Agent 专家规范中 `plugin.json` 没有 `schema` 或 `references` 字段，因此语义包作为本 Skill 的 `references/` 文件存在，由 `plugin.json` 的 `skills` 路径数组登记本 Skill；Agent frontmatter 不声明 `skills` 字段，宿主按插件登记按需加载。这样走渐进式加载，不占常驻上下文。

## 脚本（跨专家包共用同一份代码）

`scripts/` 下四个脚本在 `project-management-expert` / `customer-management-expert` / `general-timus-expert` 三个包中**字节级一致**，由各包 `tests/scripts.lock` 哈希锁定。改脚本必须全部同步并刷新各包 lock。

| 脚本 | 职责 |
| --- | --- |
| `resolve_schema.py` | 字段 / 可写性查询与参数生成（降级工具） |
| `schema_lib.py` | 受限 YAML 解析 + **类型层**校验（只判断值能否按该类型写入） |
| `point_util.py` | **业务数值口径**：`normalize` 两位小数归一化、`split` 总量按权重拆分、`next-pair` / `next-batch` 单号派生 |
| `date_util.py` | **日期口径**：`options` 候选、`dates` / `batch` 第 N 天换算、`single` 今日→目标日换算，输出 `YYYY-MM-DD HH:mm:ss` |

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

所有脚本 `exit 2` + stderr 中文原因报错：未知表 / 未知字段 / 只读字段 / 重复 `--set` / 类型不匹配 / 数值非正 / 拆分后不足 0.01 / 日期非法。stdout 只输出 JSON。

## 录入与维护技能的通用规范（所有技能必须遵循）

技能不生成 HTML 页面、不启动本地代理、浏览器不参与。信息在对话中采集，写入由助手直接调用 `timus-runtime` 连接器完成。各技能 `SKILL.md` 只写自身差异。

### 信息类别与采集渠道

| 信息类别 | 采集渠道 | 校验 / 生成位置 |
| --- | --- | --- |
| 固定值（类型枚举、固定里程碑等） | 技能预置，不向用户采集；有互斥分支时用 `AskUserQuestion` 单选确认 | 技能内固定，禁止用户改写 |
| 平台关联值（外键 ID、候选实体） | 先 `apaas_page_records` 查询候选，再用 `AskUserQuestion` 单选 | 助手核对系统原值，禁止凭记忆填写 ID |
| 自由文本（名称、联系方式、备注等） | 普通对话提问 | 助手侧 trim、长度校验 |
| 数值（数量 / 金额 / 点数 / 估点） | 首句解析或弹窗单选常用值 | **一律经 `point_util.py normalize`**；正数、两位小数；批量总量用 `split` |
| 单号（流水号 / 订单号） | 不采集 | `point_util.py next-pair`（一对）或 `next-batch`（多条） |
| 日期 | `date_util.py options` 生成候选 → 弹窗选择 | 写入值一律取脚本的 `*_datetime`，不心算星期、不手拼格式 |
| 写入确认 | 正文清单（表格）+ `AskUserQuestion` 精简确认框（必经） | 见下「写入确认两步法」 |

### AskUserQuestion 契约

`AskUserQuestion` 是宿主沟通层内置工具，本专家不声明 `tools`；在技能流程中指示助手按宿主可用能力调用，不得伪造工具名或参数。

- 每次 1–4 题，每题 2–4 个选项；`header` ≤ 12 字符，`label` 为 1–5 个词并附 `description`。
- 推荐项放首位并在 `label` 标注「（推荐）」；互不依赖的选择题合并进**同一次**调用，不做多轮逐项弹窗。
- 弹窗只承载选择题与动作确认，不承载长文本与字段明细。
- 开放输入由 UI 自带的「其他」承接，**不手工添加「自定义 / 其他」选项**（会重复 UI）。

### 写入确认两步法（唯一版本，任何技能不得另立口径）

1. **正文清单**：先在助手消息正文输出「一句话 + 表格」，逐条编号，必填项按实际值完整展示，空值写 `—`；敏感字段脱敏。字段明细**只在此处呈现**。
2. **精简弹窗**：正文清单之后立即弹一次 `AskUserQuestion`，`question` 只写 `即将写入「<表名>」表，共 N 条，确认提交？`（不重复字段值），选项固定 `确认提交`（首位、「（推荐）」）/ `取消 / 返回修改`。

判定与约束：

- 仅当用户选 `确认提交` 才写入；选取消或关闭弹窗即终止，调整后重新走两步。
- 即使用户说「直接记 / 不用确认 / 别问了」也不得省略；不得用弹窗塞字段替代正文清单，也不得用文字「请回复确认」替代弹窗。
- 弹窗后本批参数锁定；改 / 增 / 删任一条都要重出清单、重弹窗。
- **降级**：仅当宿主确实无弹窗能力时，正文清单照常输出并请用户文字回复「确认」，收到明确「确认」才写入；降级同样不得省略确认。

### 候选查询规则

- 候选必须先经 `apaas_page_records` 查询，不允许手写、凭记忆填写任何关联 ID。
- 候选超过 4 个时，取最相关前 4 项 +「查看更多」分屏翻页，保证全部候选可逐屏选到；不得只给前 4 条就断定「没有更多」。
- 是否需要状态过滤，由各技能显式声明；**未声明即不加过滤**（默认全量），避免默认值与平台流程打架。
- 选项在会话内复用，不重复查询；用户要求刷新时才重新查询。

### 字段到采集渠道映射（通用骨架）

具体映射由各技能 `SKILL.md` 的字段表给出，本节只定**判定顺序**：

1. 字段类型是 `Lookup` / `AutoNumber` / `CreatedTime` / `User` / `Formula` → 不采集、不写入。
2. 字段在本技能「固定值」清单里 → 用预置值，不问用户。
3. 字段是外键 ID（`S.<实体>ID` 形式，且类型为 `Text`）→ 查候选 + 弹窗，或由上游选择继承。
4. 字段是 `Number` → 走 `point_util`。
5. 字段是 `DateTime` → 走 `date_util`。
6. 其余 → 对话自由文本。

### 直写流程

1. 按上述顺序采集并校验全部字段；缺项先补齐，不臆造。
2. 直接构造 `apaas_add_record` 的 `arguments`；字段不确定或写入报错时才用 `resolve_schema.py` 复核。
3. 数值、单号、日期统一由脚本出数，不心算、不手拼。
4. 走「写入确认两步法」，只有 `确认提交` 才调用连接器。
5. 逐条写入、部分失败处理、错误码与安全边界一律按 `references/write-contract.md`。

## 禁止事项

- 不把整个语义包、表单标识或自定义字段名作为工具参数传入连接器。
- 不猜测字段名；不使用语义包之外的工具名。
- 不修改 `timus-runtime` 连接器、不绕过连接器直接调用 REST 接口；不生成 HTML、不启动本地 HTTP 代理、不让浏览器参与写入。
- 不伪造 `AskUserQuestion` 或连接器工具名、参数；弹窗不可用时降级为文字，不中断专家。
- 不凭记忆填写任何关联 ID；不心算数值与单号、不手拼日期格式。
- 不在语义包、脚本或输出中写入真实令牌、服务地址或其它凭据。
- 不修改 `scripts/` 下四个脚本的接口（跨包哈希锁定）；新增能力走新脚本。

## 作为「专家包模板」使用

新建一个 Timus 领域专家时，按下列顺序落地（细节见包内 `README.md` 的「后续专家规范」）：

1. 复制本包为 `<new-expert>/1.0.0`，改 `plugin.json` 的 `name` / `plugin` / `agentName` / `displayName` / `categoryId` / `description`。
2. 用目标应用的字段集替换 `references/timus-team-schema.yaml` 的 `team_code` / `tables` / `fields`，`type_policy` 保留全集。
3. 写 `agents/<new-expert>.md`：人设 + 核心能力 + 路由原则 + 能力边界，**不写字段表、不写流程细则**。
4. 领域专属能力才新建 `<实体>-create-form`；通用增删改查直接复用 `record-create-form` / `record-maintenance`，不为每个实体复制一份。
5. 改 `tests/pkg_config.py` 的 `APP_CODE` / `REQUIRED_TABLES` / `FORM_SKILLS`，跑 `python3 tests/smoke_test.py --update-lock`，再跑三件套到全绿。

## 资源

- `references/timus-team-schema.yaml`：通用模板（填写后成为该应用的唯一字段来源）。
- `references/write-contract.md`：参数语义 / 响应结构 / 错误处理 / 安全边界（跨包同一份）。
- `references/intent-routing.md`：意图 → 技能硬映射（通用版）。
- `scripts/`：四脚本，跨包字节级一致、哈希锁定。
- 解析限制：`schema_lib.py` 按行首缩进读取键值，并把行内第一个 `#` 视为注释起点；值中不能包含井号字面量，也不支持列表语法、引号包裹的井号或跨行结构。
