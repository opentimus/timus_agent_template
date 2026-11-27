# general-timus-expert / Carly 卡莉

专家模板：复制后只换人设、语义包、头像。新增场景复制 `skills/timus-app-add/`，改名并写 3 行差异。

- `skills/timus-app-data/`：数据层固定入口（查改删 / 唯一写入口 / 日期点数 / 语义包）。
- `skills/timus-app-add/`：ADD 场景模板，每个场景一个 SKILL.md。
- `skills/timus-app-html/`：页面层。
- 依赖 `timus-runtime`。
- 打包：`zip -r general-timus-expert.zip . -x '*.DS_Store'`

[Apache 2.0](LICENSE)；Copyright 2026 武汉海辞科技有限公司，署名见 [NOTICE](NOTICE)。
