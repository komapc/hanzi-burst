/* Переключатель «упрощённые / традиционные»: меняет только отображение (текстовые узлы),
   данные, ссылки и разбор остаются в упрощённой записи. Выбор — localStorage `hanzi-script` (s|t). */
(function () {
  const KEY = 'hanzi-script', HAN = /[㐀-鿿]/;
  let script = 's', map = null, loading = null;
  const orig = new Map();   // текстовый узел -> исходная (упрощённая) строка
  let busy = false;
  try { script = localStorage.getItem(KEY) === 't' ? 't' : 's'; } catch (e) {}

  const conv = s => { let o = ''; for (const c of s) o += map[c] || c; return o; };

  function walk(root) {
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: n => /^(SCRIPT|STYLE|TEXTAREA)$/.test(n.parentNode.nodeName) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
    const out = []; for (let n; (n = w.nextNode());) out.push(n); return out;
  }
  function apply(root) {
    if (!map) return;
    busy = true;
    try {
      for (const n of walk(root || document.body)) {
        const v = n.nodeValue;
        if (orig.has(n)) {
          // узел перезаписали снаружи — запоминаем новое значение как исходное
          if (v !== conv(orig.get(n))) orig.set(n, v);
        } else if (HAN.test(v)) orig.set(n, v);
        else continue;
        const want = script === 't' ? conv(orig.get(n)) : orig.get(n);
        if (n.nodeValue !== want) n.nodeValue = want;
      }
      for (const n of orig.keys()) if (!n.isConnected) orig.delete(n);
    } finally { busy = false; }
  }
  function load() {
    return loading = loading || fetch('data/s2t.json').then(r => r.json()).then(m => { map = m; }).catch(() => { map = {}; });
  }
  function sync() {
    document.querySelectorAll('.scr:not(.ph) input').forEach(i => { i.checked = i.value === script; });
  }
  function set(v) {
    script = v; try { localStorage.setItem(KEY, v); } catch (e) {}
    sync();
    load().then(() => { apply(); window.dispatchEvent(new Event('hanzi-script')); });
  }
  let timer = 0;
  new MutationObserver(() => {
    if (busy || script !== 't' || !map) return;
    clearTimeout(timer); timer = setTimeout(() => apply(), 30);
  }).observe(document.documentElement, { childList: true, subtree: true, characterData: true });

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.scr:not(.ph) input').forEach(i => i.onchange = () => { if (i.checked) set(i.value); });
    sync();
    if (script === 't') load().then(() => { apply(); window.dispatchEvent(new Event('hanzi-script')); });
  });
  window.hanziScript = { get: () => script, set, map: () => load().then(() => map) };
})();
