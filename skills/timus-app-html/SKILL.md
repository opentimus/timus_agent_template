---
name: timus-app-html
description: Timus 数据页面技能 — 需要把结构化数据以网页展示、编辑或确认时，生成自包含 HTML 并弹出页面。触发词：打开网页、生成页面、可视化、预览数据、表格展示、网页确认、导出网页。
version: 1.0.0
agent_created: true
---

# 数据页面（HTML）

当对话需要网页承载数据时，生成自包含页面并弹出；页面只做展示 / 编辑，不直连、不含凭据。

## 生成流程

1. 构造 payload JSON（字段 `key` 用表头元数据的系统字段名）。
2. 运行生成器：

```bash
python3 <skill-dir>/scripts/build_html.py --payload <payload.json> --output <页面.html>
```

3. 用 `present_files` 打开生成的 HTML，即弹出页面。

## payload 格式

```json
{
  "title": "客户列表",
  "subtitle": "本地基础数据",
  "badges": [{"label": "表", "value": "客户", "ok": true}],
  "tableTitle": "记录",
  "tableHint": "可编辑",
  "note": "编辑后点「导出 JSON」回传对话",
  "editable": true,
  "columns": [{"key": "S.客户", "label": "客户"}],
  "rows": [{"id": "cust001", "S.客户": "示例客户甲"}]
}
```

- `title` 必填；`columns` / `rows` 为数组。
- `editable: true` 时单元格可编辑，点「导出 JSON」查看回传载荷。
- 只读展示省略 `editable`。

## 约束

- 自包含：样式与脚本内联，无外链、无第三方依赖。
- 页面不含令牌 / 地址 / 凭据，也不直连连接器；令牌规范见 README「关于工具与连接器」。
- 页面数据只用于展示与回传；写入由 `timus-app-add` / `timus-app-maintenance` 执行。
- 空数据也生成页面，显示「暂无数据」，不报错。
