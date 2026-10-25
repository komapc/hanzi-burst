const $ = id => document.getElementById(id);
const T = {
  ru: { title: 'Мои иероглифы', known: 'Известные иероглифы', parts: 'Части (радикалы) в известных иероглифах', ready: 'Готовы к изучению: все части известны', some: 'Знаю часть частей',
    empty: 'Пока ничего не отмечено. Наведите на иероглиф на любой странице и нажмите на его плитку в карточке.', loading: 'Загружаю…',
    sum: (n, p, r) => `Известно иероглифов: ${n}. Частей в них: ${p}. Готово к изучению: ${r}.`, hint: 'Список хранится только в этом браузере. Клик по иероглифу переключает отметку.',
    exp: 'Копировать список', imp: 'Вставить список', go: 'Добавить', x: 'Отмена', copied: 'Скопировано', ph: 'Вставьте иероглифы или JSON-список (как на hanzi.lipu.dev)' },
  en: { title: 'My characters', known: 'Known characters', parts: 'Parts (radicals) inside known characters', ready: 'Ready to learn: all parts known', some: 'Some parts known',
    empty: 'Nothing marked yet. Hover a character on any page and click its tile in the card.', loading: 'Loading…',
    sum: (n, p, r) => `Known characters: ${n}. Parts inside them: ${p}. Ready to learn: ${r}.`, hint: 'The list is stored only in this browser. Click a character to toggle it.',
    exp: 'Copy list', imp: 'Paste list', go: 'Add', x: 'Cancel', copied: 'Copied', ph: 'Paste characters or a JSON list (as on hanzi.lipu.dev)' },
};
let lang = (navigator.language || '').startsWith('ru') ? 'ru' : 'en', known = [], chars = {}, ready = false, core = [];
const t = k => T[lang][k];
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const HAN = /[㐀-鿿]/;

async function load(list) {                       // chars and all their descendants
  let need = [...list]; const done = new Set();
  while (need.length) {
    const batch = need.filter(c => !done.has(c)); need = [];
    batch.forEach(c => done.add(c));
    await Promise.all([...new Set(batch.map(shardKey))].map(async k => {
      const cd = await shard('chars', k);
      batch.filter(c => shardKey(c) === k && cd[c]).forEach(c => { chars[c] = cd[c]; (partsOf(c, cd[c]) || []).forEach(x => { if (!done.has(x)) need.push(x); }); });
    }));
  }
}
const treeOf = (ch, depth = 0) => { const p = depth < 6 ? partsOf(ch, chars[ch]) : null; return { ch, parts: p ? p.map(x => treeOf(x, depth + 1)) : [] }; };
const leavesOf = (n, acc = new Set(), top = true) => { if (!n.parts.length) { if (!top) acc.add(n.ch); } else n.parts.forEach(x => leavesOf(x, acc, false)); return acc; };
const def = ch => { const c = chars[ch] || {}; return (lang === 'ru' && c.definition_ru) || c.definition || ''; };
const short = d => (d || '').split(/[;,]/)[0].trim();
const card = (ch, cls) => `<button class="c ${cls}" data-ch="${esc(ch)}"><span class="p">${esc(((chars[ch] || {}).pinyin || [])[0] || '')}</span><span class="z">${esc(ch)}</span><span class="d">${esc(short(def(ch)))}</span></button>`;

function render() {
  document.documentElement.lang = lang; document.title = t('title') + ' — Hanzi Burst';
  $('h1').textContent = t('title'); $('exp').textContent = t('exp'); $('imp').textContent = t('imp'); $('ioGo').textContent = t('go'); $('ioX').textContent = t('x'); $('ta').placeholder = t('ph');
  if (!known.length) { setHTML($('out'), `<div class="empty">${t('empty')}</div>`); $('sum').textContent = ''; return; }
  if (!ready) { setHTML($('out'), `<p class="m">${t('loading')}</p>`); return; }
  const ks = new Set(known), parts = new Set();
  known.forEach(c => leavesOf(treeOf(c), parts));
  const rdy = [], som = [];
  core.filter(c => !ks.has(c) && chars[c] && partsOf(c, chars[c])).forEach(c => { const s = stateOf(treeOf(c), ks); if (s === 'allp') rdy.push(c); else if (s === 'somep') som.push(c); });
  $('sum').textContent = T[lang].sum(known.length, parts.size, rdy.length) + ' ' + t('hint');
  const sec = (title, arr, cls) => arr.length ? `<h2>${title} <small>${arr.length}</small></h2><div class="grid">${arr.map(c => card(c, cls)).join('')}</div>` : '';
  setHTML($('out'), sec(t('known'), known, 'k') + sec(t('parts'), [...parts].sort().filter(c => !ks.has(c)), '') + sec(t('ready'), rdy.slice(0, 60), 'a') + sec(t('some'), som.slice(0, 60), 's'));
}

const save = list => { known = [...new Set(list)]; chrome.storage.local.set({ known }); };
$('out').onclick = e => { const b = e.target.closest('button[data-ch]'); if (!b) return; const c = b.dataset.ch; save(known.includes(c) ? known.filter(x => x !== c) : [...known, c]); };
$('exp').onclick = async () => { await navigator.clipboard.writeText(JSON.stringify(known)); $('exp').textContent = t('copied'); setTimeout(render, 1200); };
$('imp').onclick = () => { $('io').hidden = false; $('ta').focus(); };
$('ioX').onclick = () => { $('io').hidden = true; $('ta').value = ''; };
$('ioGo').onclick = () => {
  let add = []; const raw = $('ta').value.trim();
  try { const j = JSON.parse(raw); add = Array.isArray(j) ? j.flatMap(x => [...String(x)]) : []; } catch (e) { add = [...raw]; }
  add = add.filter(c => HAN.test(c));
  if (add.length) save([...known, ...add]);
  $('io').hidden = true; $('ta').value = '';
};
chrome.storage.onChanged.addListener(async ch => {
  if (ch.lang) { lang = ch.lang.newValue === 'ru' || ch.lang.newValue === 'en' ? ch.lang.newValue : lang; render(); }
  if (ch.known) { known = ch.known.newValue || []; ready = false; render(); await load(known); ready = true; render(); }
});
chrome.storage.local.get(['known', 'lang'], async v => {
  known = v.known || []; if (v.lang === 'ru' || v.lang === 'en') lang = v.lang;
  render();
  core = await fetch(chrome.runtime.getURL('data/core.json')).then(r => r.json()).catch(() => []);
  await load([...known, ...core]);
  ready = true; render();
});
