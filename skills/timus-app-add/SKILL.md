---
name: timus-app-add
description: <场景>：把用户输入转成 <目标表> 记录并一次写入。
---

# <场景>添加（ADD 模板）

复制本目录后只改 `description`、下面「触发」和「步骤」；其余不动。

触发：用户说「<说法>」。仅新增；需查询时走脚本（`data_tool.py query`，经 `timus-runtime`），不触发编辑、删除。
步骤：`data_tool.py resolve|query` 定位 → `point_util.py` / `date_util.py` 换算 → `add_data.py --app A --table T --row "字段=值|..." [--from S --map T=F]` 一次写入。
通用规则见 `agents/general-timus-expert.md`。

仅场景需自定义校验时才加脚本，且只组装参数调用 `add_data.py`。
