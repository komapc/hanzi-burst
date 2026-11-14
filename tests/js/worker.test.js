// worker/index.js routes with D1, ASSETS and Gemini stubbed: node --test tests/js/*.test.js
// The worker is an ES module; CI runs Node 20 without a package.json, so it is loaded through vm like background.js.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const src = fs.readFileSync(path.join(__dirname, '../../worker/index.js'), 'utf8').replace('export default', 'globalThis.worker =');
let gemini = () => { throw new Error('no network'); };   // what fetch() to Gemini answers in the current test
const ctx = vm.createContext({ Response, Request, URL, URLSearchParams, crypto, TextEncoder, TextDecoder, btoa, atob,
  console: { error() {}, log() {} }, fetch: (...a) => gemini(...a) });
vm.runInContext(src, ctx);
const worker = ctx.worker;

const SITE = 'https://hanzi.lipu.dev';
function fakeEnv({ mnemonics = [] } = {}) {
  const sql = [];   // [statement, args] of every write
  const DB = {
    prepare(q) {
      const st = { args: [], bind(...a) { st.args = a; return st; },
        all: async () => ({ results: mnemonics }),
        first: async () => { sql.push([q, st.args]); return { n: 1 }; },
        run: async () => { sql.push([q, st.args]); return {}; } };
      return st;
    },
    batch: async s => s,
  };
  const ASSETS = { fetch: async () => new Response(JSON.stringify({ '水': { pinyin: ['shuǐ'], definition: 'water', components: [] } })) };
  return { env: { DB, ASSETS, GEMINI_MODEL: 'm', GEMINI_API_KEY: 'k', EXPLAIN_DAILY_LIMIT: '15', GLOBAL_DAILY_LIMIT: '300' }, sql };
}
const post = (p, body, headers = {}) => new Request(SITE + p, { method: 'POST', body: JSON.stringify(body),
  headers: { 'Content-Type': 'application/json', Origin: SITE, ...headers } });

test('cookie writes from another origin are refused, even a sibling *.lipu.dev', async () => {
  const { env, sql } = fakeEnv();
  const r = await worker.fetch(post('/api/explain', { ch: '水' }, { Origin: 'https://other.lipu.dev' }), env);
  assert.equal(r.status, 403);
  assert.equal(sql.length, 0);
});

test('explain and translate need JSON (a plain form cannot post them)', async () => {
  for (const p of ['/api/explain', '/api/translate']) {
    const r = await worker.fetch(post(p, { ch: '水', zh: '水' }, { 'Content-Type': 'text/plain' }), fakeEnv().env);
    assert.equal(r.status, 415, p);
  }
});

test('the extension may call translate (its Origin is not the site)', async () => {
  gemini = async () => new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: '{"translation": "water"}' }] } }] }));
  const r = await worker.fetch(post('/api/translate', { zh: '水', lang: 'en' }, { Origin: 'chrome-extension://abc' }), fakeEnv().env);
  assert.equal(r.status, 200);
  assert.equal((await r.json()).translation, 'water');
});

test('mnemonics are not cached by the browser: a new one shows after reload', async () => {
  const r = await worker.fetch(new Request(SITE + '/api/mnemonics?ch=水&lang=en'), fakeEnv().env);
  assert.equal(r.headers.get('Cache-Control'), 'no-cache');
});

test('translate has its own site-wide counter', async () => {
  gemini = () => { throw new Error('down'); };
  const { env, sql } = fakeEnv();
  const r = await worker.fetch(post('/api/translate', { zh: '水' }), env);
  assert.equal(r.status, 502);
  const ids = sql.map(([, a]) => a[0]);
  assert.ok(ids.includes('t:*'));
  assert.ok(!ids.includes('*'));
});

test('an empty Gemini answer is not stored as a mnemonic', async () => {
  gemini = async () => new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: '{"mnemonic": "  "}' }] } }] }));
  const { env, sql } = fakeEnv();
  const r = await worker.fetch(post('/api/explain', { ch: '水', lang: 'en' }), env);
  assert.equal(r.status, 502);
  assert.ok(!sql.some(([q]) => q.includes('INTO mnemonics')));
});

test('a good answer is stored', async () => {
  gemini = async () => new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: '{"mnemonic": "Rain drops"}' }] } }] }));
  const { env, sql } = fakeEnv();
  const r = await worker.fetch(post('/api/explain', { ch: '水', lang: 'en' }), env);
  assert.equal(r.status, 200);
  assert.ok(sql.some(([q, a]) => q.includes('INTO mnemonics') && a.includes('Rain drops')));
});
