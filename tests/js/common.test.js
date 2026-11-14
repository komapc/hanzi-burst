// Unit tests for extension/common.js: node --test tests/js/*.test.js
const test = require('node:test');
const assert = require('node:assert/strict');
const { shardKey, partsOf, stateOf, mergeKnown, sentenceIn } = require('../../extension/common.js');

test('shardKey: code point without the last two hex digits', () => {
  assert.equal(shardKey('學'), '5b');   // U+5B78
  assert.equal(shardKey('你'), '4f');   // U+4F60
});

test('partsOf: IDS parts, never for radicals or incomplete entries', () => {
  assert.deepEqual(partsOf('你', { decomposition: '⿰亻尔', radical: '亻' }), ['亻', '尔']);
  assert.equal(partsOf('口', { decomposition: '⿱？？', radical: '口' }), null);
  assert.equal(partsOf('書', { decomposition: '⿱聿？', radical: '曰' }), null);
  assert.equal(partsOf('X', { decomposition: '⿰AB', incomplete: true }), null);
  assert.equal(partsOf('X', null), null);
});

test('stateOf: known / allp / somep', () => {
  const t = { ch: '你', parts: [{ ch: '亻', parts: [] }, { ch: '尔', parts: [{ ch: '⺈', parts: [] }, { ch: '小', parts: [] }] }] };
  assert.equal(stateOf(t, new Set(['你'])), 'known');
  assert.equal(stateOf(t, new Set(['亻', '尔'])), 'allp');       // a known part covers its own leaves
  assert.equal(stateOf(t, new Set(['小'])), 'somep');
  assert.equal(stateOf(t, new Set()), '');
});

test('mergeKnown: union on first sync, unmarks propagate both ways', () => {
  assert.deepEqual(mergeKnown(['a'], ['b'], null).sort(), ['a', 'b']);
  assert.deepEqual(mergeKnown(['a', 'b'], ['a', 'b', 'c'], ['a', 'b', 'c']).sort(), ['a', 'b']);   // unmarked on the site
  assert.deepEqual(mergeKnown(['a', 'b', 'c'], ['a', 'b'], ['a', 'b', 'c']).sort(), ['a', 'b']);   // unmarked in the extension
});

test('mergeKnown: a missing or wiped site list never deletes ours', () => {
  assert.deepEqual(mergeKnown(null, ['a', 'b'], ['a', 'b']).sort(), ['a', 'b']);   // key absent
  assert.deepEqual(mergeKnown([], ['a', 'b'], ['a', 'b']).sort(), ['a', 'b']);     // none of base left: treated as reset
  assert.deepEqual(mergeKnown([], ['a'], ['a'], true), []);                        // site just saved: last one unmarked
});

test('sentenceIn: Chinese run between Latin text', () => {
  const s = 'Goodbye - 再见 (zài jiàn)';
  assert.deepEqual(sentenceIn(s, s.indexOf('见')), { text: '再见', at: 1 });
});

test('sentenceIn: cut at sentence ends, keeping the own one', () => {
  const s = '我饿了。最近的地铁站在哪里？谢谢';
  assert.deepEqual(sentenceIn(s, s.indexOf('铁')), { text: '最近的地铁站在哪里？', at: 4 });
});

test('sentenceIn: commas and quotes stay inside, the closing quote is kept', () => {
  const s = '他说：“我迷路了，你能帮我吗？”然后走了。';
  assert.equal(sentenceIn(s, s.indexOf('帮')).text, '他说：“我迷路了，你能帮我吗？”');
});

test('sentenceIn: no leading spaces or closing punctuation', () => {
  const s = '好。 」 我们走吧';
  assert.equal(sentenceIn(s, s.indexOf('走')).text, '我们走吧');
});

test('sentenceIn: too long gives null', () => {
  const s = '字'.repeat(150);
  assert.equal(sentenceIn(s, 75), null);
});
