---
name: timus-app-schema
description: Timus 多维表语义包（通用版）- 两类 schema：表头元数据（表名 / 字段名 / 类型 / 可写性）与基础数据（本地业务块），以及字段解析与数值 / 日期口径脚本。触发词：查表、查字段、表结构、字段名、team_code、app_name、本地数据、基础数据、业务块、数值口径、单号生成、新建专家、适配新应用。
version: 1.0.0
---

# Timus 应用语义包（通用版）

本 Skill 是**基础数据能力服务**：定义两类 schema，提供字段解析与数值 / 日期口径脚本。行为路由、采集确认、写入与查改删流程统一由 `timus-app-maintenance` 负责。

语义包**不是 MCP 运行时入参**：连接器只接受 `app_name` / `table_name` / `fields`，映射在 schema 层完成。参数语义 / 响应 / 错误 / 安全见 `references/write-contract.md`。

领域无关：换应用 = 换 `references/` 下的两类 schema，代码与契约不动。

## 两类 schema

| 类型 | 文件 | 用途 |
| --- | --- | --- |
| 表头元数据 | `references/timus-team-schema.yaml` | 查指定字段：表名 / 字段名 / 类型 / 可写性；生成写入参数 |
| 基础数据 | `references/timus-team-data.yaml` | 提供本地业务块的记录值，避免远程调用 |

两类须成对维护：`team_code` 一致，基础数据的表名与字段名逐字照抄表头元数据，禁止自定义字段。表头元数据为**唯一字段来源**；基础数据为**本地取值来源**。

## 表头元数据

`references/timus-team-schema.yaml` 是包内**唯一**表名 / 字段名清单，为**通用模板**；首次使用须填真实 `team_code` / 表名 / 字段名，禁凭记忆或界面标题拼字段。

| 元素 | 映射到连接器 | 规则 |
| --- | --- | --- |
| `team_code` | `app_name` | 应用编码，所有工具共用 |
| `tables` 下表单名 | `table_name` | 与平台配置一致 |
| `tables` 下表单标识（`tbl...`） | 不映射 | 仅元数据 / 追溯，禁入参数 |
| `fields` 下系统字段名 | `fields[].name` | 唯一允许的字段标识 |
| `type_policy` | 可写性 | 只读：`AutoNumber` / `CreatedTime` / `Lookup` / `User` / `Formula`；可写：`Text` / `Number` / `SingleSelect` / `DateTime` |

- 字段名逐字使用，含前缀与大小写；同应用不同表前缀可不同，照 yaml 抄，不统一。
- 只读类型及需特定值结构的 `Lookup` / `User` 禁入写 `fields`。
- 字段缺失时索取准确名，不用近义词 / 界面标题 / 历史别名。
- 包内无自定义字段名；历史别名与 `A.` 前缀禁传。

## 基础数据（本地业务块）

`references/timus-team-data.yaml` 存本地业务记录；首次使用须填真实 `team_code` 与记录。结构：`data` → 表名 → 记录 ID → 字段名: 值。记录 ID 仅本地追溯，禁入连接器参数。

- 本地查询先于远程：命中即直接用，避免 `apaas_page_records`；未命中再走远程。
- 字段名须在表头元数据中存在，否则 `exit 2`。
- 本地数据只作取值来源，不伪造远程结果；远程返回的新记录按需落盘后再复用。
- 基础数据的查 / 改 / 删由 `timus-app-maintenance` 的 `data_tool.py` 执行，本技能不持有数据操作脚本。

## 脚本（跨专家包共用同一份代码）

四脚本在三包**字节级一致**；改动须全同步。基础数据的查 / 改 / 删脚本在 `timus-app-maintenance` 技能。

| 脚本 | 职责 |
| --- | --- |
| `resolve_schema.py` | 表头元数据查询与参数生成（降级） |
| `schema_lib.py` | 受限 YAML 解析 + 类型层校验 |
| `point_util.py` | 数值口径：`normalize` 两位小数、`split` 按权重拆分、`next-pair` / `next-batch` 单号 |
| `date_util.py` | 日期口径：`options` 候选、`dates` / `batch` 第 N 天、`single` 今日→目标日，输出 `YYYY-MM-DD HH:mm:ss` |

```bash
python3 <skill-dir>/scripts/resolve_schema.py --list-tables
python3 <skill-dir>/scripts/resolve_schema.py --list-fields --table <表单名>
python3 <skill-dir>/scripts/resolve_schema.py --table <表单名> --set <字段>=<值>
python3 <skill-dir>/scripts/point_util.py normalize 99.5
python3 <skill-dir>/scripts/point_util.py split --total 6 --weight 3 --weight 2 --weight 1
python3 <skill-dir>/scripts/point_util.py next-pair --prefix TIN
python3 <skill-dir>/scripts/point_util.py next-batch --prefix TPAY --count 3
python3 <skill-dir>/scripts/date_util.py options
python3 <skill-dir>/scripts/date_util.py batch --start-date 2026-11-20 --task "任务A|1|2"
python3 <skill-dir>/scripts/date_util.py single --end-date 2026-11-30
```

脚本 `exit 2` + stderr 中文原因；stdout 仅 JSON。

## 禁止事项

- 两类 schema 整体、表单标识、自定义字段名禁入连接器参数。
- 禁猜字段名；禁用语义包外的工具名。
- 禁凭记忆填关联 ID；禁心算数值 / 单号、手拼日期。
- 禁在语义包、脚本或输出写入真实令牌、地址或凭据。
- 禁改 `scripts/` 四脚本接口；新能力走新脚本。

## 资源

- `references/timus-team-schema.yaml`：表头元数据模板（含演示值），填后为唯一字段来源。
- `references/timus-team-data.yaml`：基础数据模板（含演示值），填后为本地取值来源。
- `references/write-contract.md`：参数 / 响应 / 错误 / 安全（跨包同一份）。
- `scripts/`：四脚本，跨包字节级一致。
- 解析限制：`schema_lib.py` 按行首缩进读键值；行内第一个 `#` 起为注释，值禁含 `#`，不支持列表、引号包裹的井号或跨行结构。
