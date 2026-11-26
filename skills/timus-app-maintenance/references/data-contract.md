# 基础数据维护契约（查 / 改 / 删）

表名与字段名取自 `skills/timus-app-schema/references/timus-team-schema.yaml`；本地业务块见同目录 `timus-team-data.yaml`。本文件只写脚本契约与定位规则。

## 查询

```bash
python3 <skill-dir>/scripts/data_tool.py --list-tables
python3 <skill-dir>/scripts/data_tool.py --table <表名>
python3 <skill-dir>/scripts/data_tool.py --table <表名> --where "S.<字段>=<值>" --fields "S.<字段A>" "S.<字段B>"
```

`--where` 可重复（AND），`--fields` 可多值；stdout 为 JSON。查询无破坏性、无需确认；回报条数与关键字段，无匹配如实说明。

## 定位规则（改 / 删共用）

1. 有记录 ID → 直接用。
2. 无 → 查询且**必须唯一**：
   - 0 条 → 报未找到，列可用筛选维度，请用户补充；
   - 多条 → 列候选（关键字段 + 记录 ID），请用户指定，不擅自挑；
   - 1 条 → 继续。

## 修改

```bash
python3 <skill-dir>/scripts/data_tool.py --table <表名> --record <记录ID> --set "S.<字段>=<新值>"
```

- `--set` 可多值；只改记录中已存在字段，不新增字段。
- 字段名须在表头元数据中；新值按类型书写，数值经 `point_util` 归一、日期取 `date_util` 的 `*_datetime`。
- 定位唯一后直接写入；回报记录 ID 与旧值 → 新值。

## 删除

```bash
python3 <skill-dir>/scripts/data_tool.py --table <表名> --record <记录ID> --delete
```

- 成功后回报被删标识；**不自动重查**。

## 本技能特有点

- 不新建、不批量、不改表结构；一次一条。
- 不凭记忆填记录 ID，候选来自查询。
- 改 / 删不重复提交；原地改写 YAML，保留注释与格式。
- 表头元数据或基础数据为占位符时拒绝改 / 删。
