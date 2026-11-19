# 通用数据专家（general-timus-expert / Carly 卡莉）

面向 WorkBuddy 专家市场的单个 Agent 类型专家，也是 **Timus 数据类专家的标准基座**：领域无关，按可替换的语义包对任意已登记的 Timus 应用表做建档、查询、修改与删除。

## 定位

两个用途，同一份代码：

1. **直接用**：没有专用领域专家时，用它完成任意表的录入与维护（建 / 查 / 改 / 删）。
2. **当模板**：复制本包得到一个领域专家（如项目管理、客户管理），只需替换语义包数据与 agent 人设，**通用代码与契约不动**。

领域无关的关键设计：表名、字段名、必填项、关联关系、固定值都从**语义包**推导，不在技能文档里硬编码任何业务实体。

## 文档权威源（维护须知）

为避免多份文档描述同一规则造成漂移，本包明确三个唯一权威源；改规则时**只改权威源**，其余文档保持概述并引用：

- **字段定义 / 类型 / 可写性** → `skills/timus-app-schema/references/timus-team-schema.yaml`（模板；真实应用替换为具体值，演示集见 `demo-schema.yaml`）。任何文档不得复述字段清单表格。
- **采集 / 确认 / 数值与日期口径** → `skills/timus-app-schema/SKILL.md` 的「录入与维护技能的通用规范」；各技能 `SKILL.md` 只写自身差异。
- **通用写契约**（参数语义 / 响应 / 错误 / 安全边界）→ `skills/timus-app-schema/references/write-contract.md`。
- **意图路由** → `skills/timus-app-schema/references/intent-routing.md`；`agents/*.md` 只留原则。

> 维护清单（三条命令）：改完文档跑
> `python3 tests/smoke_test.py`（结构 + 禁复述 + 哈希锁）、
> `python3 tests/test_schema_lib.py`、`python3 tests/test_util.py`。
> 改了 `skills/timus-app-schema/scripts/` 下的脚本，需同步到 `project-management-expert` 与
> `customer-management-expert` 两个包，三边各跑一次 `python3 tests/smoke_test.py --update-lock`。

## 目录结构

```
general-timus-expert/
├── .codebuddy-plugin/plugin.json
├── avatars/expert.png                    # 512×512 PNG（≤ 500KB）
├── agents/general-timus-expert.md        # 人设 / 核心能力 / 路由原则 / 能力边界
├── skills/
│   ├── timus-app-schema/                 # 语义包 + 通用契约（唯一权威源）
│   │   ├── SKILL.md                      # 字段来源 + 采集/确认/数值/日期规范 + 模板化指南
│   │   ├── references/
│   │   │   ├── timus-team-schema.yaml    # 通用模板（填写后成唯一字段来源）
│   │   │   ├── demo-schema.yaml          # 演示集，自检与单测跑在它上面
│   │   │   ├── write-contract.md         # 通用写契约（跨包同一份）
│   │   │   └── intent-routing.md         # 意图→技能映射
│   │   └── scripts/                      # 四脚本（跨包字节级一致，哈希锁定）
│   ├── record-create-form/               # 通用建档（任意表，单条/多条）
│   └── record-maintenance/               # 通用维护（任意表，查/改/删）
├── tests/
│   ├── pkg_config.py                     # APP_CODE / SCHEMA_SKILL / SCHEMA_FILE / REQUIRED_TABLES / FORM_SKILLS
│   ├── smoke_test.py                     # 结构 + 禁复述 + 哈希锁
│   ├── test_schema_lib.py                # 类型层单测
│   ├── test_util.py                      # 数值 / 日期口径单测
│   └── scripts.lock                      # 四脚本哈希
└── README.md
```

## 后续专家规范（新增领域专家时照此执行）

本包是**规范源**。新建一个 Timus 领域专家（下称 `<new>`）时按序执行，全部步骤不超过 6 步：

| 步骤 | 动作 | 验收 |
| --- | --- | --- |
| 1 | 整包复制为 `~/.workbuddy/plugins/cache/my-experts/<new>/1.0.0` | 目录骨架与本包一致 |
| 2 | 改 `plugin.json`：`name` / `plugin` / `agentName` / `displayName` / `profession` / `description` / `displayDescription` / `categoryId` / `avatar` / `tags` / `quickPrompts` | `name == plugin == agentName`；`displayDescription.zh` 40–50 字 |
| 3 | 用目标应用的字段集替换 `references/timus-team-schema.yaml` 的 `team_code` / `tables` / `fields`，`type_policy` 保留全集 | `resolve_schema.py --list-tables` 输出目标 `team_code` 与全部表 |
| 4 | 写 `agents/<new>.md`：人设 + 核心能力 + 路由原则 + 能力边界 | **不含**字段表、不含流程细则、不含数值算法（smoke 会拦字段表） |
| 5 | 领域专属能力才新建 `<实体>-create-form`；通用增删改查**直接复用** `record-create-form` / `record-maintenance`，不为每个实体复制一份 | 技能数与业务实体数解耦 |
| 6 | 改 `tests/pkg_config.py` 的 `APP_CODE` / `SCHEMA_FILE` / `REQUIRED_TABLES` / `FORM_SKILLS`，跑 `--update-lock` 后三件套全绿 | `SMOKE OK` + 两个单测 `OK` |

**必须遵守的六条硬约束**：

1. **数据分家、代码合源**：语义包各包一份，互不覆盖；`scripts/` 四脚本 + `write-contract.md` + `tests/` 三件套跨包字节级一致，靠 `scripts.lock` 锁定。
2. **规则单点**：写入确认两步法、采集渠道判定顺序、数值与日期口径只写在语义包 SKILL.md，能力技能只写差异。
3. **禁复述**：`agents/*.md` 与 `README.md` 不得出现「`S.xxx` + 类型」的字段清单表格行；`lowcode-api.md` 不复制响应结构与安全边界（smoke 断言）。
4. **数值与日期不心算**：一律 `point_util.py` / `date_util.py` 出数。
5. **能力边界诚实**：未实现的录入类型明确说明，不以分析结论冒充写入能力。
6. **模板占位符不写入**：语义包未被真实字段填充前，拒绝进入写入流程。

## 与另外两个专家包的关系

`project-management-expert`（`MAINLINE` / 7 表）与 `customer-management-expert`（`03.SPMP.TIMUS` / 6 表）是**按本规范产出的两个实例**，各自的语义包数据独立，共用同一套脚本与契约。三者之间不互为依赖、不共享字段数据。

## 关于工具与连接器

按规范「开发者不可自行添加 tools」：`plugin.json` 与 Agent frontmatter 均未声明 `tools`。所有工具权限由系统统一分配。

本包依赖 **`timus-runtime` 连接器**（`plugin.json` 的 `dependencies.connectors` 声明）：

- 服务地址与访问令牌由用户在 WorkBuddy **连接设置**中填写，注入连接器进程环境变量；凭据不写入本包、不进入对话与日志，本包不含 `.mcp.json`。
- 连接器未连接 / 令牌过期时，不假定外部数据可用、不伪造查询结果。

## 打包与上架

```bash
cd /path/to/your/workspace
zip -r general-timus-expert.zip general-timus-expert -x '*.DS_Store'
unzip -l general-timus-expert.zip | grep -F '.codebuddy-plugin'
```

上架前确认：

1. `author.name` 填署名主体「武汉海辞科技有限公司」，`author.email` 为真实联系邮箱。
2. 头像为 512×512 PNG/JPG 且 ≤ 500KB。
3. `plugin.json` 的 `skills` 声明 3 个技能目录，`dependencies.connectors` 声明 `timus-runtime`。
4. 未添加 `tools` 字段；本包不含任何明文凭据。
5. `python3 tests/smoke_test.py` 全绿（含脚本哈希锁）。

## 开源协议与署名

本项目开源，采用 [Apache License 2.0](LICENSE)。

Copyright 2026 武汉海辞科技有限公司。版权与署名声明见 [NOTICE](NOTICE)；任何再分发请保留 `LICENSE` 与 `NOTICE`。
