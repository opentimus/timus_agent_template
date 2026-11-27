#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dist = path.join(root, 'dist');
const staging = path.join(root, '.dist-staging');
const checkOnly = process.argv.includes('--check-only');
const SKILL = 'skills/timus-runtime/SKILL.md';
const errors = [];
const fail = (message) => errors.push(message);
const abs = (file) => path.join(root, file);
const has = (file) => fs.existsSync(abs(file));
const read = (file) => fs.readFileSync(abs(file), 'utf8');
const hash = (file) => crypto.createHash('sha256').update(fs.readFileSync(file, 'utf8')).digest('hex');
const json = (file) => {
  try { return JSON.parse(read(file).replace(/^\uFEFF/, '')); }
  catch (err) { fail(`${file} 不是合法 JSON：${err.message}`); return {}; }
};
const versionOf = (text) => (/(?:VERSION\s*=\s*|^\s*version:\s*)['"]?([\d.]+)/m.exec(text || '') || [])[1];
const report = () => {
  if (!errors.length) return;
  console.error('❌ 校验未通过：');
  errors.forEach((message) => console.error(`  - ${message}`));
  process.exit(1);
};

const meta = json('connector-meta.json');
const mcp = json('mcp.json');
const pkg = json('package.json');
const servers = Object.entries(mcp.mcpServers || {});
if (!servers.length) fail('mcp.json 缺少 mcpServers');
const icon = ['icon.svg', 'icon.png', 'icon.jpg'].find(has);
const whitelist = ['connector-meta.json', 'mcp.json', icon].filter(Boolean);
if (!icon) fail('缺少图标：icon.svg / icon.png / icon.jpg');
else if (/\.svg$/i.test(icon)) {
  const svg = read(icon);
  if (!/<svg[\s>]/i.test(svg) || !/viewBox\s*=|\bwidth\s*=/.test(svg)) fail(`${icon} 内容不是有效 SVG`);
}
if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(meta.source || '')) fail('source 必须是 kebab-case');

const versions = {
  meta: meta.version,
  package: pkg.version,
  server: versionOf(has('server.js') ? read('server.js') : ''),
  skill: versionOf(has(SKILL) ? read(SKILL) : '')
};
const tokenFields = meta.auth_mode === 'token'
  ? (has('token-schema.json') ? (json('token-schema.json').fields || []) : (fail('auth_mode=token 需要 token-schema.json'), []))
  : [];
if (meta.auth_mode === 'token') whitelist.push('token-schema.json');
if (tokenFields.some((f) => /token|key|secret|password/i.test(f.key || '') && f.type !== 'password')) {
  fail('凭证字段的 type 必须是 password');
}

for (const [key, server] of servers) {
  if (key !== meta.source) fail(`MCP Server key「${key}」与 source「${meta.source}」不一致`);
  if (server?.type !== 'stdio') fail(`mcpServers.${key} 当前只支持 stdio 配置`);
  const pinned = (server?.args || []).find((arg) => /^timus-runtime-mcp@/.test(arg));
  if (!pinned) fail(`mcpServers.${key} 必须用 npx 固定版本：timus-runtime-mcp@<version>`);
  else versions[`mcp:${key}`] = pinned.slice('timus-runtime-mcp@'.length);
  const placeholders = [...JSON.stringify(server || {}).matchAll(/\$\{([^}]+)\}/g)].map((m) => m[1]).sort();
  const keys = tokenFields.map((f) => f.key).sort();
  if (JSON.stringify(placeholders) !== JSON.stringify(keys)) {
    fail(`mcpServers.${key} 占位符 ${placeholders} 与 token-schema 字段 ${keys} 不一致`);
  }
}
for (const [where, version] of Object.entries(versions)) {
  if (!version) fail(`未能从 ${where} 读取版本`);
  else if (version !== meta.version) fail(`版本不一致：${where}=${version}，connector-meta=${meta.version}`);
}

if (!has(SKILL)) fail(`缺少 ${SKILL}`);
else {
  const front = /^---\r?\n([\s\S]*?)\r?\n---/m.exec(read(SKILL));
  const name = front && /^name:\s*(\S+)/m.exec(front[1])?.[1];
  if (!name) fail(`${SKILL} 缺少 frontmatter name`);
  if (name && name !== 'timus-runtime') fail(`skill name「${name}」应为 timus-runtime`);
  whitelist.push(SKILL);
}

const SENSITIVE = /^\.env($|\.)|^credentials?$|\.pem$|\.key$/i;
function scanSecrets(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (['dist', '.dist-staging', 'node_modules', '.git'].includes(entry.name)) continue;
    const full = path.join(dir, entry.name);
    const rel = path.relative(root, full);
    if (SENSITIVE.test(entry.name)) fail(`发现疑似凭据文件，禁止出包：${rel}`);
    if (entry.isDirectory()) scanSecrets(full);
  }
}
scanSecrets(root);

if (checkOnly) {
  for (const file of whitelist) {
    const out = path.join(dist, file);
    if (!fs.existsSync(out)) fail(`dist 缺少产物：${file}`);
    else if (hash(abs(file)) !== hash(out)) fail(`dist 与源不一致：${file}`);
  }
}
report();

if (!checkOnly) {
  fs.rmSync(staging, { recursive: true, force: true });
  for (const file of whitelist) {
    const target = path.join(staging, file);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.copyFileSync(abs(file), target);
  }
  fs.rmSync(dist, { recursive: true, force: true });
  fs.renameSync(staging, dist);
  console.log(`已生成产物：dist/（${whitelist.length} 个文件）`);
}
console.log('✅ 校验通过，可提交审核。');
