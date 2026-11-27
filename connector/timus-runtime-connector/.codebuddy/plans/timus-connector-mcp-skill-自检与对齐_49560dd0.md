---
name: timus-connector-mcp-skill-自检与对齐
overview: 按 WorkBuddy「MCP + Skill」连接器规范对 timus-runtime-connector 做逐条合规自检，并修复不合规项：交付方式改为 npm + npx 的 stdio、修正版本门禁与元信息文案、把元数据 Skill 改为自包含纯 Markdown、清理包内凭据文件。
todos:
  - id: compliance-report
    content: 按规范逐条自检并撰写 compliance-report.md，列出偏离项与修复动作
    status: completed
  - id: delivery-npm
    content: 新增 package.json 与 scripts/pack-connector.mjs，生成仅含规范文件的 dist 产物并校验
    status: completed
    dependencies:
      - compliance-report
  - id: meta-and-form
    content: 修正 connector-meta.json、mcp.json、token-schema.json（版本门槛、npx、表单文案）
    status: completed
    dependencies:
      - compliance-report
  - id: runtime-skill
    content: 用 [skill:skill-creator] 重写 timus-runtime/SKILL.md 并去除内部调试细节
    status: completed
    dependencies:
      - meta-and-form
  - id: schema-skill
    content: 用 [skill:skill-creator] 将 timus-spmp-schema 元数据内联为自包含 SKILL.md
    status: completed
    dependencies:
      - runtime-skill
  - id: security-audit
    content: 用 [skill:skills安全审计] 审查两篇 Skill 并整改问题
    status: completed
    dependencies:
      - schema-skill
  - id: cleanup-verify
    content: 移出 .env.local、清理 .DS_Store，执行 dist 与 npm pack 复核
    status: completed
    dependencies:
      - delivery-npm
      - security-audit
---

## 产品概述

对现有「Timus Runtime 组织元数据」连接器包（connector/timus-runtime-connector）按 WorkBuddy Connector 规范的「MCP + Skill 接入」路径做一次完整自检，并落地修复，使该包可以直接提交审核、上架 Connector 市场。

## 核心功能

- **逐条合规体检**：以规范条目为清单（包结构、元信息字段、命名规范、Skill 写法、图标、安全要求、MCP 配置文件、自填凭证表单、版本兼容），逐项给出「符合 / 偏离 / 待确认」结论、证据位置与修复动作，并汇总成一份可归档的检查表。
- **接入形态改为规范描述的标准形态**：连接器不再依赖随包分发的本地服务端脚本，而是复用已发布的运行时程序、由宿主自动拉起，用户侧无需额外安装。
- **元信息与安装表单对齐规范**：统一名称、描述与示例口径；描述长度落入建议区间；示例不再与本包内的表结构脱节；安装表单明确告知凭证只保存在本机、不再向用户暴露内部调试机制。
- **版本门槛统一**：声明的最低宿主版本与实际用到的能力一致，避免低版本用户装上后无法启动。
- **元数据技能维持 YAML 单一真源**：表名 / 字段名 / 可写性继续由 `skills/timus-spmp-schema/references/timus-spmp.yaml` 承载，随连接器包一起下发；SKILL.md 只写「怎么读这份 YAML、怎么映射成工具参数」，取消对 Python 脚本与专家包上下文的依赖。
- **凭据与产物清理**：包目录内明文凭据和系统垃圾文件被移出或排除；提供一键生成「仅含规范文件」的提交产物，且产物内容可逐项核对。

## 视觉与使用效果

- Connector 市场卡片、详情页、安装表单的文案与示例保持统一、可信，用户填表即可连接，无需理解内部实现。
- AI 在对话中先查字段元数据、再执行读写，写操作前复述目标记录并等待确认，删除等破坏性操作有明确前置核对。

## 技术栈

- 运行时：Node.js ≥ 18，现有 `server.js` 为**零第三方依赖** stdio MCP Server（仅 `fs/http/https/path/readline`），已实现 initialize / ping / tools/list / tools/call 与 5 个工具。
- 分发：npm 包（`npx` 启动）+ WorkBuddy `runtime: { type: "node" }` 托管 Node。
- 配置：WorkBuddy Connector 规范文件（`connector-meta.json` / `mcp.json` / `token-schema.json` / `icon.svg` / `skills/*/SKILL.md` + Skill 自带 `references/*.yaml`），认证方式保持 `auth_mode: "token"`。
- 校验与打包：Node 内置脚本（`scripts/pack-connector.mjs`），不引入构建依赖。

## 实施方案

### 1. 交付形态：stdio + npm + npx（推荐，用户已授权由我定方案）

现状 `command: "node", args: ["server.js"]` 依赖「宿主执行随包分发的服务端代码」，而规范包结构只允许元信息 / 连接配置 / Skill / 图标四类文件，stdio 示例是「通过 npx 运行本地进程」，且当前还缺 `cwd`，属于最不可控的一项。

- 采用：`command: "npx"`、`args: ["-y", "timus-runtime-mcp@1.3.0"]`、保留 `runtime: { type: "node", version: ">=18.0.0" }`、`timeout: 60000`、`env` 占位符不变。
- 为什么不是远程 HTTP MCP：`API_BASE_URL` / `CLIENT_TOKEN` 是 per-user 私有部署参数，托管形态需要我方中转第三方令牌，扩大凭据暴露面并新增常驻服务；而本地 stdio 进程与现架构一致，令牌不出本机。
- 为什么不是「包内 server.js + cwd」：`cwd`（v4.22.15）存在但规范未声明随包分发服务端代码，属未验证行为，风险高于发布 npm 包；保留为备选，仅在无法发布 npm 时启用。
- 代价与缓解：多一步 npm 发布与版本固定；已在 `mcp.json` 固定版本号，发布新版本时同步递增三处版本号（元信息、`SERVER_VERSION`、Skill frontmatter）。

### 2. 版本门槛修正

`runtime` 自 v5.0.0 起支持，`auth_mode: "token"` 自 v4.23.0 起支持；两者取高者 → `minWorkbuddyVersion: "5.0.0"`。否则 4.23.0~4.x 客户端会展示 token 表单却无法托管 Node，失败点在启动阶段、用户不可自查。

### 3. 元数据 Skill：保留 YAML 作为单一真源（按用户要求）

连接器只自动加载 `SKILL.md`，因此采取「YAML 随包下发 + SKILL.md 指路」的组合，而不是把 37 个字段抄进 Markdown：

- `skills/timus-spmp-schema/references/timus-spmp.yaml` **保留并进入发布产物**，继续作为唯一表名 / 字段名 / `type_policy` 真源，新增表或字段只改这一处。
- SKILL.md 重写为「定位 → 读取 → 映射 → 校验 → 调用」的确定性流程：写明 YAML 的包内相对路径、`team_code`/`tables`/`fields`/`type_policy` 各段含义、系统字段名到 `fields[].name` 的映射规则、只读类型不得写入，以及遇到未知字段时的处理（向用户索取，禁止猜测）。
- 删除所有对 `resolve_schema.py` / `schema_lib.py` / 专家包 `plugin.json` / `customer-create-form` 的引用；`scripts/*.py` 保留为开发期校验工具，但不进入发布产物、不被 SKILL.md 引用。
- 风险兜底：若宿主未下发 `references/` 目录导致 AI 读不到 YAML，SKILL.md 明确「取不到字段清单时先向用户索取字段名，不得猜测或按界面标题写入」，并把这一条列入打包校验与提交前自测项。
- 打包脚本做一致性校验：`skills/*/references/*.yaml` 必须存在且可解析；SKILL.md 中出现的 YAML 相对路径必须在产物中真实存在；YAML 顶层 `team_code` 必须与 SKILL.md 声明一致。

### 4. 产物与凭据处理

- 新增 `scripts/pack-connector.mjs`：白名单复制到 `dist/`（`connector-meta.json`、`mcp.json`、`token-schema.json`、`icon.svg`、`skills/*/SKILL.md`、`skills/*/references/*.yaml`），并校验 JSON 可解析、`source` 为 kebab-case、`token-schema` 的 `fields[].key` 与 `mcp.json` 占位符一一对应、图标存在、YAML 与 SKILL.md 交叉引用成立。
- `package.json` 用 `files: ["server.js"]` 白名单，保证 npm 包只有运行时脚本；`npm pack --dry-run` 可验证。
- 将 `.env.local`（明文凭据）移出包目录至仓库根 `.secrets/`（`.gitignore` 已忽略同模式，需补一条），并交由用户在 Timus 侧轮换该令牌；删除 `.DS_Store`；`--local-env` 调试分支代码保留但不再写入任何面向用户/Skill 的文档。

### 5. 一致性与性能

- 版本号单点：`connector-meta.version` = `package.json.version` = `server.js SERVER_VERSION` = Skill `version` = `mcp.json` 中 npx 固定版本，全部 1.3.0；打包脚本校验一致性。
- 性能：npx 首次冷启动有下载开销（单文件包，体量 < 40KB），之后命中缓存；不新增依赖、不增加请求路径；分页建议（10~50、`pageToken` 续页、`return_fields` 收敛）继续由 Skill 约束，避免大响应。
- 日志：沿用现有 stderr 诊断与 `Bearer ****` 脱敏；不新增打印凭据的路径。

## 关键配置结构（最终形态）

```
{
  "mcpServers": {
    "timus-runtime": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "timus-runtime-mcp@1.3.0"],
      "env": { "API_BASE_URL": "${API_BASE_URL}", "CLIENT_TOKEN": "${CLIENT_TOKEN}" },
      "runtime": { "type": "node", "version": ">=18.0.0" },
      "timeout": 60000
    }
  }
}
```

## 目录结构

```
connector/timus-runtime-connector/
├── connector-meta.json      # [MODIFY] version→1.3.0、minWorkbuddyVersion→5.0.0、description_en 压到≤100字符、统一 name_zh、示例对齐 03.SPMP.TIMUS（客户/项目）
├── mcp.json                 # [MODIFY] stdio 改为 npx + 固定版本，保留 runtime/env/timeout
├── token-schema.json        # [MODIFY] 文案改为「凭证仅保存在本机 ~/.workbuddy 目录」，删除明文调试实现描述，补字段级 _en 说明
├── icon.svg                 # 保持（64×64 viewBox，符合要求）
├── package.json             # [NEW] npm 包 timus-runtime-mcp@1.3.0，bin=server.js，files 白名单，engines>=18
├── server.js                # [MODIFY] SERVER_VERSION→1.3.0（工具与 PATH 不变）
├── scripts/pack-connector.mjs # [NEW] 白名单出包 + JSON/占位符/版本/YAML↔SKILL 一致性校验
├── compliance-report.md     # [NEW] 规范逐条自检表（结论/证据/修复动作），不进入发布产物
├── README.md                # [NEW] 维护说明：发布流程、版本同步点、YAML 真源维护规则
└── skills/
    ├── timus-runtime/SKILL.md        # [MODIFY] 去掉 .env.local/--local-env，补认证与授权失效指引、参数表与 inputSchema 对齐
    └── timus-spmp-schema/
        ├── SKILL.md                  # [MODIFY] 改为读取 references/timus-spmp.yaml 的映射流程，去除外部脚本/专家包引用
        ├── references/timus-spmp.yaml # [KEEP] 单一真源，随包下发（进入 dist）
        └── scripts/*.py              # [KEEP] 开发期校验工具，不进入 dist，SKILL.md 不再引用
```

## Agent Extensions

### Skill

- **skills安全审计**
- Purpose: 对两篇 SKILL.md 做安全审查，确认无越权指令、无凭据示例、无危险命令引导、外部引用可解析
- Expected outcome: 输出每篇 Skill 的问题清单与整改结论，整改后复检通过
- **skill-creator**
- Purpose: 按 Skill 编写最佳实践重写 `timus-runtime` 与 `timus-spmp-schema` 两篇 SKILL.md（frontmatter 规范、工具参数表、边界与错误处理）
- Expected outcome: 两篇结构统一、AI 可直接执行；`timus-spmp-schema` 以 YAML 为字段真源并给出可执行读取流程