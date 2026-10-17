(() => {
  const HAN = /[㐀-鿿]/;
  const lang = (navigator.language || '').startsWith('ru') ? 'ru' : 'en';
  let host = null, enabled = true, off = false, mode = 'select';
  const key = 'off:' + location.hostname;
  try {
    chrome.storage.local.get(['enabled', 'mode', key], v => { enabled = v.enabled !== false; mode = v.mode === 'hover' ? 'hover' : 'select'; off = !!v[key]; });
    chrome.storage.onChanged.addListener(ch => {
      if (ch.enabled) enabled = ch.enabled.newValue !== false;
      if (ch.mode) { mode = ch.mode.newValue === 'hover' ? 'hover' : 'select'; hide(); }
      if (ch[key]) off = !!ch[key].newValue;
    });
  } catch (e) {}

  const CSS = `:host{all:initial}
  .card{position:fixed;z-index:2147483647;max-width:340px;max-height:60vh;overflow:auto;background:#fff;color:#1b1b1f;
    border:1px solid #d0d0d8;border-radius:12px;box-shadow:0 8px 28px rgba(0,0,0,.25);padding:12px 14px;
    font:14px/1.45 system-ui,sans-serif}
  .row+.row{margin-top:10px;padding-top:10px;border-top:1px solid #8883}
  .big{font-size:30px;line-height:1.1;margin-right:8px}.py{font-weight:600}.def{color:#555}
  .sub{margin:4px 0 0 14px;color:#666;font-size:13px}.sub b{font-size:17px;margin-right:6px}
  .sub .sub{border-left:1px solid #8885;padding-left:8px;margin-left:8px}
  a{color:#2b6cb0;text-decoration:none;font-size:12px}
  @media(prefers-color-scheme:dark){.card{background:#1d1e24;color:#ececf1;border-color:#3a3b44}.def,.sub{color:#a6a8b3}a{color:#7db3ff}}`;
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const tree = parts => (parts || []).map(p => `<div class="sub"><b>${esc(p.ch)}</b>${esc(p.def)}${tree(p.parts)}</div>`).join('');

  function hide() { if (host) { host.remove(); host = null; } shown = ''; }
  let shown = '';

  function render(r, rect) {
    if (host) { host.remove(); host = null; }
    host = document.createElement('div');
    const root = host.attachShadow({ mode: 'closed' });
    let h = '';
    if (r.word) h += `<div class="row"><span class="big">${esc(r.word.w)}</span><span class="py">${esc(r.word.pinyin)}</span><div class="def">${esc(r.word.def)}</div></div>`;
    r.chars.forEach(c => {
      h += `<div class="row"><span class="big">${esc(c.ch)}</span><span class="py">${esc(c.pinyin)}</span><div class="def">${esc(c.def)}</div>${tree(c.parts)}</div>`;
    });
    h += `<div class="row"><a href="https://hanzi.lipu.dev/" target="_blank" rel="noopener">hanzi.lipu.dev</a></div>`;
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
      const r = await chrome.runtime.sendMessage({ type: 'lookup', text, lang });
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
        const r = await chrome.runtime.sendMessage({ type: 'lookup', text: hit.text, lang, hover: true });
        if (my === seq && r) { render(r, hit.rect); shown = hit.id; }
      } catch (err) {}
    }, 250);
  }, { passive: true });
})();
