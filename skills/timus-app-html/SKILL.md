---
name: timus-app-html
description: 把结构化数据生成自包含 HTML 页面。
---

# 数据页面

运行 `<skill-dir>/scripts/build_html.py` 生成 HTML，再用 `present_files` 打开；payload 与参数见 `-h`。页面只展示 / 编辑，不直连、不含凭据。editable 编辑后点击「提交」，由 runtime 注入的 `timusAdd` 完成 add；未注入时回退导出 JSON。
