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
  console: { error() {}, log() {}, warn() {} }, fetch: (...a) => gemini(...a) });
vm.runInContext(src, ctx);
const worker = ctx.worker;

const SITE = 'https://hanzi.lipu.dev';
function fakeEnv({ mnemonics = [], count = 1 } = {}) {
  const sql = [];   // [statement, args] of every write (and of .first(), which the counters use)
  const DB = {
    prepare(q) {
      const st = { q, args: [], bind(...a) { st.args = a; return st; },
        all: async () => ({ results: mnemonics }),
        first: async () => { sql.push([q, st.args]); return { n: count }; },
        run: async () => { sql.push([q, st.args]); return {}; } };
      return st;
    },
    batch: async s => { s.forEach(st => sql.push([st.q, st.args])); return s; },
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

test('the Yandex verification file is served at its exact address (200, no redirect)', async () => {
  const { env } = fakeEnv();
  let asked = null;
  env.ASSETS = { fetch: async u => { asked = new URL(u).pathname; return new Response('Verification: 075f1191e804f3a2'); } };
  const r = await worker.fetch(new Request(SITE + '/yandex_075f1191e804f3a2.html'), env);
  assert.equal(r.status, 200);
  assert.equal(asked, '/yandex_075f1191e804f3a2');
});

// anonymous rate-limit keys: HMAC of the IP with IP_HASH_SECRET (a plain SHA-256 of an IPv4 is brute-forceable)
const b64u = buf => Buffer.from(buf).toString('base64url');
const usageKeys = sql => sql.filter(([q]) => q.includes('INTO usage')).map(([, a]) => a[0]);
test('anonymous limits are keyed by an HMAC of the IP when IP_HASH_SECRET is set', async () => {
  gemini = () => { throw new Error('down'); };
  const req = () => post('/api/translate', { zh: '水' }, { 'CF-Connecting-IP': '203.0.113.7' });
  const plain = 't:ip:' + b64u(await crypto.subtle.digest('SHA-256', new TextEncoder().encode('hanzi-burst:203.0.113.7'))).slice(0, 22);
  const a = fakeEnv(); await worker.fetch(req(), a.env);
  assert.equal(usageKeys(a.sql)[0], plain);                  // no secret: old key, still works
  const b = fakeEnv(); b.env.IP_HASH_SECRET = 'test-secret'; await worker.fetch(req(), b.env);
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode('test-secret'), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const mac = 't:ip:' + b64u(await crypto.subtle.sign('HMAC', key, new TextEncoder().encode('hanzi-burst:203.0.113.7'))).slice(0, 22);
  assert.equal(usageKeys(b.sql)[0], mac);
  assert.notEqual(mac, plain);
});

// /api/known needs a session: sign one the way the worker does
async function sessionCookie(secret) {
  const enc = new TextEncoder();
  const body = b64u(enc.encode(JSON.stringify({ sub: 'u1', exp: Math.floor(Date.now() / 1000) + 60 })));
  const key = await crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return `hb_session=${body}.${b64u(await crypto.subtle.sign('HMAC', key, enc.encode(body)))}`;
}
const putKnown = async (env, body) => worker.fetch(new Request(SITE + '/api/known', { method: 'PUT', body: JSON.stringify(body),
  headers: { 'Content-Type': 'application/json', Origin: SITE, Cookie: await sessionCookie(env.SESSION_SECRET) } }), env);

test('known: only hanzi/kana are added; markup characters are dropped', async () => {
  const { env, sql } = fakeEnv(); env.SESSION_SECRET = 's';
  const r = await putKnown(env, { add: ['水', 'マ', '<', '"', 'ab', 7, '𠔼'] });
  assert.equal(r.status, 200);
  const added = sql.filter(([q]) => q.includes('INTO known')).map(([, a]) => a[1]);
  assert.deepEqual(added, ['水', 'マ', '𠔼']);
});

test('known: legacy junk can still be removed', async () => {
  const { env, sql } = fakeEnv(); env.SESSION_SECRET = 's';
  await putKnown(env, { remove: ['<'] });
  assert.ok(sql.some(([q, a]) => q.startsWith('DELETE FROM known') && a[1] === '<'));
});

test('known: a user is capped (409 past the limit, and the INSERT itself checks it)', async () => {
  const full = fakeEnv({ count: 20000 }); full.env.SESSION_SECRET = 's';
  const r = await putKnown(full.env, { add: ['水'] });
  assert.equal(r.status, 409);
  assert.ok(!full.sql.some(([q]) => q.includes('INTO known')));
  const ok = fakeEnv({ count: 10 }); ok.env.SESSION_SECRET = 's';
  assert.equal((await putKnown(ok.env, { add: ['水'] })).status, 200);
  assert.ok(ok.sql.some(([q, a]) => q.includes('INTO known') && q.includes('COUNT(*)') && a[3] === 20000));
});
