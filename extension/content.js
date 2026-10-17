(() => {
  const HAN = /[㐀-鿿]/;
  const autoLang = (navigator.language || '').startsWith('ru') ? 'ru' : 'en';
  let host = null, enabled = true, off = false, mode = 'select', langPref = 'auto';
  const lang = () => (langPref === 'auto' ? autoLang : langPref);
  const key = 'off:' + location.hostname;
  try {
    chrome.storage.local.get(['enabled', 'mode', 'lang', key], v => { langPref = v.lang || 'auto'; enabled = v.enabled !== false; mode = v.mode === 'hover' ? 'hover' : 'select'; off = !!v[key]; });
    chrome.storage.onChanged.addListener(ch => {
      if (ch.enabled) enabled = ch.enabled.newValue !== false;
      if (ch.lang) langPref = ch.lang.newValue || 'auto';
      if (ch.mode) { mode = ch.mode.newValue === 'hover' ? 'hover' : 'select'; hide(); }
      if (ch[key]) off = !!ch[key].newValue;
    });
  } catch (e) {}

  const CSS = `:host{all:initial}
  *{box-sizing:border-box}
  .card{--bg:#faf7f2;--fg:#1f1b16;--muted:#7a7166;--card:#fff;--accent:#c8402a;--line:#cfc6b6;--soft:#e6dfd3;
    position:fixed;z-index:2147483647;width:max-content;max-width:360px;max-height:min(80vh,640px);overflow:auto;
    background:var(--card);color:var(--fg);border:1px solid var(--soft);border-radius:16px;padding:6px 0 4px;
    box-shadow:0 12px 40px rgba(31,27,22,.22),0 2px 6px rgba(31,27,22,.1);
    font:14px/1.45 system-ui,"Noto Sans SC",sans-serif;animation:in .12s ease-out;scrollbar-width:thin;scrollbar-color:var(--line) transparent}
  @keyframes in{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
  @media(prefers-reduced-motion:reduce){.card{animation:none}}
  .row{padding:10px 16px}.row+.row{border-top:1px solid var(--soft)}
  .head{display:flex;align-items:center;gap:12px}
  .tile{display:inline-flex;align-items:center;justify-content:center;min-width:44px;height:44px;padding:0 6px;background:var(--bg);
    border:2px solid var(--line);border-radius:12px;font:28px/1 "Noto Serif SC","Songti SC",serif;letter-spacing:.04em}
  .word .tile{border-color:var(--accent)}
  .py{font-weight:700;font-size:16px;color:var(--accent)}
  .def{color:var(--muted);margin-top:1px}
  .tree{margin:8px 0 0 22px}
  .node{position:relative;padding-left:18px;margin-top:6px}
  .node:before{content:"";position:absolute;left:0;top:-6px;bottom:0;border-left:1.5px solid var(--line)}
  .node:last-child:before{bottom:auto;height:20px}
  .node:after{content:"";position:absolute;left:0;top:14px;width:14px;border-top:1.5px solid var(--line)}
  .nrow{display:flex;align-items:center;gap:8px;min-height:28px}
  .nt{flex:none;display:inline-flex;align-items:center;justify-content:center;min-width:28px;height:28px;background:var(--bg);
    border:1.5px solid var(--line);border-radius:8px;font:18px/1 "Noto Serif SC","Songti SC",serif}
  .nt.leaf{border-style:dashed}
  .nd{color:var(--muted);font-size:13px}
  .foot{display:flex;justify-content:space-between;align-items:center;padding:8px 16px 6px;font-size:12px}
  .foot a{color:var(--accent);text-decoration:none;font-weight:600}.foot a:hover{text-decoration:underline}
  .foot span{color:var(--muted)}
  @media(prefers-color-scheme:dark){.card{--bg:#17140f;--fg:#f1ebe0;--muted:#9d9486;--card:#221e17;--accent:#ff7a5c;--line:#5a5144;--soft:#352f25;
    box-shadow:0 12px 40px rgba(0,0,0,.6),0 2px 6px rgba(0,0,0,.4)}}`;
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const tree = parts => (parts && parts.length ? `<div class="tree">${parts.map(p => `<div class="node"><div class="nrow"><span class="nt${p.parts.length ? '' : ' leaf'}">${esc(p.ch)}</span><span class="nd">${esc(p.def)}</span></div>${tree(p.parts)}</div>`).join('')}</div>` : '');

  function hide() { if (host) { host.remove(); host = null; } shown = ''; }
  let shown = '';

  function render(r, rect) {
    if (host) { host.remove(); host = null; }
    host = document.createElement('div');
    const root = host.attachShadow({ mode: 'closed' });
    const head = (cls, big, py, def) => `<div class="head"><span class="tile">${esc(big)}</span><div><div class="py">${esc(py)}</div><div class="def">${esc(def)}</div></div></div>`;
    let h = '';
    if (r.word) h += `<div class="row word">${head('', r.word.w, r.word.pinyin, r.word.def)}</div>`;
    r.chars.forEach(c => { h += `<div class="row">${head('', c.ch, c.pinyin, c.def)}${tree(c.parts)}</div>`; });
    h += `<div class="foot"><span>Hanzi Burst</span><a href="https://hanzi.lipu.dev/" target="_blank" rel="noopener">hanzi.lipu.dev ↗</a></div>`;
    root.innerHTML = `<style>${CSS}</style><div class="card">${h}</div>`;
    document.documentElement.appendChild(host);
    const card = root.querySelector('.card');
    const w = card.offsetWidth, ch = card.offsetHeight;
    const x = Math.min(Math.max(8, rect.left), innerWidth - w - 8);
    let y = rect.bottom + 6; if (y + ch > innerHeight - 8) y = Math.max(8, rect.top - ch - 6);
    card.style.left = x + 'px'; card.style.top = y + 'px';
  }

  // ---- mode: select ----
  async function onSelect(e) {
    if (!enabled || off || mode !== 'select') return;
    if (host && e && e.composedPath().includes(host)) return;
    const sel = getSelection(); const text = sel ? sel.toString().trim() : '';
    if (!text || text.length > 40 || !HAN.test(text)) return hide();
    const rect = sel.getRangeAt(0).getBoundingClientRect();
    try {
      const r = await chrome.runtime.sendMessage({ type: 'lookup', text, lang: lang() });
      if (r && getSelection().toString().trim() === text) render(r, rect);
    } catch (err) { /* extension reloaded */ }
  }
  document.addEventListener('mouseup', e => setTimeout(() => onSelect(e), 10));
  document.addEventListener('keyup', e => { if (e.key === 'Escape') hide(); else if (e.shiftKey) onSelect(e); });
  document.addEventListener('mousedown', e => { if (host && !e.composedPath().includes(host)) hide(); });
  document.addEventListener('scroll', hide, true);

  // ---- mode: hover ----
  // Character under the pointer plus the text that follows it (for word matching), and the character's box.
  function charAt(x, y) {
    let node, off;
    if (document.caretPositionFromPoint) { const p = document.caretPositionFromPoint(x, y); if (p) { node = p.offsetNode; off = p.offset; } }
    else if (document.caretRangeFromPoint) { const p = document.caretRangeFromPoint(x, y); if (p) { node = p.startContainer; off = p.startOffset; } }
    if (!node || node.nodeType !== 3) return null;
    const t = node.data;
    for (const o of [off, off - 1]) {                              // caret sits between characters: try both neighbours
      if (o < 0 || o >= t.length || !HAN.test(t[o])) continue;
      const r = document.createRange(); r.setStart(node, o); r.setEnd(node, o + 1);
      const b = r.getBoundingClientRect();
      if (x >= b.left - 1 && x <= b.right + 1 && y >= b.top - 1 && y <= b.bottom + 1) return { text: t.slice(o, o + 8), rect: b, id: o + ':' + t.slice(o, o + 8) };
    }
    return null;
  }
  let timer = 0, seq = 0;
  document.addEventListener('mousemove', e => {
    if (!enabled || off || mode !== 'hover') return;
    clearTimeout(timer);
    if (host && e.composedPath().includes(host)) return;           // pointer is on the card: keep it
    const x = e.clientX, y = e.clientY;
    timer = setTimeout(async () => {
      const hit = charAt(x, y);
      if (!hit) return hide();
      if (hit.id === shown) return;
      const my = ++seq;
      try {
        const r = await chrome.runtime.sendMessage({ type: 'lookup', text: hit.text, lang: lang(), hover: true });
        if (my === seq && r) { render(r, hit.rect); shown = hit.id; }
      } catch (err) {}
    }, 250);
  }, { passive: true });
})();
