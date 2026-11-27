'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const server = require('../server.js');

function useEnv(base, token) {
  process.env.API_BASE_URL = base;
  process.env.CLIENT_TOKEN = token;
  delete process.env.REQUEST_TIMEOUT_MS;
}

function captureStdout(t) {
  const original = process.stdout.write;
  const chunks = [];
  process.stdout.write = (chunk) => { chunks.push(String(chunk)); return true; };
  t.after(() => { process.stdout.write = original; });
  return () => chunks.join('').trim().split('\n').filter(Boolean).map(JSON.parse);
}

function mockFetch(t, impl) {
  const original = global.fetch;
  global.fetch = impl;
  t.after(() => { global.fetch = original; });
}

test('config: 无协议地址补 https，显式 http 被标记为不安全', (t) => {
  t.after(() => useEnv('', ''));
  useEnv('example.com', 'token-value');
  assert.equal(server.config().base, 'https://example.com');
  useEnv('http://example.com', 'token-value');
  const c = server.config();
  assert.equal(c.base, '');
  assert.equal(c.insecure, true);
});

test('config: 任意位置的未替换占位符均视为未配置', (t) => {
  t.after(() => useEnv('', ''));
  useEnv('https://${API_HOST}', '${CLIENT_TOKEN}');
  assert.equal(server.config().unresolved, true);
});

test('明文 http 不会发起请求，并返回 insecure_base_url', async (t) => {
  const lines = captureStdout(t);
  let called = false;
  mockFetch(t, async () => { called = true; throw new Error('不应发起请求'); });
  useEnv('http://example.com', 'token-value');
  await server.handle({ jsonrpc: '2.0', id: 1, method: 'tools/call',
    params: { name: 'apaas_page_records', arguments: { app_name: 'A', table_name: 'T', page_size: '10' } } });
  assert.equal(called, false);
  const text = lines()[0].result.content[0].text;
  assert.match(text, /insecure_base_url/);
  assert.match(text, /必须使用 https/);
});

test('bodyError: 识别 HTTP 200 中的业务错误', () => {
  assert.equal(server.bodyError({ code: '0', rows: [] }), null);
  assert.equal(server.bodyError({ errorCode: 'forbidden', errorMessage: '无权限' }).errorCode, 'forbidden');
  assert.equal(server.bodyError({ success: false }).errorCode, 'upstream_failure');
});

test('toolResult: 超长对象裁剪后仍是合法 JSON 并标记 _truncated', () => {
  const long = 'x'.repeat(9000);
  const result = server.toolResult({ ok: true, data: { rows: [{ text: long }] } });
  const parsed = JSON.parse(result.content[0].text);
  assert.equal(parsed._truncated, true);
  assert.ok(parsed.rows[0].text.length <= 201);
});

test('page_size 非正整数时返回参数错误', async (t) => {
  const lines = captureStdout(t);
  mockFetch(t, async () => { throw new Error('不应发起请求'); });
  useEnv('https://example.com', 'token-value');
  await server.handle({ jsonrpc: '2.0', id: 2, method: 'tools/call',
    params: { name: 'apaas_page_records', arguments: { app_name: 'A', table_name: 'T', page_size: 'abc' } } });
  assert.match(lines()[0].result.content[0].text, /page_size 必须是正整数字符串/);
  assert.equal(lines()[0].result.isError, true);
});

test('composite_query.conjunction 只允许 AND/OR', async (t) => {
  const lines = captureStdout(t);
  useEnv('https://example.com', 'token-value');
  await server.handle({ jsonrpc: '2.0', id: 3, method: 'tools/call',
    params: { name: 'apaas_page_records', arguments: { app_name: 'A', table_name: 'T', page_size: '10',
      composite_query: [{ conjunction: 'XOR', query_fields: [{ name: 'S.状态' }] }] } } });
  assert.match(lines()[0].result.content[0].text, /conjunction 只能是 AND 或 OR/);
});

test('initialize: 协商受支持的协议版本，拒绝非法 jsonrpc', (t) => {
  const lines = captureStdout(t);
  server.handle({ jsonrpc: '2.0', id: 4, method: 'initialize', params: { protocolVersion: '2025-03-26' } });
  server.handle({ jsonrpc: '2.0', id: 5, method: 'initialize', params: { protocolVersion: '1999-01-01' } });
  server.handle({ jsonrpc: '1.0', id: 6, method: 'initialize' });
  assert.equal(lines()[0].result.protocolVersion, '2025-03-26');
  assert.equal(lines()[1].result.protocolVersion, '2024-11-05');
  assert.equal(lines()[2].error.code, -32600);
});

test('tools/list: operator 枚举与技能文档一致', (t) => {
  const lines = captureStdout(t);
  server.handle({ jsonrpc: '2.0', id: 7, method: 'tools/list' });
  const page = lines()[0].result.tools.find((tool) => tool.name === 'apaas_page_records');
  const operator = page.inputSchema.properties.query_fields.items.properties.operator;
  assert.deepEqual(operator.enum, server.OPERATORS);
});
