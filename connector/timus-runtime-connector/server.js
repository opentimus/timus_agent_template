#!/usr/bin/env node
'use strict';
const fs = require('fs'), path = require('path'), readline = require('readline');

const NAME = 'timus-runtime', VERSION = '1.3.0', TIMEOUT = 60000;
const PATH = Object.fromEntries(['add', 'edit', 'delete', 'page', 'info'].map(k =>
  [k === 'delete' ? 'remove' : k, `/api/lowcode/normal/dify/app/table/record/${k}`]));
const HINT = {
  missing_base_url: '请填写「服务地址」（https://域名，不带 /api）。',
  insecure_base_url: '服务地址必须使用 https；明文 http 会泄露访问令牌。',
  missing_token: '请填写「访问令牌」（Bearer 之后的内容）。',
  placeholder_config: '连接设置未生效：存在未替换的 ${...}，请填写服务地址与令牌。',
  unauthorized: '令牌无效或过期，请更新「访问令牌」。',
  forbidden: '令牌无该表访问权限。',
  not_found: '接口不存在，检查服务地址是否带 /api。',
  timeout: '请求超时，可增大 REQUEST_TIMEOUT_MS。',
  response_stream_error: '响应中断，勿重复提交同一写入。',
  kits_lowcode_error_table_config_not_found: '组织编码或表名未配置，检查 app_name/table_name。'
};
const redact = (v, max = 300) => {
  const s = String(v ?? '')
    .replace(/Bearer\s+[A-Za-z0-9._+\/=-]+/gi, 'Bearer ****')
    .replace(/["']?(client_token|access_token|token|authorization|secret)["']?\s*[:=]\s*["']?[A-Za-z0-9._+\/=-]{8,}["']?/gi, '$1=****');
  return s.length > max ? s.slice(0, max) + '…（已截断）' : s;
};
const log = m => process.stderr.write(`[timus-runtime] ${redact(m, 500)}\n`);
const maskHost = raw => { try { return new URL(raw).protocol + '//***'; } catch (_) { return '(已配置)'; } };

function loadLocalEnv() {
  try {
    for (const line of fs.readFileSync(path.join(__dirname, '.env.local'), 'utf8').split(/\r?\n/)) {
      const m = /^\s*([\w]+)\s*=\s*["']?([^"'\r\n]*)["']?\s*$/.exec(line);
      if (m && process.env[m[1]] === undefined) process.env[m[1]] = m[2];
    }
  } catch (_) {}
}

function config() {
  const rawBase = (process.env.API_BASE_URL || '').trim();
  const rawToken = (process.env.CLIENT_TOKEN || '').trim();
  const unresolved = [rawBase, rawToken].some(v => /\$\{[^}]+\}/.test(v));
  let base = '', insecure = false;
  if (!unresolved && rawBase) {
    if (/^http:\/\//i.test(rawBase)) insecure = true;
    else {
      const url = /^https:\/\//i.test(rawBase) ? rawBase : 'https://' + rawBase;
      base = (url.match(/^(https:\/\/[^/]+)/i) || [''])[0];
    }
  }
  const t = Number(process.env.REQUEST_TIMEOUT_MS);
  return { base, token: unresolved ? '' : rawToken.replace(/^bearer\s+/i, ''), unresolved, insecure, timeout: t > 0 ? t : TIMEOUT };
}

const fail = (errorCode, status = 0, extra = {}) => ({ ok: false, status, error: { errorCode, ...extra } });
function bodyError(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return null;
  const raw = typeof data.code === 'string' ? data.code.trim() : '';
  const ok = ['0', '200', 'ok', 'success'].includes(raw.toLowerCase());
  const code = typeof data.errorCode === 'string' && data.errorCode.trim() ? data.errorCode.trim() : raw && !ok && data.success !== true ? raw : '';
  if (!code && data.success !== false) return null;
  return { errorPath: data.errorPath, errorCode: code || 'upstream_failure', errorMessage: data.errorMessage || data.message || '', traceId: data.traceId };
}

async function callApi({ path: endpoint, query, body }) {
  const { base, token, timeout, unresolved, insecure } = config();
  if (unresolved) return fail('placeholder_config');
  if (insecure) return fail('insecure_base_url');
  if (!base) return fail('missing_base_url');
  if (!token) return fail('missing_token');
  let target;
  try { target = new URL(base + endpoint); } catch (_) { return fail('invalid_base_url', 0, { errorMessage: '服务地址格式不合法' }); }
  for (const [k, v] of Object.entries(query || {})) if (v != null && v !== '') target.searchParams.set(k, String(v));
  log('POST ' + target.pathname + ' token=****');
  const headers = { Authorization: 'Bearer ' + token, Accept: 'application/json', 'User-Agent': 'timus-runtime-connector/' + VERSION };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  let resp;
  try {
    resp = await fetch(target, { method: 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(timeout) });
  } catch (e) {
    const to = /Timeout|Abort/.test(e.name || '') || /请求超时/.test(e.message || '');
    return fail(to ? 'timeout' : 'network_error', 0, to ? {} : { errorMessage: redact('无法连接目标服务：' + e.message) });
  }
  let text;
  try { text = (await resp.text()).trim(); } catch (e) { return fail('response_stream_error', 0, { errorMessage: redact('响应流中断：' + e.message) }); }
  let data = text || null;
  if (text) { try { data = JSON.parse(text); } catch (_) {} }
  const status = resp.status, failure = bodyError(data);
  if (status < 200 || status >= 300 || failure) {
    const error = failure || {
      errorCode: status === 401 ? 'unauthorized' : status === 403 ? 'forbidden' : status === 404 ? 'not_found' : 'http_' + status,
      errorMessage: typeof data === 'string' ? redact(data, 500) : '接口返回 HTTP ' + status
    };
    return { ok: false, status, data, error };
  }
  return { ok: true, status, data };
}

class ToolError extends Error {}
const bad = m => { throw new ToolError(m); };
const need = (ok, m) => { if (!ok) bad(m); };
const nonEmpty = v => typeof v === 'string' && !!v.trim();
const arrArg = (a, k) => {
  const v = a[k];
  if (v === undefined || v === null) return undefined;
  need(Array.isArray(v), `参数 ${k} 必须是数组`);
  return v;
};
const items = (list, label, fn) => (list || []).map((it, i) => {
  const at = `${label}[${i}]`;
  need(it && typeof it === 'object' && !Array.isArray(it), `${at} 必须是对象`);
  return fn(it, at);
});
const nameOf = (it, at) => { need(nonEmpty(it.name), `${at}.name 必填`); return it.name; };
const fields = list => {
  need(list && list.length, 'fields 至少一项');
  return items(list, 'fields', (it, at) => {
    need(Object.prototype.hasOwnProperty.call(it, 'value'), `${at}.value 必填`);
    return { name: nameOf(it, at), value: it.value };
  });
};
const queries = (list, label) => items(list, label, (it, at) => {
  const o = { name: nameOf(it, at) };
  if (it.operator != null && it.operator !== '') {
    need(OPERATORS.includes(it.operator), `${at}.operator 只能是 ${OPERATORS.join('/')}`);
    o.operator = it.operator;
  }
  if (it.value != null) {
    need(['string', 'number', 'boolean'].includes(typeof it.value), `${at}.value 必须是字符串`);
    o.value = String(it.value);
  }
  return o;
});
const composite = list => items(list, 'composite_query', (g, at) => {
  const inner = arrArg(g, 'query_fields');
  need(inner && inner.length, `${at}.query_fields 不能为空`);
  const o = { queryFieldList: queries(inner, `${at}.query_fields`) };
  if (g.conjunction != null && g.conjunction !== '') {
    need(g.conjunction === 'AND' || g.conjunction === 'OR', `${at}.conjunction 只能是 AND 或 OR`);
    o.conjunction = g.conjunction;
  }
  return o;
});
const sorts = list => items(list, 'sort_fields', (it, at) => {
  const o = { name: nameOf(it, at) };
  if (it.ascend != null) {
    need(typeof it.ascend === 'boolean', `${at}.ascend 必须是布尔值`);
    o.ascend = it.ascend;
  }
  return o;
});
const returns = list => (list || []).map((s, i) => {
  need(nonEmpty(s), `return_fields[${i}] 必须是字段名字符串`);
  return { name: s.trim() };
});
const locator = (a, action) => {
  const id = nonEmpty(a.record_id) ? a.record_id.trim() : '';
  const q = arrArg(a, 'query_fields');
  need(id || q, `record_id 与 query_fields 至少提供一个（唯一定位要${action}的记录）`);
  return { ...(id ? { id } : {}), ...(q ? { queryFieldList: queries(q, 'query_fields') } : {}) };
};

const call = (op, a, record, query) => {
  need(nonEmpty(a.app_name) && nonEmpty(a.table_name), 'app_name 与 table_name 必填');
  return callApi({ path: PATH[op], query, body: { appName: a.app_name, tableName: a.table_name, record } });
};
const add = a => call('add', a, { payloadFieldList: fields(a.fields) });
const edit = a => { const r = locator(a, '修改'); r.payloadFieldList = fields(a.fields); return call('edit', a, r); };
const remove = a => call('remove', a, locator(a, '删除'));
function page(a) {
  need(nonEmpty(a.app_name) && nonEmpty(a.table_name), 'app_name/table_name 必填');
  const pageSize = a.page_size == null ? '' : String(a.page_size).trim();
  need(/^[1-9]\d*$/.test(pageSize), 'page_size 必须是正整数字符串');
  const r = {};
  if (a.conjunction) {
    need(a.conjunction === 'AND' || a.conjunction === 'OR', 'conjunction 只能是 AND 或 OR');
    r.conjunction = a.conjunction;
  }
  const q = arrArg(a, 'query_fields'), c = arrArg(a, 'composite_query');
  need(!(q && c), 'query_fields 与 composite_query 二选一');
  if (q) r.queryFieldList = queries(q, 'query_fields');
  if (c) r.compositeQueryFieldList = composite(c);
  const s = arrArg(a, 'sort_fields'); if (s) r.sortFieldList = sorts(s);
  const ret = arrArg(a, 'return_fields'); if (ret) r.payloadFieldList = returns(ret);
  const query = { pageNum: nonEmpty(a.page_num) ? a.page_num.trim() : '1', pageSize };
  if (nonEmpty(a.page_token)) query.pageToken = a.page_token.trim();
  return callApi({ path: PATH.page, query, body: { appName: a.app_name, tableName: a.table_name, record: r } });
}
const get = a => { need(nonEmpty(a.record_id), 'record_id 必填'); return call('info', a, { id: a.record_id }); };

const str = description => ({ type: 'string', description });
const arr = (description, items, minItems) => ({ type: 'array', description, ...(minItems ? { minItems } : {}), items });
const obj = (properties, required) => ({ type: 'object', properties, required, additionalProperties: false });
const desc = (schema, description) => ({ ...schema, description });

const OPERATORS = ['eq', 'neq', 'like', 'nlike', 'gt', 'ge', 'lt', 'le', 'is', 'isnot'];
const APP = str('组织编码（teamCode），如 03.TASK.TIMUS');
const TABLE = str('平台配置的元数据表名，如 Backlog');
const RID = str('记录 id，由 apaas_page_records / apaas_get_record 获取');
const FIELDS = arr('字段列表；字段名为平台内部标识（如 sys.to_do），value 为任意 JSON',
  obj({ name: str('字段名'), value: { description: '任意 JSON 值' } }, ['name', 'value']), 1);
const QUERY_ITEM = obj({ name: str('字段名'), operator: { type: 'string', enum: OPERATORS, description: '操作符，默认 eq；无值字段用 is/isnot' }, value: str('字符串值；日期可用 today 等') }, ['name']);
const QUERY = arr('简单查询条件；operator 默认 eq', QUERY_ITEM, 1);
const SORT = arr('排序字段', obj({ name: str('字段名'), ascend: { type: 'boolean', description: '正序，默认 true' } }, ['name']));
const COMPOSITE = arr('复杂查询：条件组按 conjunction 连接，与 query_fields 二选一',
  obj({ conjunction: { type: 'string', enum: ['AND', 'OR'], description: '组内连接方式，默认 AND' }, query_fields: arr('组内条件', QUERY_ITEM, 1) }, ['query_fields']), 1);
const RETURNS = arr('返回的字段名数组；省略则按服务端默认', str('字段名'));

const TOOLS = [
  { name: 'apaas_add_record', description: '新增一条记录。先查询同表确认字段结构。',
    inputSchema: obj({ app_name: APP, table_name: TABLE, fields: FIELDS }, ['app_name', 'table_name', 'fields']), handler: add },
  { name: 'apaas_edit_record', description: '修改一条记录。record_id 或 query_fields 定位（优先 id），fields 为新值。',
    inputSchema: obj({ app_name: APP, table_name: TABLE, record_id: RID, query_fields: desc(QUERY, '唯一查询条件'), fields: FIELDS }, ['app_name', 'table_name', 'fields']), handler: edit },
  { name: 'apaas_delete_record', description: '删除一条记录（不可撤销，须先与用户确认）。id 或 query_fields 定位。',
    inputSchema: obj({ app_name: APP, table_name: TABLE, record_id: RID, query_fields: desc(QUERY, '唯一查询条件') }, ['app_name', 'table_name']), handler: remove },
  { name: 'apaas_page_records', description: '分页查询；也是取 id 与真实字段名的主要方式。',
    inputSchema: obj({
      app_name: APP, table_name: TABLE,
      page_num: str('页码，从 1 开始'), page_size: str('每页条数，如 10/20/50'),
      page_token: str('飞书数据源续页 token，不与 page_num 混用'),
      conjunction: { type: 'string', enum: ['AND', 'OR'], description: '条件连接方式，默认 AND' },
      query_fields: QUERY, composite_query: COMPOSITE, sort_fields: SORT, return_fields: RETURNS
    }, ['app_name', 'table_name', 'page_size']), handler: page },
  { name: 'apaas_get_record', description: '按 id 查一条记录详情。',
    inputSchema: obj({ app_name: APP, table_name: TABLE, record_id: RID }, ['app_name', 'table_name', 'record_id']), handler: get }
];
const TOOL_MAP = new Map(TOOLS.map(t => [t.name, t]));

const send = m => process.stdout.write(JSON.stringify(m) + '\n');
const result = (id, value) => send({ jsonrpc: '2.0', id, result: value });
const rpcError = (id, code, message) => send({ jsonrpc: '2.0', id, error: { code, message } });

function errorText(status, error) {
  const code = error?.errorCode || 'unknown_error';
  const business = status >= 200 && status < 300;
  const head = !status ? '无法调用 Timus Runtime' : business ? '调用失败（业务错误）' : `调用失败（HTTP ${status}）`;
  const lines = [head];
  if (error?.errorMessage) lines.push('原因：' + redact(error.errorMessage));
  if (error?.errorPath) lines.push('路径：' + redact(error.errorPath));
  lines.push('错误码：' + code);
  if (error?.traceId) lines.push('traceId：' + redact(error.traceId));
  if (HINT[code]) lines.push('建议：' + HINT[code]);
  return lines.join('\n');
}
function trimStrings(value, limit) {
  if (typeof value === 'string') return value.length > limit ? value.slice(0, limit) + '…' : value;
  if (Array.isArray(value)) return value.map(item => trimStrings(item, limit));
  if (value && typeof value === 'object') {
    const out = {};
    for (const [key, item] of Object.entries(value)) out[key] = trimStrings(item, limit);
    return out;
  }
  return value;
}
function toolResult(resp) {
  if (!resp.ok) return { content: [{ type: 'text', text: errorText(resp.status, resp.error) }], isError: true };
  const d = resp.data === null || resp.data === undefined ? { data: null } : resp.data;
  let raw = typeof d === 'string' ? d : JSON.stringify(d);
  if (raw.length > 4000 && typeof d === 'object' && d !== null) {
    const clipped = trimStrings(d, 200);
    clipped._truncated = true;
    raw = JSON.stringify(clipped);
  }
  return { content: [{ type: 'text', text: redact(raw, 4000) }] };
}
async function callTool(id, params) {
  const name = params?.name, args = params?.arguments || {};
  if (typeof name !== 'string') return rpcError(id, -32602, '缺少 name');
  const tool = TOOL_MAP.get(name);
  if (!tool) return rpcError(id, -32602, '未知工具：' + name);
  if (!args || typeof args !== 'object' || Array.isArray(args)) return rpcError(id, -32602, 'arguments 必须是对象');
  try { result(id, toolResult(await tool.handler(args))); }
  catch (e) {
    if (e instanceof ToolError) return result(id, { content: [{ type: 'text', text: '参数错误：' + e.message }], isError: true });
    log('工具 ' + name + ' 异常：' + redact(e?.stack || e));
    result(id, { content: [{ type: 'text', text: '工具异常：' + redact(e?.message || String(e)) }], isError: true });
  }
}
function handle(m) {
  if (!m || typeof m !== 'object' || m.id === undefined || m.id === null) return;
  const { id, method, params } = m;
  if (m.jsonrpc !== '2.0') return rpcError(id, -32600, 'jsonrpc 必须为 2.0');
  switch (method) {
    case 'initialize': {
      const requested = params?.protocolVersion;
      const supported = ['2024-11-05', '2025-03-26'];
      return result(id, {
        protocolVersion: supported.includes(requested) ? requested : '2024-11-05',
        capabilities: { tools: { listChanged: false } },
        serverInfo: { name: NAME, version: VERSION },
        instructions: 'Timus Runtime 组织元数据连接器。先查询确认字段结构，再增删改。'
      });
    }
    case 'ping': return result(id, {});
    case 'tools/list': return result(id, { tools: TOOLS.map(({ name, description, inputSchema }) => ({ name, description, inputSchema })) });
    case 'tools/call': return callTool(id, params).catch(e => { log('tools/call 失败：' + redact(e?.stack || e)); rpcError(id, -32603, '内部错误'); });
    case 'resources/list': return result(id, { resources: [] });
    case 'prompts/list': return result(id, { prompts: [] });
    default: return rpcError(id, -32601, '不支持的方法：' + String(method));
  }
}
function start() {
  const c = config();
  log(`MCP 已启动 baseUrl=${c.base ? maskHost(c.base) : '(未配置)'} token=${c.token ? '****' : '(未配置)'} scheme=${c.insecure ? 'http(已拒绝)' : 'https'}`);
  const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
  rl.on('line', line => {
    if (!line.trim()) return;
    if (line.length > 1000000) return rpcError(null, -32600, '消息过大');
    let m;
    try { m = JSON.parse(line.trim()); } catch (_) { return rpcError(null, -32700, 'JSON 解析失败'); }
    try { handle(m); } catch (e) { log('消息处理异常：' + redact(e?.stack || e)); if (m?.id != null) rpcError(m.id, -32603, '内部错误'); }
  });
  rl.on('close', () => log('stdin 已关闭'));
}
module.exports = { NAME, VERSION, config, fail, bodyError, redact, errorText, toolResult, trimStrings, handle, start, TOOLS, OPERATORS };

if (require.main === module) {
  const argv = process.argv.slice(2);
  if (argv.includes('--version') || argv.includes('-v')) process.stdout.write(`${NAME} ${VERSION}\n`);
  else if (argv.includes('--help') || argv.includes('-h')) process.stdout.write([
    'Timus Runtime MCP Server（stdio）',
    '用法：API_BASE_URL=https://domain CLIENT_TOKEN=xxx node server.js',
    '  --local-env  读取 .env.local（仅本地调试，凭据视为已泄露）',
    '  --version/-v 输出版本',
    '环境变量：API_BASE_URL（仅 https）、CLIENT_TOKEN 必填；REQUEST_TIMEOUT_MS 默认 60000'
  ].join('\n') + '\n');
  else {
    if (argv.includes('--local-env')) loadLocalEnv();
    start();
  }
}
