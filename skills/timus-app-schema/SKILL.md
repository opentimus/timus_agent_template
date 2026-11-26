---
name: timus-app-schema
description: Timus 多维表语义包（通用版）— 两类 schema：表头元数据（表名 / 字段名 / 类型 / 可写性）与基础数据（本地业务块），以及字段解析与数值 / 日期口径脚本。触发词：查表、查字段、表结构、字段名、team_code、app_name、本地数据、基础数据、数值口径、单号生成、新建专家、适配新应用。
version: 1.0.0
---

# Timus 应用语义包（通用版）

**基础数据能力服务**：定义两类 schema，提供字段解析与数值 / 日期口径脚本。行为路由、采集确认、写入与查改删统一由 `timus-app-maintenance` 负责。语义包不是 MCP 运行时入参：连接器只接受 `app_name` / `table_name` / `fields`，映射在 schema 层完成。换应用 = 换 `references/` 下两类 schema，代码与契约不动。

## 两类 schema

| 类型 | 文件 | 用途 |
| --- | --- | --- |
| 表头元数据 | `references/timus-team-schema.yaml` | 表名 / 字段名 / 类型 / 可写性；**唯一字段来源** |
| 基础数据 | `references/timus-team-data.yaml` | 本地业务块记录值；**本地取值来源** |

两类须成对维护：`team_code` 一致，基础数据的表名与字段名逐字照抄表头元数据，禁自定义字段。首次使用须填真实 `team_code` / 表名 / 字段名，禁凭记忆或界面标题拼字段。

## 表头元数据

映射：`team_code` → `app_name`；`tables` 下表单名 → `table_name`；表单标识 `tbl...` 仅追溯、禁入参数；`fields` 下系统字段名 → `fields[].name`（唯一允许的字段标识）；`type_policy` 定可写性——只读：`AutoNumber` / `CreatedTime` / `Lookup` / `Formula`，可写：`Text` / `Number` / `SingleSelect` / `DateTime` / `User`。

字段名逐字使用（含前缀与大小写，同应用不同表前缀可不同，照 yaml 抄不统一）；字段缺失索取准确名，不用近义词 / 界面标题 / 历史别名；`User` 可写但值必须是 `open_id`（非姓名 / 别名 / 邮箱）。

## 基础数据

结构：`data` → 表名 → 记录 ID → 字段名: 值；另有 `synced_at` / `source` / `members` 快照（成员字段下划线命名）。`members` 每项含 `member_id` / `member` / `role` / `open_id` / `record_id`：`open_id` 即 `User` 写入值，`record_id` 仅本地追溯。

取值先本地后远程：本地命中直接用，避免 `apaas_page_records`；未命中再远程，远程新记录按需落盘复用。字段名须在表头元数据中存在，否则 `exit 2`；本地数据不伪造远程结果。查 / 改 / 删由 `timus-app-maintenance` 的 `data_tool.py` 执行，本技能不持有数据操作脚本。

## 脚本（单点实现，跨包 import）

| 脚本 | 职责 |
| --- | --- |
| `schema_lib.py` | 受限 YAML 解析 + 字段可写性查询 |
| `point_util.py` | 数值：`normalize` 两位小数、`split` 按权重拆分、`next-pair` / `next-batch` 单号 |
| `date_util.py` | 日期：`options` 候选、`batch` 第 N 天、`single` 今日→目标日，输出 `YYYY-MM-DD HH:mm:ss` |

```bash
python3 <skill-dir>/scripts/point_util.py normalize 99.5
python3 <skill-dir>/scripts/point_util.py split --total 6 --weight 3 --weight 2 --weight 1
python3 <skill-dir>/scripts/point_util.py next-pair --prefix TIN
python3 <skill-dir>/scripts/point_util.py next-batch --prefix TPAY --count 3
python3 <skill-dir>/scripts/date_util.py options
python3 <skill-dir>/scripts/date_util.py batch --start-date 2026-11-20 --task "任务A|1|2"
python3 <skill-dir>/scripts/date_util.py single --end-date 2026-11-30
```

`exit 2` + stderr 中文原因；stdout 仅 JSON。禁改三脚本接口（新能力走新脚本）；两类 schema 整体、表单标识、自定义字段名禁入连接器参数；禁猜字段名、禁用语义包外的工具名。其余通用禁令见 `agents/general-timus-expert.md`。解析限制：按行首缩进读键值，不支持列表与跨行结构。
