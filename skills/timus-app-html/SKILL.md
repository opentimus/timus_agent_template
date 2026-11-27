---
name: timus-app-html
description: Timus 数据页面 — 把结构化数据生成自包含 HTML 展示或编辑。
version: 1.0.0
agent_created: true
---

# 数据页面（HTML）

需要网页承载数据时，构造 payload 后运行 `<skill-dir>/scripts/build_html.py`（参数见 `-h`），用 `present_files` 打开。页面只展示 / 编辑，不含凭据、不直连，写入仍走 `timus-app-add` / `timus-app-maintenance`。

payload 必含 `title`、`columns[]`（`key` 用稳定字段 ID）、`rows[]`；`editable: true` 时可编辑并导出 JSON 回传。空数据显示「暂无数据」。样式与脚本内联，无外链 / 第三方依赖。
