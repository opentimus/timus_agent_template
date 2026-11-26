# 通用数据专家（general-timus-expert / Carly 卡莉）

**Timus 数据类专家的标准模板**：基础功能已闭环，领域无关，按可替换语义包对任意已登记 Timus 应用表做查 / 改 / 删；不直接投入使用。

## 定位

本包是**专家模板**，不直接投入使用：基础功能已闭环，复制本包生成领域专家，只换语义包与人设，**通用代码与契约不动**。

领域无关的关键：表名、字段名、关联、固定值都从**语义包**推导；必填 / 选填由创建类型技能约束定义，不推导；技能文档不硬编码业务实体。

## 文档权威源（维护须知）

改规则**只改权威源**，其余文档概述并引用：

- 字段定义 / 类型 / 可写性（表头元数据）→ `skills/timus-app-schema/references/timus-team-schema.yaml`（模板含演示值）。文档不得复述字段清单表格。
- 本地业务块（基础数据）→ `skills/timus-app-schema/references/timus-team-data.yaml`（模板含演示值）；先本地命中，未命中再远程。
- 数值 / 日期口径与脚本 → `skills/timus-app-schema/SKILL.md`；schema 仅作基础数据能力服务。
- 行为路由 / 采集确认 / 写入流程 → `skills/timus-app-maintenance/SKILL.md`；逐关键词映射见同技能 `references/intent-routing.md`。
- 通用写契约（参数 / 响应 / 错误 / 安全）→ `skills/timus-app-schema/references/write-contract.md`；`agents/*.md` 只留原则。

## 目录结构

```
general-timus-expert/
├── .codebuddy-plugin/plugin.json
├── avatars/expert.png                    # 512×512 PNG（≤ 500KB）
├── agents/general-timus-expert.md        # 人设 / 核心能力 / 路由原则 / 能力边界
├── skills/
│   ├── timus-app-schema/                 # 基础数据能力服务（schema + 契约 + 脚本）
│   │   ├── SKILL.md                      # 两类 schema + 数值/日期口径 + 模板化指南
│   │   ├── references/
│   │   │   ├── timus-team-schema.yaml    # 表头元数据模板（唯一字段来源）
│   │   │   ├── timus-team-data.yaml      # 基础数据模板（本地业务块）
│   │   │   └── write-contract.md         # 通用写契约（跨包同一份）
│   │   └── scripts/                      # 四脚本（跨包字节级一致）
│   ├── timus-app-maintenance/            # 行为层权威源（路由 + 采集确认 + 查改删）
│   │   ├── SKILL.md                      # 行为层唯一权威源
│   │   ├── scripts/data_tool.py          # 本地基础数据查改删
│   │   └── references/
│   │       ├── intent-routing.md         # 意图→技能映射
│   │       └── data-contract.md          # 本地数据脚本契约
│   ├── timus-app-add/                    # 基础数据批量添加（先查后加 / 直接填写）
│   │   └── scripts/add_data.py           # 批量追加记录
│   ├── timus-app-html/                   # 数据页面（自包含 HTML 展示 / 编辑）
│   │   ├── assets/app.html.tpl           # 页面模板
│   │   └── scripts/build_html.py         # payload → HTML
│   └── rag/                              # 离线知识库（源文档 + 预建索引 + 检索脚本）
└── README.md
```

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
3. `plugin.json` 的 `skills` 声明技能目录，`dependencies.connectors` 声明 `timus-runtime`。
4. 无 `tools` 字段、无明文凭据。

## 开源协议与署名

[Apache License 2.0](LICENSE)。Copyright 2026 武汉海辞科技有限公司；署名见 [NOTICE](NOTICE)，再分发保留 `LICENSE` 与 `NOTICE`。
