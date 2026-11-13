// extension/background.js lookup() on small fixture shards (tests/js/fixtures/data), chrome.* and fetch stubbed.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const EXT = path.join(__dirname, '../../extension');
const DATA = path.join(__dirname, 'fixtures');
const noop = new Proxy(function () {}, { get: () => noop, apply: () => undefined });   // chrome.anything.anything()
const ctx = vm.createContext({
  chrome: { runtime: { getURL: p => p, onMessage: noop, onInstalled: noop }, contextMenus: noop, storage: noop, tabs: noop, action: noop },
  fetch: async url => {
    const f = path.join(DATA, url);
    return fs.existsSync(f) ? { ok: true, json: async () => JSON.parse(fs.readFileSync(f, 'utf8')) } : { ok: false, json: async () => ({}) };
  },
  console, URL, setTimeout,
});
for (const f of ['common.js', 'background.js']) vm.runInContext(fs.readFileSync(path.join(EXT, f), 'utf8'), ctx, { filename: f });
// results come from another realm: copy them so deepEqual compares plain arrays
const lookup = async (text, hover = true) => JSON.parse(JSON.stringify(await vm.runInContext('lookup', ctx)(text, 'en', hover)));
const flat = n => [n.ch, ...n.parts.map(flat)];

test('a traditional character with its own entry is broken down as itself (禰 = 礻 + 爾)', async () => {
  const r = await lookup('禰');
  assert.equal(r.chars[0].ch, '禰');
  assert.deepEqual(r.chars[0].parts.map(p => p.ch), ['礻', '爾']);
});

test('traditional word: matched in simplified, shown as on the page', async () => {
  const r = await lookup('漢字是');
  assert.equal(r.word.w, '漢字');
  assert.equal(r.word.pinyin, 'hàn zì');
  assert.deepEqual(r.chars.map(c => c.ch), ['漢', '字']);
  assert.deepEqual(r.chars[0].parts.map(p => p.ch), ['氵', '堇']);
});

test('traditional character without an entry falls back to simplified (後 → 后)', async () => {
  const r = await lookup('後');
  assert.equal(r.chars[0].ch, '后');
});

test('simplified text is unchanged; parts are never converted (你-style: 尔 stays 尔)', async () => {
  const r = await lookup('祢');
  assert.deepEqual(flat(r.chars[0]), ['祢', ['礻'], ['尔', ['⺈'], ['小']]]);
});

test('selection: no word, every character', async () => {
  const r = await lookup('字汉', false);
  assert.equal(r.word, null);
  assert.deepEqual(r.chars.map(c => c.ch), ['字', '汉']);
});
