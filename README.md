# 通用数据专家模板（general-timus-expert / Carly 卡莉）

复制后只换语义包与人设；通用代码和契约不动。表名、字段名、关联、固定值从语义包推导；必填 / 选填由创建类型技能定义。

技能按 `应用-表-动作` 命名，例如 `todo-member-add`；实例技能在宿主层直接映射到脚本，固化 `--app` / `--table` / `--pack`，不读 `SKILL.md`。模板保留 `timus-app-*` 通用名。

实例技能可预置类型枚举 / 常用候选，命中直接用，不弹 `AskUserQuestion`。

表和字段用稳定英文 ID；每个应用独立配置 `language`，`tables` / `fields` 自带 `platform[language]`，本地记录用稳定 ID。

`type_policy` 仅为字段默认策略；用户可手动调整字段的 `@策略`，以最终配置为准。

## 权威源

| 主题 | 权威源 |
| --- | --- |
| 稳定表 / 字段 ID / 类型 / 可写性 / 平台映射 / 本地记录 | `skills/timus-app-maintenance/references/timus-team.yaml` |
| 意图路由与定位 | `skills/timus-app-maintenance/references/intent-routing.md` |
| 脚本命令与返回约定 | `skills/timus-app-maintenance/SKILL.md` |
| 脚本参数 | 各脚本 `-h` |
| 原则与边界 | `agents/general-timus-expert.md` |

## 目录

```
avatars/expert.png
agents/general-timus-expert.md
skills/
├── timus-app-maintenance/   # 语义包 + 行为层：单文件 YAML / 路由 / 查改删 / 脚本
├── timus-app-add/           # 批量添加
└── timus-app-html/          # 自包含 HTML
README.md
```

## 运行

依赖 `timus-runtime` 连接器；令牌由用户在连接设置注入，不进本包 / HTML / 对话 / 日志。未连接或令牌过期不伪造结果。权限由系统分配，不声明 `tools`。

打包：`zip -r general-timus-expert.zip . -x '*.DS_Store'`

## 协议

[Apache 2.0](LICENSE)；Copyright 2026 武汉海辞科技有限公司，署名见 [NOTICE](NOTICE)。
