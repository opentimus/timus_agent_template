---
name: timus-app-maintenance
description: Timus 数据查 / 改 / 删与语义包 — 记录查询、字段更新、记录删除、本地数据维护。
version: 1.0.0
agent_created: true
---

# 数据维护（查 / 改 / 删）

最短链路：加载技能 → 调用脚本 → 返回 ID 即完成。明确指令直接写入，仅含糊时 `AskUserQuestion`；不写后查询。

- 实例技能直达脚本，固化 `--app` / `--table` / `--pack`，不读本文件。
- 语义包结构、字段 / 类型 / 策略 / 本地记录见 `references/timus-team.yaml` 注释；动作族与定位见 `references/intent-routing.md`；原则与边界见 `agents/general-timus-expert.md`。
- 命令：`data_tool.py -h`（查 / 改 / 删）、`point_util.py -h`（数值 / 单号）、`date_util.py -h`（日期）。参数见 `-h`，`stdout` 仅 JSON，错误走 `stderr` + `exit 2`。
- 批量：多条追加用重复 `--set` 一次调用，不拆多次。
- 并发：同一 pack 文件写操作串行；不同 pack 文件可并行。
- 返回：写入返回记录 ID，不再查询验证；改 / 删无 ID 用 `--where` 定位唯一记录（删不跳过定位，改可不传 ID）。
