# 通用数据专家模板（general-timus-expert / Carly 卡莉）

Timus 数据类专家模板：领域无关，按可替换语义包对任意已登记应用表查 / 改 / 删。**不直接投入使用**——复制后只换语义包与人设，通用代码与契约不动。表名、字段名、关联、固定值全从语义包推导；必填 / 选填由创建类型技能约束定义，不推导。

## 文档权威源

改规则**只改权威源**，其余文档概述并引用，不复述：

| 主题 | 权威源 |
| --- | --- |
| 字段定义 / 类型 / 可写性 | `skills/timus-app-schema/references/timus-team-schema.yaml` |
| 本地业务块（基础数据） | `skills/timus-app-schema/references/timus-team-data.yaml` |
| 数值 / 日期口径与脚本 | `skills/timus-app-schema/SKILL.md` |
| 行为路由 / 采集确认 / 写入流程 | `skills/timus-app-maintenance/SKILL.md`（逐关键词见其 `references/intent-routing.md`） |
| 原则与边界 | `agents/general-timus-expert.md`（只留原则，不复述流程） |

## 目录结构

```
general-timus-expert/
├── avatars/expert.png                 # 512×512 PNG（≤500KB）
├── agents/general-timus-expert.md     # 人设 / 原则 / 能力边界
├── skills/
│   ├── timus-app-schema/              # 语义包：两类 schema + 三脚本；字段唯一来源
│   ├── timus-app-maintenance/         # 行为层权威源：路由 + 采集 + 查改删
│   ├── timus-app-add/                 # 批量添加
│   ├── timus-app-html/                # 自包含 HTML 页面
│   └── rag/                           # 示例离线知识库（复制后删除或替换）
└── README.md
```

## 工具与连接器

- 不声明 `tools`：清单与 Agent frontmatter 均无 `tools`，权限由系统分配。
- 依赖 `timus-runtime` 连接器；令牌由用户在连接设置注入连接器进程，不写入 HTML / 对话 / 日志，不进本包（无 `.mcp.json`）。HTML 若需令牌与域名，放独立 `.js` 凭据文件。
- 连接器未连 / 令牌过期：不假定数据可用，不伪造结果。

## 打包与上架

```bash
zip -r general-timus-expert.zip general-timus-expert -x '*.DS_Store'
```

上架前确认：`author.name` 为「武汉海辞科技有限公司」且邮箱真实；头像 512×512 ≤500KB；清单声明 `skills` 与 `dependencies.connectors: timus-runtime`；无 `tools`、无明文凭据。

## 协议

[Apache License 2.0](LICENSE)。Copyright 2026 武汉海辞科技有限公司；署名见 [NOTICE](NOTICE)，再分发保留两者。
