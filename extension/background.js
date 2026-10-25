// Chrome: service worker loads the helpers itself; Firefox: manifest background.scripts lists them.
if (typeof importScripts === 'function') { self.window = self; importScripts('common.js', 'ja.js'); }
// Offline lookup. Data shards are copied from site/data by scripts/build_extension.py.
const HAN = /[㐀-鿿]/;
const MAX_DEPTH = 3;
let trad = null;
const tradMap = () => trad || (trad = fetch(chrome.runtime.getURL('data/trad.json')).then(r => r.json()).catch(() => ({})));

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
    const et = c && c.etymology; const hint = et ? ((lang === 'ru' && et.hint_ru) || et.hint || '') : '';
    return { ch, def: pick(c), hint, py: ((c && c.pinyin) || []).slice(0, 2).join(' / '), parts: kids ? kids.map(k => tree(k, depth + 1, path.concat(ch))) : [] };
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

// Pinyin over page text: per text, segments [text, pinyin|''] — longest CC-CEDICT word first (up to 6 characters),
// its syllables spread over its characters; a lone character gets its main reading. Traditional text is looked up
// through trad.json but shown as is.
async function annotate(texts) {
  const map = await tradMap();
  const simp = s => [...s].map(c => map[c] || c);
  const han = [...new Set(texts.flatMap(t => simp(t).filter(c => HAN.test(c))))];
  const words = {}, chars = {};
  await Promise.all([...new Set(han.map(shardKey))].map(async k => {
    const [w, c] = await Promise.all([shard('words', k), shard('chars', k)]);
    Object.assign(words, w); Object.assign(chars, c);
  }));
  const one = c => (((chars[c] || {}).pinyin || [])[0] || '');
  return texts.map(t => {
    const cs = [...t], ss = simp(t), out = [];
    const push = (txt, py) => { const l = out[out.length - 1]; if (!py && l && !l[1]) l[0] += txt; else out.push([txt, py]); };
    for (let i = 0; i < cs.length;) {
      if (!HAN.test(ss[i])) { push(cs[i], ''); i++; continue; }
      let m = Math.min(6, cs.length - i);
      for (; m > 1; m--) {
        const w = ss.slice(i, i + m);
        if (w.every(c => HAN.test(c)) && words[w.join('')] && words[w.join('')][0].split(' ').length === m) break;
      }
      if (m > 1) words[ss.slice(i, i + m).join('')][0].split(' ').forEach((p, j) => push(cs[i + j], p.toLowerCase()));
      else push(cs[i], one(ss[i]));
      i += m;
    }
    return out;
  });
}

// Context menu: look up the selection; pinyin over this page.
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({ id: 'hb-look', title: 'Hanzi Burst: “%s”', contexts: ['selection'] });
    chrome.contextMenus.create({ id: 'hb-ruby', title: 'Hanzi Burst: pinyin on this page (on/off)', contexts: ['page'] });
  });
});
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (!tab || tab.id < 0) return;
  try { chrome.tabs.sendMessage(tab.id, { type: info.menuItemId === 'hb-ruby' ? 'ctx-ruby' : 'ctx-look' }, { frameId: info.frameId || 0 }); } catch (e) {}
});

// Japanese: words by site/ja.js (JMdict shards data/ja), kanji readings and meanings from data/kanji.
async function lookupJa(raw, lang, hover) {
  const r = await JA.analyze([...raw].slice(0, hover ? 12 : 30).join(''), shard);
  let words = r.words.filter(w => !w.punct);
  if (hover) words = words.slice(0, 1);
  if (!words.length) return null;
  const K = {};
  const load = async list => Promise.all([...new Set(list.map(shardKey))].map(async k => {
    const d = await shard('kanji', k); list.forEach(c => { if (d[c]) K[c] = d[c]; });
  }));
  const kan = [...new Set(words.flatMap(w => w.chars).filter(c => HAN.test(c)))].slice(0, hover ? 4 : 8);
  await load(kan);
  const parts = c => (K[c] && K[c].components || []).map((p, i) => ((K[c].orig || [])[i]) || p);
  await load([...new Set(kan.flatMap(parts))].filter(c => !K[c]));
  const mean = k => (k && ((lang === 'ru' && k.ru) || (k.en || []).slice(0, 4).join(', '))) || '';
  return {
    ja: true, text: r.zh,
    words: words.filter(w => w.reading || w.gloss).map(w => ({
      w: w.word, reading: w.reading, tr: lang === 'ru' ? w.cyr : w.lat, lemma: w.lemma,
      def: (lang === 'ru' && w.gloss_ru) || w.gloss || '' })),
    chars: kan.filter(c => K[c]).map(c => ({
      ch: c, def: mean(K[c]), on: (K[c].on || []).slice(0, 3).join('、'), kun: (K[c].kun || []).slice(0, 3).join('、'),
      parts: (K[c].components || []).map((p, i) => ({ ch: p, def: mean(K[p] || K[(K[c].orig || [])[i]]), parts: [] })) })),
  };
}

chrome.runtime.onMessage.addListener((msg, _s, send) => {
  if (msg && msg.type === 'open-learned') { chrome.tabs.create({ url: chrome.runtime.getURL('learned.html') }); return; }
  if (msg && msg.type === 'annotate') { annotate(msg.texts || []).then(send, () => send(null)); return true; }
  if (msg && msg.type === 'lookup' && msg.ja) { lookupJa(msg.text, msg.lang, !!msg.hover).then(send, () => send(null)); return true; }
  if (msg && msg.type === 'lookup') { lookup(msg.text, msg.lang, !!msg.hover).then(send, () => send(null)); return true; }
});
