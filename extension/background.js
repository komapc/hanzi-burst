// Offline lookup. Data shards are copied from site/data by scripts/build_extension.py.
const HAN = /[㐀-鿿]/;
const shardKey = ch => ch.codePointAt(0).toString(16).slice(0, -2);
const cache = {};
const shard = (kind, k) => cache[kind + k] || (cache[kind + k] =
  fetch(chrome.runtime.getURL(`data/${kind}/${k}.json`)).then(r => (r.ok ? r.json() : {})).catch(() => ({})));
let trad = null;
const tradMap = () => trad || (trad = fetch(chrome.runtime.getURL('data/trad.json')).then(r => r.json()).catch(() => ({})));

async function lookup(raw, lang) {
  const map = await tradMap();
  const text = [...raw].slice(0, 30).map(c => map[c] || c).join('');
  const han = [...text].filter(c => HAN.test(c));
  if (!han.length) return null;
  const uniq = [...new Set(han)];
  const words = {};
  await Promise.all([...new Set(uniq.map(shardKey))].map(async k => Object.assign(words, await shard('words', k))));
  const w = words[text] ? text : null;               // whole selection is a dictionary word
  const chars = {};
  const load = async list => {
    await Promise.all([...new Set(list.map(shardKey))].map(async k => {
      const cd = await shard('chars', k);
      list.filter(c => shardKey(c) === k && cd[c]).forEach(c => { chars[c] = cd[c]; });
    }));
  };
  await load(uniq);
  const parts = [...new Set(uniq.flatMap(c => (chars[c] && chars[c].components) || []))].filter(c => !chars[c]);
  await load(parts);
  const pick = c => c && ((lang === 'ru' && c.definition_ru) || c.definition) || '';
  const view = ch => {
    const c = chars[ch]; if (!c) return { ch };
    return {
      ch, pinyin: (c.pinyin || []).join(' / '), def: pick(c), radical: c.radical || '',
      atomic: !!c.atomic,
      parts: (c.components || []).map(p => ({ ch: p, def: pick(chars[p]) })),
    };
  };
  return {
    text, converted: text !== raw.slice(0, 30),
    word: w ? { w, pinyin: words[w][0], def: words[w][1] } : null,
    chars: uniq.slice(0, 8).map(view),
  };
}

chrome.runtime.onMessage.addListener((msg, _s, send) => {
  if (msg && msg.type === 'lookup') { lookup(msg.text, msg.lang).then(send, () => send(null)); return true; }
});
