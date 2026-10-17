// Offline lookup. Data shards are copied from site/data by scripts/build_extension.py.
const HAN = /[㐀-鿿]/;
const IDS_OP = /[⿰-⿻]/;
const MAX_DEPTH = 3;
const shardKey = ch => ch.codePointAt(0).toString(16).slice(0, -2);
const cache = {};
const shard = (kind, k) => cache[kind + k] || (cache[kind + k] =
  fetch(chrome.runtime.getURL(`data/${kind}/${k}.json`)).then(r => (r.ok ? r.json() : {})).catch(() => ({})));
let trad = null;
const tradMap = () => trad || (trad = fetch(chrome.runtime.getURL('data/trad.json')).then(r => r.json()).catch(() => ({})));

// Direct parts of a character from its IDS string; null when unknown or incomplete (a "？" hole).
function partsOf(ch, c) {
  if (!c || c.incomplete || c.radical === ch) return null;       // radicals are never split
  const d = c.decomposition || '';
  if (!d || /[？①-⑳]/.test(d)) return null;
  const p = [...d].filter(x => !IDS_OP.test(x));
  return p.length && !p.includes(ch) ? p : null;
}

async function lookup(raw, lang, hover) {
  const map = await tradMap();
  let text = [...raw].slice(0, hover ? 8 : 30).map(c => map[c] || c).join('');
  const han = [...text].filter(c => HAN.test(c));
  if (!han.length || (hover && !HAN.test([...text][0]))) return null;
  const words = {};
  await Promise.all([...new Set(han.map(shardKey))].map(async k => Object.assign(words, await shard('words', k))));
  let w = null;
  if (hover) {                                                    // longest dictionary word starting under the cursor
    const cs = [...text];
    for (let m = Math.min(6, cs.length); m >= 1; m--) { const s = cs.slice(0, m).join(''); if (m === 1 || words[s]) { text = s; w = m > 1 ? s : null; break; } }
  } else if (words[text]) w = text;
  const uniq = [...new Set([...text].filter(c => HAN.test(c)))];

  const chars = {};
  const load = async list => {
    await Promise.all([...new Set(list.map(shardKey))].map(async k => {
      const cd = await shard('chars', k);
      list.filter(c => shardKey(c) === k && cd[c]).forEach(c => { chars[c] = cd[c]; });
    }));
  };
  let level = uniq;
  for (let d = 0; d <= MAX_DEPTH && level.length; d++) {          // load the whole tree level by level
    await load(level);
    level = [...new Set(level.flatMap(c => partsOf(c, chars[c]) || []))].filter(c => !chars[c]);
  }
  const pick = c => (c && ((lang === 'ru' && c.definition_ru) || c.definition)) || '';
  const tree = (ch, depth, path) => {
    const c = chars[ch];
    const kids = depth < MAX_DEPTH && !path.includes(ch) ? partsOf(ch, c) : null;
    return { ch, def: pick(c), parts: kids ? kids.map(k => tree(k, depth + 1, path.concat(ch))) : [] };
  };
  const view = ch => {
    const c = chars[ch]; if (!c) return { ch, parts: [] };
    return { ...tree(ch, 0, []), pinyin: (c.pinyin || []).join(' / ') };
  };
  return {
    text, converted: !hover && text !== raw.slice(0, 30),
    word: w ? { w, pinyin: words[w][0], def: words[w][1] } : null,
    chars: uniq.slice(0, 8).map(view),
  };
}

chrome.runtime.onMessage.addListener((msg, _s, send) => {
  if (msg && msg.type === 'lookup') { lookup(msg.text, msg.lang, !!msg.hover).then(send, () => send(null)); return true; }
});
