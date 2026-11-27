# Timus Runtime Connector

WorkBuddy Connector（MCP + Skill），把 Timus Runtime 组织元数据读写接入 WorkBuddy。连接器包只含配置与 Skill；MCP 运行时以 npm 包发布，用 `npx` 启动。

## 文件

| 提交产物（`dist/`） | 开发文件（不进产物） |
| --- | --- |
| `connector-meta.json`、`mcp.json`、`token-schema.json`、`icon.svg`、`skills/timus-runtime/SKILL.md` | `server.js`、`package.json`、`scripts/pack-connector.mjs` |

## 命令

`npm run check`（只校验）、`npm run pack:connector`（生成 `dist/`）、`npm pack --dry-run`（核对 npm 白名单）。

## 发布

版本同步五处：`connector-meta.json`、`package.json`、`server.js` 的 `VERSION`、`skills/timus-runtime/SKILL.md` 的 frontmatter、`mcp.json` 的 `timus-runtime-mcp@<版本>`。`npm publish` 后执行 `npm run pack:connector`，提交 `dist/`。`npm run check` 会比对源与 `dist/` 内容哈希，校验脚本拦截不一致。

## 边界

- 不内置元数据表名/字段名：上游注入 → 用户给出 → 读样本记录 → 索取。
- 凭证只由连接设置注入本机 MCP 进程；服务地址仅接受 https（明文 http 直接拒绝）。包内不放 `.env.local` / `.DS_Store`，出包前校验会检测凭据文件并拒绝通过。
- `mcp.json` 固定官方 registry 与版本号；发布账号需开启 2FA。
- `docUrl` 目前为通用文档，上架前替换为 Timus 侧取参说明。
