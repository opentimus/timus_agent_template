# 通用数据专家（general-timus-expert / Carly 卡莉）

WorkBuddy 专家市场的单 Agent 专家，也是 **Timus 数据类专家的标准基座**：领域无关，按可替换语义包对任意已登记 Timus 应用表做建 / 查 / 改 / 删。

## 定位

同一份代码，两种用途：

1. **直接用**：无专用领域专家时，完成任意表的录入与维护。
2. **当模板**：复制本包生成领域专家，只换语义包与人设，**通用代码与契约不动**。

领域无关的关键：表名、字段名、必填项、关联、固定值都从**语义包**推导，技能文档不硬编码业务实体。

## 文档权威源（维护须知）

改规则**只改权威源**，其余文档概述并引用：

- 字段定义 / 类型 / 可写性 → `skills/timus-app-schema/references/timus-team-schema.yaml`（模板；演示集 `demo-schema.yaml`）。文档不得复述字段清单表格。
- 采集 / 确认 / 数值 / 日期口径 → `skills/timus-app-schema/SKILL.md`「录入与维护技能的通用规范」；各技能只写差异。
- 通用写契约（参数 / 响应 / 错误 / 安全）→ `skills/timus-app-schema/references/write-contract.md`。
- 意图路由 → `skills/timus-app-schema/references/intent-routing.md`；`agents/*.md` 只留原则。

> 维护清单：改完跑 `python3 tests/smoke_test.py`、`python3 tests/test_schema_lib.py`、`python3 tests/test_util.py`。改 `skills/timus-app-schema/scripts/` 须同步到 `project-management-expert` 与 `customer-management-expert` 两包，三边各跑一次 `python3 tests/smoke_test.py --update-lock`。

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

本包是**规范源**。新建 `<new>` 按序执行，≤6 步：

| 步骤 | 动作 | 验收 |
| --- | --- | --- |
| 1 | 整包复制为 `~/.workbuddy/plugins/cache/my-experts/<new>/1.0.0` | 目录骨架一致 |
| 2 | 改 `plugin.json`：`name` / `plugin` / `agentName` / `displayName` / `profession` / `description` / `displayDescription` / `categoryId` / `avatar` / `tags` / `quickPrompts` | 三者同名；`displayDescription.zh` 40–50 字 |
| 3 | 用目标应用字段集替换 `references/timus-team-schema.yaml` 的 `team_code` / `tables` / `fields`，`type_policy` 保留全集 | `--list-tables` 输出目标 `team_code` 与全部表 |
| 4 | 写 `agents/<new>.md`：人设 + 核心能力 + 路由原则 + 能力边界 | 无字段表 / 流程细则 / 数值算法 |
| 5 | 领域专属能力才建 `<实体>-create-form`；通用增删改查复用 `record-create-form` / `record-maintenance` | 技能数与实体数解耦 |
| 6 | 改 `tests/pkg_config.py` 的 `APP_CODE` / `SCHEMA_FILE` / `REQUIRED_TABLES` / `FORM_SKILLS`，跑 `--update-lock` 后三件套全绿 | `SMOKE OK` + 两单测 `OK` |

**六条硬约束**：

1. **数据分家、代码合源**：语义包各包一份；`scripts/` 四脚本 + `write-contract.md` + `tests/` 三件套跨包字节级一致，由 `scripts.lock` 锁定。
2. **规则单点**：写入确认两步法、采集渠道判定顺序、数值 / 日期口径只写在语义包 SKILL.md；能力技能只写差异。
3. **禁复述**：`agents/*.md` 与 README 禁「`S.xxx` + 类型」字段表格行；`lowcode-api.md` 禁复制响应结构与安全边界。
4. **数值与日期不心算**：一律 `point_util.py` / `date_util.py` 出数。
5. **能力边界诚实**：未实现的录入类型须说明，不以分析结论冒充写入能力。
6. **占位符不写入**：语义包未填真实字段前拒绝写入。

## 与另外两个专家包的关系

`project-management-expert`（`MAINLINE` / 7 表）与 `customer-management-expert`（`03.SPMP.TIMUS` / 6 表）按本规范产出：语义包各自独立，脚本与契约共用；三者互不依赖、不共享字段。

## 关于工具与连接器

按规范开发者不加 `tools`：`plugin.json` 与 Agent frontmatter 均无 `tools`；工具权限由系统统一分配。

依赖 **`timus-runtime` 连接器**（`plugin.json` 的 `dependencies.connectors`）：

- 地址与令牌由用户在 WorkBuddy **连接设置**填写，注入连接器进程环境变量；不写入本包、不进对话与日志；本包无 `.mcp.json`。
- 连接器未连 / 令牌过期：不假定数据可用，不伪造查询结果。

## 打包与上架

```bash
cd /path/to/your/workspace
zip -r general-timus-expert.zip general-timus-expert -x '*.DS_Store'
unzip -l general-timus-expert.zip | grep -F '.codebuddy-plugin'
```

上架前确认：

1. `author.name` 为「武汉海辞科技有限公司」，`author.email` 真实。
2. 头像 512×512 PNG/JPG，≤ 500KB。
3. `plugin.json` 的 `skills` 声明 3 个技能目录，`dependencies.connectors` 声明 `timus-runtime`。
4. 无 `tools` 字段、无明文凭据。
5. `python3 tests/smoke_test.py` 全绿（含脚本哈希锁）。

## 开源协议与署名

[Apache License 2.0](LICENSE)。Copyright 2026 武汉海辞科技有限公司；署名见 [NOTICE](NOTICE)，再分发保留 `LICENSE` 与 `NOTICE`。
